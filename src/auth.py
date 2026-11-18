import streamlit as st

def exigir_senha():
    """Bloqueia a execução da página até que a senha correta da república seja inserida."""
    # Se já autenticou nesta sessão, libera o acesso imediatamente
    if st.session_state.get("autenticado", False):
        return

    st.title("🔒 Acesso Restrito — República CC")
    st.markdown("Digite a senha da casa para acessar o sistema de atas e o placar.")

    with st.form("form_login_cc"):
        senha_digitada = st.text_input("Senha da República", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")

        if entrar:
            if senha_digitada == st.secrets["senha_casa"]:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta! Tente novamente.")

    # Interrompe a execução do restante da página enquanto não estiver autenticado
    st.stop()