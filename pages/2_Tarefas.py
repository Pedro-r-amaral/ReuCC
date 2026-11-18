import streamlit as st
from src.database import run_query, execute_command

st.set_page_config(page_title="Tarefas da Casa - CC", page_icon="✅", layout="wide")

from src.auth import exigir_senha

st.set_page_config(...)  # Mantenha o set_page_config sempre como o 1º comando Streamlit
exigir_senha()           # Chama a trava de senha logo em seguida

st.title("✅ Quadro de Tarefas da República")
st.markdown("Acompanhe as pendências da semana, filtre por morador e dê baixa assim que concluir.")

# --- FILTROS NO TOPO ---
col_f1, col_f2 = st.columns([1, 2])

status_filtro = col_f1.radio(
    "Status das Tarefas:",
    options=["pendente", "concluida", "todas"],
    format_func=lambda x: {"pendente": "⏳ Pendentes", "concluida": "✅ Concluídas", "todas": "📋 Todas"}[x],
    horizontal=True
)

df_moradores = run_query("SELECT apelido FROM moradores WHERE ativo = TRUE ORDER BY apelido ASC")
lista_moradores = ["Todos"] + df_moradores["apelido"].tolist()
morador_filtro = col_f2.selectbox("Filtrar por Responsável:", options=lista_moradores)

# --- QUERY DINÂMICA COM STRING_AGG PARA AGRUPAR DUPLAS ---
where_clauses = []
params = {}

if status_filtro != "todas":
    where_clauses.append("t.status = :status")
    params["status"] = status_filtro

if morador_filtro != "Todos":
    where_clauses.append("""
        t.id IN (
            SELECT tr2.tarefa_id 
            FROM tarefa_responsaveis tr2 
            JOIN moradores m2 ON m2.id = tr2.morador_id 
            WHERE m2.apelido = :morador
        )
    """)
    params["morador"] = morador_filtro

where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

query_tarefas = f"""
    SELECT 
        t.id,
        t.titulo,
        t.descricao,
        t.prazo_data,
        t.prazo_texto,
        t.status,
        t.concluida_em,
        r.data_reuniao AS data_origem,
        COALESCE(STRING_AGG(m.apelido, ' / ' ORDER BY m.apelido), 'Sem responsável') AS responsaveis
    FROM tarefas t
    LEFT JOIN reunioes r ON r.id = t.reuniao_origem_id
    LEFT JOIN tarefa_responsaveis tr ON tr.tarefa_id = t.id
    LEFT JOIN moradores m ON m.id = tr.morador_id
    {where_sql}
    GROUP BY t.id, t.titulo, t.descricao, t.prazo_data, t.prazo_texto, t.status, t.concluida_em, r.data_reuniao
    ORDER BY 
        CASE WHEN t.status = 'pendente' THEN 0 ELSE 1 END,
        t.prazo_data ASC NULLS LAST,
        t.id DESC
"""

df_tarefas = run_query(query_tarefas, params)

st.divider()

if df_tarefas.empty:
    st.info("Nenhuma tarefa encontrada com os filtros selecionados.")
else:
    st.caption(f"Exibindo **{len(df_tarefas)}** tarefa(s)")
    
    for _, row in df_tarefas.iterrows():
        t_id = int(row["id"])
        is_pendente = row["status"] == "pendente"
        
        with st.container(border=True):
            c_info, c_prazo, c_acao = st.columns([4, 2, 1])
            
            with c_info:
                badge = "⏳" if is_pendente else "✅"
                st.markdown(f"### {badge} {row['titulo']} — `{row['responsaveis']}`")
                if row["descricao"]:
                    st.write(row["descricao"])
                if row["data_origem"]:
                    st.caption(f"Criada na ata de {row['data_origem'].strftime('%d/%m/%Y')}")
            
            with c_prazo:
                if row["prazo_data"]:
                    st.markdown(f"**Data Limite:** {row['prazo_data'].strftime('%d/%m/%Y')}")
                if row["prazo_texto"]:
                    st.markdown(f"**Condição:** {row['prazo_texto']}")
                if not row["prazo_data"] and not row["prazo_texto"]:
                    st.caption("Sem prazo definido")
            
            with c_acao:
                st.write("")  # Espaçamento vertical
                if is_pendente:
                    if st.button("Concluir ✔️", key=f"done_{t_id}", use_container_width=True, type="primary"):
                        execute_command(
                            "UPDATE tarefas SET status = 'concluida', concluida_em = NOW() WHERE id = :id",
                            {"id": t_id}
                        )
                        st.rerun()
                else:
                    if st.button("Reabrir ↩️", key=f"reopen_{t_id}", use_container_width=True):
                        execute_command(
                            "UPDATE tarefas SET status = 'pendente', concluida_em = NULL WHERE id = :id",
                            {"id": t_id}
                        )
                        st.rerun()