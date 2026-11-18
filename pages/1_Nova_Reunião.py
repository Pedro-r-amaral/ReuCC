import streamlit as st
from datetime import date
from src.database import run_query, salvar_reuniao_completa

st.set_page_config(page_title="Nova Reunião - CC", page_icon="📝", layout="wide")

from src.auth import exigir_senha

st.set_page_config(...)  # Mantenha o set_page_config sempre como o 1º comando Streamlit
exigir_senha()           # Chama a trava de senha logo em seguida

st.title("📝 Registro de Reunião Semanal")

# --- INICIALIZAÇÃO DA MEMÓRIA TEMPORÁRIA (SESSION STATE) ---
if "lembretes_lista" not in st.session_state:
    st.session_state.lembretes_lista = []
if "repasses_lista" not in st.session_state:
    st.session_state.repasses_lista = []
if "pautas_lista" not in st.session_state:
    st.session_state.pautas_lista = []
if "novas_tarefas_lista" not in st.session_state:
    st.session_state.novas_tarefas_lista = []
if "roles_lista" not in st.session_state:
    st.session_state.roles_lista = []

# --- CARREGA MORADORES ATIVOS ---
df_moradores = run_query("SELECT id, apelido, turma FROM moradores WHERE ativo = TRUE ORDER BY apelido ASC")
if df_moradores.empty:
    st.warning("Nenhum morador ativo encontrado. Cadastre os moradores primeiro.")
    st.stop()

mapa_apelido_id = dict(zip(df_moradores["apelido"], df_moradores["id"]))
lista_apelidos = df_moradores["apelido"].tolist()

# --- ABAS DA REUNIÃO ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1️⃣ Abertura & Chamada",
    "2️⃣ Lembretes & Repasses",
    "3️⃣ Pautas",
    "4️⃣ Novas Tarefas",
    "5️⃣ Placar do Rolê & Finalizar"
])

# ==============================================================================
# ABA 1: ABERTURA E CHAMADA
# ==============================================================================
with tab1:
    st.subheader("Cabeçalho e Presença")
    col1, col2, col3 = st.columns([1, 1, 1])
    data_reuniao = col1.date_input("Data da Reunião", value=date.today(), format="DD/MM/YYYY")
    redator_apelido = col2.selectbox("Redator da Ata", options=lista_apelidos)
    local_reuniao = col3.text_input("Local", value="São Carlos - SP")
    
    piada_do_dia = st.text_area("Piada do dia", placeholder="Digite a piada da reunião...", height=80)

    # Busca contagem atual de faltas não justificadas do semestre
    semestre = 1 if data_reuniao.month <= 6 else 2
    periodo_label = f"{data_reuniao.year}.{semestre}"
    df_faltas = run_query(
        "SELECT morador_id, faltas_nao_justificadas FROM vw_faltas_semestral WHERE periodo_label = :p",
        {"p": periodo_label}
    )
    mapa_faltas = dict(zip(df_faltas["morador_id"], df_faltas["faltas_nao_justificadas"])) if not df_faltas.empty else {}

    st.markdown(f"**Lista de Presença** *(Faltas acumuladas em {periodo_label} exibidas ao lado)*")
    
    presencas_coletadas = []
    cols_chamada = st.columns(2)
    for i, row in df_moradores.iterrows():
        m_id = int(row["id"])
        apelido = row["apelido"]
        faltas_atuais = mapa_faltas.get(m_id, 0)
        
        with cols_chamada[i % 2]:
            status_escolha = st.radio(
                f"**{apelido}** *(FNJ no semestre: {faltas_atuais})*",
                options=["presente", "justificada", "nao_justificada"],
                format_func=lambda x: {"presente": "✅ Presente", "justificada": "🟡 Justificada", "nao_justificada": "🔴 Não Justificada"}[x],
                horizontal=True,
                key=f"presenca_{m_id}"
            )
            presencas_coletadas.append({"morador_id": m_id, "status": status_escolha})

