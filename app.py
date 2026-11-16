import streamlit as st
from datetime import date
from src.database import run_query

st.set_page_config(
    page_title="Sistema de Atas - República CC",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ República Casa do Caralho — Sistema de Atas")
st.caption("Instituto do Caos de São Carlos • Gestão de Reuniões, Tarefas e Placar do Rolê")

# Identifica o semestre atual automaticamente
hoje = date.today()
semestre_atual = 1 if hoje.month <= 6 else 2
periodo_atual = f"{hoje.year}.{semestre_atual}"

st.info(f"📅 Período vigente: **{periodo_atual}** (Semestre {semestre_atual} de {hoje.year})")

# --- KPIs RÁPIDOS NA HOME ---
col1, col2, col3 = st.columns(3)

df_ativos = run_query("SELECT COUNT(*) AS total FROM moradores WHERE ativo = TRUE")
df_tarefas = run_query("SELECT COUNT(*) AS total FROM tarefas WHERE status = 'pendente'")
df_reunioes = run_query("SELECT COUNT(*) AS total FROM reunioes")

col1.metric("Moradores Ativos", int(df_ativos["total"].iloc[0]))
col2.metric("Tarefas Pendentes", int(df_tarefas["total"].iloc[0]))
col3.metric("Reuniões Registradas", int(df_reunioes["total"].iloc[0]))

st.divider()

# --- PRÉVIA DO PLACAR E REUNIÕES ---
esq, dir = st.columns(2)

with esq:
    st.subheader(f"🏆 Top Placar do Rolê ({periodo_atual})")
    df_placar = run_query(
        """
        SELECT posicao_ranking AS "#", apelido AS "Morador", total_pontos AS "Rolês"
        FROM vw_placar_semestral
        WHERE periodo_label = :periodo AND ativo = TRUE
        ORDER BY total_pontos DESC, apelido ASC
        LIMIT 10
        """,
        {"periodo": periodo_atual}
    )
    if df_placar.empty:
        st.write("Nenhuma reunião registrada neste semestre ainda.")
    else:
        st.dataframe(df_placar, use_container_width=True, hide_index=True)

with dir:
    st.subheader("📄 Últimas Atas Registradas")
    df_atas = run_query("""
        SELECT r.id, r.data_reuniao AS "Data", m.apelido AS "Redator", r.status AS "Status"
        FROM reunioes r
        LEFT JOIN moradores m ON m.id = r.redator_id
        ORDER BY r.data_reuniao DESC
        LIMIT 10
    """)
    if df_atas.empty:
        st.write("Nenhuma ata cadastrada ainda. Use o menu lateral para iniciar a primeira reunião.")
    else:
        st.dataframe(df_atas, use_container_width=True, hide_index=True)