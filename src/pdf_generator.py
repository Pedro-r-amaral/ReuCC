import os
from fpdf import FPDF
from src.database import run_query

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def formatar_data_extenso(dt) -> str:
    return f"{dt.day:02d} de {MESES_PT[dt.month]} de {dt.year}"

def limpar_texto(texto: str) -> str:
    """Garante compatibilidade com fontes padrão Latin-1 do FPDF (Times/Helvetica)."""
    if not texto:
        return ""
    substituicoes = {
        "—": "-",
        "–": "-",
        "•": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "..."
    }
    for orig, sub in substituicoes.items():
        texto = texto.replace(orig, sub)
    return texto.encode("latin-1", "replace").decode("latin-1")

class AtaPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Times", "", 10)
        self.cell(0, 10, f"{self.page_no()}", align="C")

def gerar_pdf_ata(reuniao_id: int) -> bytes:
    """Busca todos os dados da reunião no PostgreSQL e monta o PDF oficial em bytes."""
    df_reu = run_query("""
        SELECT r.*, m.apelido AS redator_apelido
        FROM reunioes r
        LEFT JOIN moradores m ON m.id = r.redator_id
        WHERE r.id = :id
    """, {"id": reuniao_id})
    
    if df_reu.empty:
        raise ValueError("Reunião não encontrada.")
    
    reu = df_reu.iloc[0]
    dt = reu["data_reuniao"]
    data_extenso = formatar_data_extenso(dt)

    df_pres = run_query("""
        SELECT m.apelido, pr.status
        FROM presencas_reuniao pr
        JOIN moradores m ON m.id = pr.morador_id
        WHERE pr.reuniao_id = :id
        ORDER BY m.apelido ASC
    """, {"id": reuniao_id})

    presentes = df_pres[df_pres["status"] == "presente"]["apelido"].tolist()
    justificadas = df_pres[df_pres["status"] == "justificada"]["apelido"].tolist()
    nao_justificadas = df_pres[df_pres["status"] == "nao_justificada"]["apelido"].tolist()

    mes_inicio = 1 if dt.month <= 6 else 7
    data_inicio_sem = f"{dt.year}-{mes_inicio:02d}-01"
    
    df_fnj_acum = run_query("""
        SELECT m.apelido, COUNT(*)::INT AS total
        FROM presencas_reuniao pr
        JOIN reunioes r ON r.id = pr.reuniao_id
        JOIN moradores m ON m.id = pr.morador_id
        WHERE pr.status = 'nao_justificada'
          AND r.data_reuniao BETWEEN :inicio AND :fim
        GROUP BY m.apelido
        ORDER BY total DESC, m.apelido ASC
    """, {"inicio": data_inicio_sem, "fim": dt})

    df_itens = run_query("""
        SELECT ia.*, m.apelido AS proponente_apelido
        FROM itens_ata ia
        LEFT JOIN moradores m ON m.id = ia.proponente_id
        WHERE ia.reuniao_id = :id
        ORDER BY ia.ordem ASC, ia.id ASC
    """, {"id": reuniao_id})

    lembretes = df_itens[df_itens["tipo"] == "lembrete"]
    repasses = df_itens[df_itens["tipo"] == "repasse"]
    pautas = df_itens[df_itens["tipo"] == "pauta"]

    df_tarefas = run_query("""
        SELECT t.titulo, t.descricao, t.prazo_data, t.prazo_texto,
               COALESCE(STRING_AGG(m.apelido, '/' ORDER BY m.apelido), '') AS responsaveis
        FROM tarefas t
        LEFT JOIN tarefa_responsaveis tr ON tr.tarefa_id = t.id
        LEFT JOIN moradores m ON m.id = tr.morador_id
        WHERE t.reuniao_origem_id = :id
        GROUP BY t.id, t.titulo, t.descricao, t.prazo_data, t.prazo_texto
        ORDER BY t.id ASC
    """, {"id": reuniao_id})

    df_roles = run_query("""
        SELECT er.nome_evento,
               COALESCE(STRING_AGG(LOWER(m.apelido), ', ' ORDER BY m.apelido), '') AS participantes
        FROM eventos_role er
        LEFT JOIN presencas_role pr ON pr.evento_id = er.id
        LEFT JOIN moradores m ON m.id = pr.morador_id
        WHERE er.reuniao_id = :id
        GROUP BY er.id, er.nome_evento
        ORDER BY er.id ASC
    """, {"id": reuniao_id})

    # ==========================================================================
    # MONTAGEM VISUAL DO PDF
    # ==========================================================================
    pdf = AtaPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(22, 20, 22)
    pdf.set_auto_page_break(auto=True, margin=20)
    largura_util = pdf.epw  # Largura útil exata (210 - 22 - 22 = 166mm)

    # --- PÁGINA 1: CAPA INSTITUCIONAL ---
    pdf.add_page()
    pdf.ln(15)
    
    brasao_path = os.path.join("assets", "brasao_cc.png")
    if os.path.exists(brasao_path):
        pdf.image(brasao_path, x=80, w=50)
        pdf.ln(8)
    else:
        pdf.set_line_width(1.8)
        pdf.ellipse(82, 35, 46, 46)
        pdf.set_y(49)
        pdf.set_font("Helvetica", "B", 34)
        pdf.cell(largura_util, 18, "CC", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(18)

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Times", "B", 15)
    pdf.cell(largura_util, 8, limpar_texto("REPÚBLICA CASA DO CARALHO"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "", 12)
    pdf.cell(largura_util, 7, limpar_texto("INSTITUTO DO CAOS DE SÃO CARLOS"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(25)

    pdf.set_font("Times", "B", 18)
    pdf.cell(largura_util, 10, "CC", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Times", "", 17)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(largura_util, 9, limpar_texto(f"Reunião Caralho {data_extenso}"), align="C")

    pdf.set_y(-50)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Times", "", 12)
    pdf.cell(largura_util, 7, limpar_texto(reu["local"] or "São Carlos - SP"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(largura_util, 7, limpar_texto(data_extenso), align="C", new_x="LMARGIN", new_y="NEXT")

    # --- PÁGINA 2 EM DIANTE: CONTEÚDO DA ATA ---
    pdf.add_page()
    
    def titulo_secao(texto: str, tamanho: int = 14):
        pdf.ln(4)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Times", "B", tamanho)
        pdf.cell(largura_util, 8, limpar_texto(texto), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def linha_rotulo_valor(rotulo: str, valor: str):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Times", "", 11)
        texto_limpo = limpar_texto(f"**{rotulo}** {valor}")
        pdf.multi_cell(largura_util, 6, texto_limpo, markdown=True)

    titulo_secao("1   Reunião", 15)
    linha_rotulo_valor("Redator:", reu["redator_apelido"] or "-")
    linha_rotulo_valor("Presentes:", ", ".join(presentes) if presentes else "Nenhum")
    linha_rotulo_valor("Faltas justificadas:", ", ".join(justificadas))
    linha_rotulo_valor("Faltas não justificadas:", ", ".join(nao_justificadas))

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, limpar_texto("Contagem de Faltas não justificadas:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "", 11)
    if df_fnj_acum.empty:
        pdf.set_x(pdf.l_margin)
        pdf.cell(largura_util, 6, limpar_texto("  - Nenhuma falta não justificada no semestre."), new_x="LMARGIN", new_y="NEXT")
    else:
        for _, f_row in df_fnj_acum.iterrows():
            pdf.set_x(pdf.l_margin)
            pdf.cell(largura_util, 6, limpar_texto(f"  - {f_row['apelido']}: {f_row['total']}"), new_x="LMARGIN", new_y="NEXT")

    if reu["piada_do_dia"]:
        pdf.ln(2)
        linha_rotulo_valor("Piada do dia:", reu["piada_do_dia"])

    # 1.1 Lembretes
    titulo_secao("1.1   Lembretes:", 13)
    pdf.set_font("Times", "", 11)
    if lembretes.empty:
        pdf.set_x(pdf.l_margin)
        pdf.cell(largura_util, 6, "  - Sem lembretes.", new_x="LMARGIN", new_y="NEXT")
    else:
        for _, item in lembretes.iterrows():
            resp = item["proponente_apelido"] or item["turma_alvo"] or ""
            sufixo = f" - {resp}" if resp else ""
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(largura_util, 6, limpar_texto(f"  - {item['titulo']}{sufixo}"))

    # 1.2 Repasses
    titulo_secao("1.2   Repasses:", 13)
    if repasses.empty:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Times", "", 11)
        pdf.cell(largura_util, 6, "Sem repasses registrados.", new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, (_, item) in enumerate(repasses.iterrows(), start=1):
            resp = item["proponente_apelido"] or ""
            sufixo = f" - {resp}:" if resp else ":"
            pdf.ln(1)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Times", "B", 11)
            pdf.multi_cell(largura_util, 6, limpar_texto(f"1.2.{idx}   {item['titulo']}{sufixo}"))
            if item["descricao"]:
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Times", "", 11)
                pdf.multi_cell(largura_util, 6, limpar_texto(item["descricao"]))

    # 1.3 Pautas
    titulo_secao("1.3   Pautas", 13)
    if pautas.empty:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Times", "", 11)
        pdf.cell(largura_util, 6, "Sem pautas discutidas.", new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, (_, item) in enumerate(pautas.iterrows(), start=1):
            resp = item["proponente_apelido"] or ""
            sufixo = f" - {resp}:" if resp else ":"
            pdf.ln(1)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Times", "B", 11)
            pdf.multi_cell(largura_util, 6, limpar_texto(f"1.3.{idx}   {item['titulo']}{sufixo}"))
            if item["descricao"]:
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Times", "", 11)
                pdf.multi_cell(largura_util, 6, limpar_texto(item["descricao"]))

    # 1.4 Tarefas
    titulo_secao("1.4   Tarefas", 13)
    if df_tarefas.empty:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Times", "", 11)
        pdf.cell(largura_util, 6, limpar_texto("Nenhuma nova tarefa atribuída."), new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, (_, tar) in enumerate(df_tarefas.iterrows(), start=1):
            resp = tar["responsaveis"]
            sufixo = f" - {resp}:" if resp else ":"
            pdf.ln(1)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Times", "B", 11)
            pdf.multi_cell(largura_util, 6, limpar_texto(f"1.4.{idx}   {tar['titulo']}{sufixo}"))
            
            detalhes = tar["descricao"] or ""
            extras = []
            if tar["prazo_data"]:
                extras.append(f"Prazo: {tar['prazo_data'].strftime('%d/%m/%Y')}")
            if tar["prazo_texto"]:
                extras.append(tar["prazo_texto"])
            if extras:
                detalhes = f"{detalhes} ({' | '.join(extras)})".strip()
                
            if detalhes:
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Times", "", 11)
                pdf.multi_cell(largura_util, 6, limpar_texto(detalhes))

    # 1.5 Placar do role
    titulo_secao("1.5   Placar do role", 13)
    pdf.set_font("Times", "", 11)
    if df_roles.empty:
        pdf.set_x(pdf.l_margin)
        pdf.cell(largura_util, 6, limpar_texto("  - Nenhum rolê registrado nesta semana."), new_x="LMARGIN", new_y="NEXT")
    else:
        for _, r_row in df_roles.iterrows():
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(largura_util, 6, limpar_texto(f"  - {r_row['nome_evento']}: {r_row['participantes']}"))

    # Recado de rodapé
    if reu["recado_rodape"]:
        pdf.ln(8)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Times", "B", 11)
        pdf.multi_cell(largura_util, 6, limpar_texto(reu["recado_rodape"]))

    return bytes(pdf.output())