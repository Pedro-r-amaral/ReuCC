import streamlit as st
import plotly.express as px
from src.database import run_query

st.set_page_config(page_title="Placar e Analytics - CC", page_icon="🏆", layout="wide")

st.title("🏆 Placar do Rolê & Analytics da República")
st.markdown("Acompanhamento semestral de rolês, assiduidade nas reuniões e entrega de tarefas.")

# --- SELETOR DE PERÍODO (SEMESTRE OU HISTÓRICO GERAL) ---
df_periodos = run_query("""
    SELECT DISTINCT periodo_label 
    FROM vw_placar_semestral 
    ORDER BY periodo_label DESC
""")

opcoes_periodo = df_periodos["periodo_label"].tolist() if not df_periodos.empty else []
opcoes_periodo.append("Histórico Geral (Todos)")

periodo_escolhido = st.selectbox("Selecione o Ciclo Semestral:", options=opcoes_periodo)

# --- CONSULTAS ANALÍTICAS ---
if periodo_escolhido == "Histórico Geral (Todos)":
    df_placar = run_query("""
        SELECT 
            apelido,
            COALESCE(turma, 'S/T') AS turma,
            ativo,
            SUM(total_pontos)::INT AS total_pontos
        FROM vw_placar_semestral
        GROUP BY apelido, turma, ativo
        ORDER BY total_pontos DESC, apelido ASC
    """)
    
    df_faltas = run_query("""
        SELECT 
            apelido,
            SUM(faltas_nao_justificadas)::INT AS faltas_nao_justificadas,
            SUM(faltas_justificadas)::INT AS faltas_justificadas,
            SUM(presencas)::INT AS presencas
        FROM vw_faltas_semestral
        GROUP BY apelido
        ORDER BY faltas_nao_justificadas DESC, apelido ASC
    """)
else:
    df_placar = run_query(
        """
        SELECT 
            posicao_ranking,
            apelido,
            COALESCE(turma, 'S/T') AS turma,
            ativo,
            total_pontos
        FROM vw_placar_semestral
        WHERE periodo_label = :periodo
        ORDER BY total_pontos DESC, apelido ASC
        """,
        {"periodo": periodo_escolhido}
    )
    
    df_faltas = run_query(
        """
        SELECT 
            apelido,
            faltas_nao_justificadas,
            faltas_justificadas,
            presencas
        FROM vw_faltas_semestral
        WHERE periodo_label = :periodo
        ORDER BY faltas_nao_justificadas DESC, apelido ASC
        """,
        {"periodo": periodo_escolhido}
    )

# --- KPIs DO CICLO ---
df_kpi_tarefas = run_query("""
    SELECT 
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE status = 'concluida') AS concluidas
    FROM tarefas
""")
total_tar = int(df_kpi_tarefas["total"].iloc[0])
conc_tar = int(df_kpi_tarefas["concluidas"].iloc[0])
taxa_conclusao = (conc_tar / total_tar * 100) if total_tar > 0 else 0.0

k1, k2, k3 = st.columns(3)
lider = df_placar.iloc[0]["apelido"] if (not df_placar.empty and df_placar.iloc[0]["total_pontos"] > 0) else "—"
pts_lider = int(df_placar.iloc[0]["total_pontos"]) if not df_placar.empty else 0

k1.metric("👑 Líder do Placar", lider, f"{pts_lider} rolê(s)")
k2.metric("📈 Taxa Geral de Tarefas Concluídas", f"{taxa_conclusao:.1f}%", f"{conc_tar} de {total_tar}")
k3.metric("🚨 Total de Faltas Não Justificadas", int(df_faltas["faltas_nao_justificadas"].sum()) if not df_faltas.empty else 0)

st.divider()

# --- GRÁFICO 1: RANKING DO PLACAR DO ROLÊ ---
col_graf1, col_tab1 = st.columns([2, 1])

with col_graf1:
    st.subheader(f"🍻 Ranking de Rolês ({periodo_escolhido})")
    if df_placar.empty or df_placar["total_pontos"].sum() == 0:
        st.info("Ainda não há pontuação registrada neste período.")
    else:
        df_plot_role = df_placar[df_placar["total_pontos"] > 0].sort_values("total_pontos", ascending=True)
        fig_role = px.bar(
            df_plot_role,
            x="total_pontos",
            y="apelido",
            color="turma",
            orientation="h",
            text="total_pontos",
            labels={"total_pontos": "Pontos (Rolês)", "apelido": "Morador", "turma": "Turma"},
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_role.update_traces(textposition="outside")
        fig_role.update_layout(height=420, margin=dict(l=10, r=30, t=20, b=20))
        st.plotly_chart(fig_role, use_container_width=True)

with col_tab1:
    st.subheader("Tabela Oficial")
    if not df_placar.empty:
        colunas_exibir = ["apelido", "turma", "total_pontos"]
        if "posicao_ranking" in df_placar.columns:
            colunas_exibir.insert(0, "posicao_ranking")
        st.dataframe(
            df_placar[colunas_exibir],
            use_container_width=True,
            hide_index=True,
            column_config={
                "posicao_ranking": "#",
                "apelido": "Morador",
                "turma": "Turma",
                "total_pontos": "Rolês"
            }
        )

st.divider()

# --- GRÁFICO 2: FALTAS E PRESENÇAS NAS REUNIÕES ---
col_graf2, col_graf3 = st.columns(2)

with col_graf2:
    st.subheader("🔴 Faltas Não Justificadas")
    df_fnj = df_faltas[df_faltas["faltas_nao_justificadas"] > 0] if not df_faltas.empty else df_faltas
    if df_fnj.empty:
        st.success("Nenhuma falta não justificada registrada neste período!")
    else:
        fig_faltas = px.bar(
            df_fnj,
            x="apelido",
            y="faltas_nao_justificadas",
            text="faltas_nao_justificadas",
            labels={"apelido": "Morador", "faltas_nao_justificadas": "Faltas Não Justificadas"},
            color_discrete_sequence=["#EF553B"]
        )
        fig_faltas.update_traces(textposition="outside")
        fig_faltas.update_layout(height=350)
        st.plotly_chart(fig_faltas, use_container_width=True)

with col_graf3:
    st.subheader("🍺 Últimos Rolês Registrados")
    df_ultimos_roles = run_query("""
        SELECT 
            r.data_reuniao AS "Data",
            er.nome_evento AS "Rolê",
            COUNT(pr.morador_id) AS "Qtd Moradores",
            STRING_AGG(m.apelido, ', ' ORDER BY m.apelido) AS "Quem foi"
        FROM eventos_role er
        JOIN reunioes r ON r.id = er.reuniao_id
        LEFT JOIN presencas_role pr ON pr.evento_id = er.id
        LEFT JOIN moradores m ON m.id = pr.morador_id
        GROUP BY r.data_reuniao, er.id, er.nome_evento
        ORDER BY r.data_reuniao DESC, er.id DESC
        LIMIT 10
    """)
    if df_ultimos_roles.empty:
        st.write("Nenhum rolê registrado ainda.")
    else:
        st.dataframe(df_ultimos_roles, use_container_width=True, hide_index=True)