# ==============================================================================
# ABA 2: LEMBRETES E REPASSES (COM IMPORTAÇÃO AUTOMÁTICA)
# ==============================================================================
with tab2:
    col_lemb, col_rep = st.columns(2)
    
    # --- 1.1 LEMBRETES ---
    with col_lemb:
        st.subheader("1.1 Lembretes")
        with st.form("form_add_lembrete", clear_on_submit=True):
            l_titulo = st.text_input("Título do Lembrete", placeholder="Ex: checklist férias")
            l_resp = st.selectbox("Responsável / Turma (opcional)", options=["Nenhum", "024", "025", "026"] + lista_apelidos)
            if st.form_submit_button("➕ Adicionar Lembrete"):
                if l_titulo.strip():
                    prop_id = mapa_apelido_id.get(l_resp)
                    turma_v = l_resp if l_resp in ["024", "025", "026"] else None
                    st.session_state.lembretes_lista.append({
                        "tipo": "lembrete",
                        "titulo": l_titulo.strip(),
                        "proponente_id": prop_id,
                        "proponente_nome": l_resp if l_resp != "Nenhum" else "",
                        "turma_alvo": turma_v,
                        "descricao": ""
                    })

        for idx, item in enumerate(st.session_state.lembretes_lista):
            c1, c2 = st.columns([5, 1])
            sufixo = f" - {item['proponente_nome']}" if item["proponente_nome"] else ""
            c1.write(f"• **{item['titulo']}**{sufixo}")
            if c2.button("🗑️", key=f"del_lemb_{idx}"):
                st.session_state.lembretes_lista.pop(idx)
                st.rerun()

    # --- 1.2 REPASSES & BAIXA DE TAREFAS ANTIGAS ---
    with col_rep:
        st.subheader("1.2 Repasses")
        
        # Puxa tarefas pendentes do banco para dar baixa ou repassar
        df_pend = run_query("""
            SELECT t.id, t.titulo, STRING_AGG(m.apelido, '/') AS responsaveis
            FROM tarefas t
            LEFT JOIN tarefa_responsaveis tr ON t.id = tr.tarefa_id
            LEFT JOIN moradores m ON tr.morador_id = m.id
            WHERE t.status = 'pendente'
            GROUP BY t.id, t.titulo
            ORDER BY t.id ASC
        """)
        
        tarefas_atualizadas = []
        if not df_pend.empty:
            st.info("Tarefas pendentes da casa (marque as que foram concluídas nesta semana):")
            for _, t_row in df_pend.iterrows():
                t_id = int(t_row["id"])
                resp_str = f" ({t_row['responsaveis']})" if t_row["responsaveis"] else ""
                feita = st.checkbox(f"✅ Concluída: **{t_row['titulo']}**{resp_str}", key=f"check_tarefa_{t_id}")
                tarefas_atualizadas.append({"id": t_id, "concluida": feita})

        with st.form("form_add_repasse", clear_on_submit=True):
            r_titulo = st.text_input("Título do Repasse", placeholder="Ex: bebedouro")
            r_resp = st.selectbox("Quem repassou", options=["Nenhum"] + lista_apelidos)
            r_desc = st.text_area("O que foi dito no repasse", height=70)
            if st.form_submit_button("➕ Adicionar Repasse"):
                if r_titulo.strip():
                    st.session_state.repasses_lista.append({
                        "tipo": "repasse",
                        "titulo": r_titulo.strip(),
                        "proponente_id": mapa_apelido_id.get(r_resp),
                        "proponente_nome": r_resp if r_resp != "Nenhum" else "",
                        "turma_alvo": None,
                        "descricao": r_desc.strip()
                    })

        for idx, item in enumerate(st.session_state.repasses_lista):
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                sufixo = f" - {item['proponente_nome']}" if item["proponente_nome"] else ""
                c1.markdown(f"**{item['titulo']}**{sufixo}\n\n{item['descricao']}")
                if c2.button("🗑️", key=f"del_rep_{idx}"):
                    st.session_state.repasses_lista.pop(idx)
                    st.rerun()

