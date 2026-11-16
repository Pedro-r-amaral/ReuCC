import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

@st.cache_resource
def get_engine():
    """Cria e mantém em cache o motor de conexão com o PostgreSQL (Supabase)."""
    db_url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(db_url, pool_pre_ping=True)

def run_query(query: str, params: dict = None) -> pd.DataFrame:
    """Executa uma consulta SELECT e retorna um DataFrame do Pandas."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def execute_command(query: str, params: dict = None):
    """Executa comandos INSERT, UPDATE ou DELETE com commit automático."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(query), params or {})

def salvar_reuniao_completa(dados_reuniao: dict):
    """
    Grava a reunião e todas as suas dependências em uma única transação atômica.
    Se qualquer etapa falhar, o PostgreSQL faz ROLLBACK automático.
    """
    engine = get_engine()
    with engine.begin() as conn:
        # 1. Inserir cabeçalho da reunião e recuperar o ID gerado (RETURNING id)
        res_reuniao = conn.execute(
            text("""
                INSERT INTO reunioes (data_reuniao, local, redator_id, piada_do_dia, recado_rodape, status)
                VALUES (:data_reuniao, :local, :redator_id, :piada_do_dia, :recado_rodape, 'finalizada')
                RETURNING id
            """),
            {
                "data_reuniao": dados_reuniao["data_reuniao"],
                "local": dados_reuniao["local"],
                "redator_id": dados_reuniao["redator_id"],
                "piada_do_dia": dados_reuniao["piada_do_dia"] or None,
                "recado_rodape": dados_reuniao["recado_rodape"] or None,
            }
        )
        reuniao_id = res_reuniao.scalar_one()

        # 2. Inserir Presenças da Reunião
        for p in dados_reuniao["presencas"]:
            conn.execute(
                text("""
                    INSERT INTO presencas_reuniao (reuniao_id, morador_id, status)
                    VALUES (:reuniao_id, :morador_id, :status)
                """),
                {"reuniao_id": reuniao_id, "morador_id": p["morador_id"], "status": p["status"]}
            )

        # 3. Atualizar status das Tarefas antigas (repassadas na reunião)
        for t_upd in dados_reuniao["tarefas_atualizadas"]:
            if t_upd["concluida"]:
                conn.execute(
                    text("""
                        UPDATE tarefas 
                        SET status = 'concluida', concluida_em = NOW()
                        WHERE id = :id
                    """),
                    {"id": t_upd["id"]}
                )

        # 4. Inserir Itens da Ata (Lembretes, Repasses, Pautas)
        for idx, item in enumerate(dados_reuniao["itens_ata"], start=1):
            conn.execute(
                text("""
                    INSERT INTO itens_ata (reuniao_id, tipo, ordem, titulo, proponente_id, turma_alvo, descricao)
                    VALUES (:reuniao_id, :tipo, :ordem, :titulo, :proponente_id, :turma_alvo, :descricao)
                """),
                {
                    "reuniao_id": reuniao_id,
                    "tipo": item["tipo"],
                    "ordem": idx,
                    "titulo": item["titulo"],
                    "proponente_id": item["proponente_id"],
                    "turma_alvo": item["turma_alvo"] or None,
                    "descricao": item["descricao"] or None
                }
            )

        # 5. Inserir Novas Tarefas e seus Responsáveis (N:N)
        for tarefa in dados_reuniao["novas_tarefas"]:
            res_tarefa = conn.execute(
                text("""
                    INSERT INTO tarefas (reuniao_origem_id, titulo, descricao, prazo_data, prazo_texto, status)
                    VALUES (:reuniao_id, :titulo, :descricao, :prazo_data, :prazo_texto, 'pendente')
                    RETURNING id
                """),
                {
                    "reuniao_id": reuniao_id,
                    "titulo": tarefa["titulo"],
                    "descricao": tarefa["descricao"] or None,
                    "prazo_data": tarefa["prazo_data"],
                    "prazo_texto": tarefa["prazo_texto"] or None
                }
            )
            tarefa_id = res_tarefa.scalar_one()

            for m_id in tarefa["responsaveis_ids"]:
                conn.execute(
                    text("""
                        INSERT INTO tarefa_responsaveis (tarefa_id, morador_id)
                        VALUES (:tarefa_id, :morador_id)
                    """),
                    {"tarefa_id": tarefa_id, "morador_id": m_id}
                )

        # 6. Inserir Eventos do Placar do Rolê e Participantes
        for evento in dados_reuniao["eventos_role"]:
            res_evento = conn.execute(
                text("""
                    INSERT INTO eventos_role (reuniao_id, nome_evento, peso_pontos)
                    VALUES (:reuniao_id, :nome_evento, :peso_pontos)
                    RETURNING id
                """),
                {
                    "reuniao_id": reuniao_id,
                    "nome_evento": evento["nome_evento"],
                    "peso_pontos": evento["peso_pontos"]
                }
            )
            evento_id = res_evento.scalar_one()

            for m_id in evento["participantes_ids"]:
                conn.execute(
                    text("""
                        INSERT INTO presencas_role (evento_id, morador_id)
                        VALUES (:evento_id, :morador_id)
                    """),
                    {"evento_id": evento_id, "morador_id": m_id}
                )

        return reuniao_id