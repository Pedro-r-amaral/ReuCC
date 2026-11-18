import streamlit as st
from datetime import date
from src.database import run_query
from src.pdf_generator import gerar_pdf_ata
from src.auth import exigir_senha


st.set_page_config(
    page_title="Sistema de Atas - República CC",
    page_icon="🏛️",
    layout="wide"
)

exigir_senha()           # Chama a trava de senha logo em seguida

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
    st.subheader("📄 Atas Registradas & Exportação PDF")
    df_atas = run_query("""
        SELECT r.id, r.data_reuniao, m.apelido AS redator, r.status
        FROM reunioes r
        LEFT JOIN moradores m ON m.id = r.redator_id
        ORDER BY r.data_reuniao DESC
        LIMIT 15
    """)
    if df_atas.empty:
        st.write("Nenhuma ata cadastrada ainda. Use o menu lateral para iniciar a primeira reunião.")
    else:
        opcoes_atas = {
            f"Ata {row['data_reuniao'].strftime('%d/%m/%Y')} (Redator: {row['redator']})": int(row["id"])
            for _, row in df_atas.iterrows()
        }
        ata_escolhida = st.selectbox("Selecione uma ata para gerar o PDF oficial:", options=list(opcoes_atas.keys()))
        id_ata_sel = opcoes_atas[ata_escolhida]
        
        data_str_arquivo = df_atas[df_atas["id"] == id_ata_sel]["data_reuniao"].iloc[0].strftime("%m_%d")
        pdf_bytes = gerar_pdf_ata(id_ata_sel)
        
        st.download_button(
            label="📥 Baixar Ata Oficial (.PDF)",
            data=pdf_bytes,
            file_name=f"Ata_CC_{data_str_arquivo}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        st.dataframe(
            df_atas[["data_reuniao", "redator", "status"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "data_reuniao": "Data",
                "redator": "Redator",
                "status": "Status"
            }
        )