# ==============================================================================
# ABA 3: PAUTAS
# ==============================================================================
with tab3:
    st.subheader("1.3 Pautas Discutidas")
    with st.form("form_add_pauta", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        p_titulo = c1.text_input("Título da Pauta", placeholder="Ex: CCeia")
        p_autor = c2.selectbox("Autor da Pauta", options=["Nenhum"] + lista_apelidos)
        p_desc = st.text_area("Discussão e Resolução", height=100)
        
        if st.form_submit_button("➕ Adicionar Pauta"):
            if p_titulo.strip():
                st.session_state.pautas_lista.append({
                    "tipo": "pauta",
                    "titulo": p_titulo.strip(),
                    "proponente_id": mapa_apelido_id.get(p_autor),
                    "proponente_nome": p_autor if p_autor != "Nenhum" else "",
                    "turma_alvo": None,
                    "descricao": p_desc.strip()
                })

    for idx, p in enumerate(st.session_state.pautas_lista):
        with st.container(border=True):
            c1, c2 = st.columns([6, 1])
            sufixo = f" - {p['proponente_nome']}" if p["proponente_nome"] else ""
            c1.markdown(f"**1.3.{idx+1} {p['titulo']}**{sufixo}\n\n{p['descricao']}")
            if c2.button("🗑️", key=f"del_pauta_{idx}"):
                st.session_state.pautas_lista.pop(idx)
                st.rerun()

# ==============================================================================
# ABA 4: NOVAS TAREFAS
# ==============================================================================
with tab4:
    st.subheader("1.4 Novas Tarefas Definidas na Reunião")
    with st.form("form_add_tarefa", clear_on_submit=True):
        c1, c2 = st.columns([2, 2])
        t_titulo = c1.text_input("Título da Tarefa", placeholder="Ex: borboleta do fogão")
        t_resps = c2.multiselect("Responsável(is)", options=lista_apelidos, placeholder="Selecione um ou mais moradores")
        
        c3, c4 = st.columns([1, 2])
        usar_data = c3.checkbox("Definir data exata?")
        t_data = c3.date_input("Prazo (Data)", value=date.today(), format="DD/MM/YYYY", disabled=not usar_data)
        t_prazo_txt = c4.text_input("Ou condição de prazo", placeholder="Ex: quando o gás acabar / próx reunião")
        t_desc = st.text_area("Detalhes da Tarefa", height=70)
        
        if st.form_submit_button("➕ Adicionar Tarefa"):
            if t_titulo.strip() and t_resps:
                st.session_state.novas_tarefas_lista.append({
                    "titulo": t_titulo.strip(),
                    "responsaveis_nomes": t_resps,
                    "responsaveis_ids": [mapa_apelido_id[nome] for nome in t_resps],
                    "prazo_data": t_data if usar_data else None,
                    "prazo_texto": t_prazo_txt.strip(),
                    "descricao": t_desc.strip()
                })
            else:
                st.warning("Preencha o título e selecione pelo menos um responsável.")

    for idx, t in enumerate(st.session_state.novas_tarefas_lista):
        with st.container(border=True):
            c1, c2 = st.columns([6, 1])
            nomes_str = "/".join(t["responsaveis_nomes"])
            prazo_str = f" | Prazo: {t['prazo_data'].strftime('%d/%m/%Y')}" if t["prazo_data"] else ""
            prazo_str += f" ({t['prazo_texto']})" if t["prazo_texto"] else ""
            c1.markdown(f"**1.4.{idx+1} {t['titulo']} - {nomes_str}**{prazo_str}\n\n{t['descricao']}")
            if c2.button("🗑️", key=f"del_tar_{idx}"):
                st.session_state.novas_tarefas_lista.pop(idx)
                st.rerun()

# ==============================================================================
# ABA 5: PLACAR DO ROLÊ E FINALIZAÇÃO
# ==============================================================================
with tab5:
    st.subheader("1.5 Placar do Rolê")
    with st.form("form_add_role", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        r_nome = c1.text_input("Nome do Rolê / Evento", placeholder="Ex: Banana da Capitu")
        r_peso = c2.number_input("Pontos", min_value=1, max_value=10, value=1)
        r_participantes = st.multiselect("Quem colou no rolê?", options=lista_apelidos)
        
        if st.form_submit_button("➕ Registrar Rolê"):
            if r_nome.strip() and r_participantes:
                st.session_state.roles_lista.append({
                    "nome_evento": r_nome.strip(),
                    "peso_pontos": int(r_peso),
                    "participantes_nomes": r_participantes,
                    "participantes_ids": [mapa_apelido_id[nome] for nome in r_participantes]
                })
            else:
                st.warning("Informe o nome do rolê e selecione quem foi.")

    for idx, r in enumerate(st.session_state.roles_lista):
        c1, c2 = st.columns([6, 1])
        c1.write(f"• **{r['nome_evento']}** ({r['peso_pontos']} pt): {', '.join(r['participantes_nomes'])}")
        if c2.button("🗑️", key=f"del_role_{idx}"):
            st.session_state.roles_lista.pop(idx)
            st.rerun()

    st.divider()
    st.subheader("Fechamento da Ata")
    recado_rodape = st.text_input("Recado final de rodapé (opcional)", placeholder="Ex: Nag, volta a olhar a ata!")

    if st.button("💾 SALVAR E FINALIZAR REUNIÃO", type="primary", use_container_width=True):
        itens_consolidados = (
            st.session_state.lembretes_lista +
            st.session_state.repasses_lista +
            st.session_state.pautas_lista
        )
        
        pacote_reuniao = {
            "data_reuniao": data_reuniao,
            "local": local_reuniao,
            "redator_id": mapa_apelido_id[redator_apelido],
            "piada_do_dia": piada_do_dia,
            "recado_rodape": recado_rodape,
            "presencas": presencas_coletadas,
            "tarefas_atualizadas": tarefas_atualizadas if not df_pend.empty else [],
            "itens_ata": itens_consolidados,
            "novas_tarefas": st.session_state.novas_tarefas_lista,
            "eventos_role": st.session_state.roles_lista
        }

        try:
            novo_id = salvar_reuniao_completa(pacote_reuniao)
            # Limpa os rascunhos da sessão após salvar
            for key in ["lembretes_lista", "repasses_lista", "pautas_lista", "novas_tarefas_lista", "roles_lista"]:
                st.session_state[key] = []
            st.success(f"🎉 Reunião #{novo_id} salva com sucesso no banco de dados!")
            st.balloons()
        except Exception as e:
            st.error(f"Erro ao salvar reunião (verifique se já existe uma reunião nesta data): {e}")