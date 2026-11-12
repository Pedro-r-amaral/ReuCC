-- 1. Tabela de Moradores
CREATE TABLE IF NOT EXISTS moradores (
    id SERIAL PRIMARY KEY,
    nome_completo VARCHAR(100),
    apelido VARCHAR(50) UNIQUE NOT NULL,
    turma VARCHAR(10),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- 2. Tabela de Reuniões
CREATE TABLE IF NOT EXISTS reunioes (
    id SERIAL PRIMARY KEY,
    data_reuniao DATE NOT NULL UNIQUE,
    local VARCHAR(100) DEFAULT 'São Carlos - SP',
    redator_id INT REFERENCES moradores(id),
    piada_do_dia TEXT,
    recado_rodape TEXT,
    status VARCHAR(20) DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'finalizada')),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- 3. Presença por Reunião
CREATE TABLE IF NOT EXISTS presencas_reuniao (
    reuniao_id INT REFERENCES reunioes(id) ON DELETE CASCADE,
    morador_id INT REFERENCES moradores(id),
    status VARCHAR(20) NOT NULL CHECK (status IN ('presente', 'justificada', 'nao_justificada')),
    PRIMARY KEY (reuniao_id, morador_id)
);

-- 4. Itens da Ata (1.1 Lembretes, 1.2 Repasses, 1.3 Pautas)
CREATE TABLE IF NOT EXISTS itens_ata (
    id SERIAL PRIMARY KEY,
    reuniao_id INT REFERENCES reunioes(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('lembrete', 'repasse', 'pauta')),
    ordem INT NOT NULL DEFAULT 1,
    titulo VARCHAR(150) NOT NULL,
    proponente_id INT REFERENCES moradores(id),
    turma_alvo VARCHAR(10),
    descricao TEXT
);

-- 5. Tarefas (1.4 Tarefas + Quadro Geral)
CREATE TABLE IF NOT EXISTS tarefas (
    id SERIAL PRIMARY KEY,
    reuniao_origem_id INT REFERENCES reunioes(id),
    item_ata_id INT REFERENCES itens_ata(id) ON DELETE SET NULL,
    titulo VARCHAR(150) NOT NULL,
    descricao TEXT,
    prazo_data DATE,
    prazo_texto VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'concluida', 'cancelada')),
    concluida_em TIMESTAMP
);

-- 6. Responsáveis pela Tarefa (Suporta duplas como vorta/aposto)
CREATE TABLE IF NOT EXISTS tarefa_responsaveis (
    tarefa_id INT REFERENCES tarefas(id) ON DELETE CASCADE,
    morador_id INT REFERENCES moradores(id),
    PRIMARY KEY (tarefa_id, morador_id)
);

-- 7. Eventos do Placar do Rolê (1.5 Placar do role)
CREATE TABLE IF NOT EXISTS eventos_role (
    id SERIAL PRIMARY KEY,
    reuniao_id INT REFERENCES reunioes(id) ON DELETE CASCADE,
    nome_evento VARCHAR(150) NOT NULL,
    peso_pontos INT DEFAULT 1
);

-- 8. Participação no Rolê
CREATE TABLE IF NOT EXISTS presencas_role (
    evento_id INT REFERENCES eventos_role(id) ON DELETE CASCADE,
    morador_id INT REFERENCES moradores(id),
    PRIMARY KEY (evento_id, morador_id)
);