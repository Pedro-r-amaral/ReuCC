import streamlit as st
from src.database import run_query, execute_command

st.set_page_config(page_title="Moradores - CC", page_icon="👥", layout="wide")

from src.auth import exigir_senha

st.set_page_config(...)  # Mantenha o set_page_config sempre como o 1º comando Streamlit
exigir_senha()           # Chama a trava de senha logo em seguida

st.title("👥 Gestão de Moradores da República")
st.markdown("Cadastre novos membros, atualize turmas ou altere o status de moradores ativos/ex-moradores.")

# --- FORMULÁRIO DE NOVO MORADOR ---
with st.expander("➕ Cadastrar Novo Morador", expanded=False):
    with st.form("form_novo_morador", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        apelido = col1.text_input("Apelido (como sai na ata)*", placeholder="Ex: Calouro")
        nome_completo = col2.text_input("Nome Completo (opcional)", placeholder="Ex: João Silva")
        turma = col3.text_input("Turma", placeholder="Ex: 026")
        
        submitted = st.form_submit_button("Salvar Morador")
        
        if submitted:
            if not apelido.strip():
                st.error("O apelido é obrigatório!")
            else:
                try:
                    execute_command(
                        """
                        INSERT INTO moradores (apelido, nome_completo, turma, ativo)
                        VALUES (:apelido, :nome_completo, :turma, TRUE)
                        """,
                        {
                            "apelido": apelido.strip(),
                            "nome_completo": nome_completo.strip() or None,
                            "turma": turma.strip() or None
                        }
                    )
                    st.success(f"Morador **{apelido}** cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar (verifique se o apelido já existe): {e}")

st.divider()

# --- LISTAGEM E EDIÇÃO ---
df_moradores = run_query("""
    SELECT id, apelido, nome_completo, turma, ativo 
    FROM moradores 
    ORDER BY ativo DESC, apelido ASC
""")

col_esq, col_dir = st.columns([2, 1])

with col_esq:
    st.subheader("Lista Atual")
    st.dataframe(
        df_moradores,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "apelido": "Apelido",
            "nome_completo": "Nome Completo",
            "turma": "Turma",
            "ativo": st.column_config.CheckboxColumn("Morador Ativo?")
        }
    )

with col_dir:
    st.subheader("Editar Morador")
    if not df_moradores.empty:
        apelido_selecionado = st.selectbox(
            "Selecione o morador para alterar:",
            options=df_moradores["apelido"].tolist()
        )
        
        dados_atual = df_moradores[df_moradores["apelido"] == apelido_selecionado].iloc[0]
        
        with st.form("form_editar_morador"):
            novo_nome = st.text_input("Nome Completo", value=dados_atual["nome_completo"] or "")
            nova_turma = st.text_input("Turma", value=dados_atual["turma"] or "")
            novo_status = st.checkbox("Ativo na casa (aparece na chamada)", value=bool(dados_atual["ativo"]))
            
            if st.form_submit_button("Atualizar Dados"):
                execute_command(
                    """
                    UPDATE moradores 
                    SET nome_completo = :nome, turma = :turma, ativo = :ativo
                    WHERE id = :id
                    """,
                    {
                        "nome": novo_nome.strip() or None,
                        "turma": nova_turma.strip() or None,
                        "ativo": novo_status,
                        "id": int(dados_atual["id"])
                    }
                )
                st.success("Dados atualizados!")
                st.rerun()