-- View 1: Placar de Rolês por Semestre (S1: Jan-Jun | S2: Jul-Dez)
CREATE OR REPLACE VIEW vw_placar_semestral AS
WITH periodos AS (
    SELECT DISTINCT
        EXTRACT(YEAR FROM data_reuniao)::INT AS ano,
        CASE WHEN EXTRACT(MONTH FROM data_reuniao) <= 6 THEN 1 ELSE 2 END AS semestre
    FROM reunioes
)
SELECT 
    p.ano,
    p.semestre,
    p.ano || '.' || p.semestre AS periodo_label,
    m.id AS morador_id,
    m.apelido,
    m.turma,
    m.ativo,
    COALESCE(SUM(er.peso_pontos), 0)::INT AS total_pontos,
    RANK() OVER (
        PARTITION BY p.ano, p.semestre 
        ORDER BY COALESCE(SUM(er.peso_pontos), 0) DESC
    )::INT AS posicao_ranking
FROM periodos p
CROSS JOIN moradores m
LEFT JOIN reunioes r 
    ON EXTRACT(YEAR FROM r.data_reuniao) = p.ano
    AND (CASE WHEN EXTRACT(MONTH FROM r.data_reuniao) <= 6 THEN 1 ELSE 2 END) = p.semestre
LEFT JOIN eventos_role er ON er.reuniao_id = r.id
LEFT JOIN presencas_role pr ON pr.evento_id = er.id AND pr.morador_id = m.id
GROUP BY p.ano, p.semestre, m.id, m.apelido, m.turma, m.ativo;

-- View 2: Contagem de Faltas Não Justificadas por Semestre
CREATE OR REPLACE VIEW vw_faltas_semestral AS
SELECT 
    EXTRACT(YEAR FROM r.data_reuniao)::INT AS ano,
    CASE WHEN EXTRACT(MONTH FROM r.data_reuniao) <= 6 THEN 1 ELSE 2 END AS semestre,
    EXTRACT(YEAR FROM r.data_reuniao)::INT || '.' || (CASE WHEN EXTRACT(MONTH FROM r.data_reuniao) <= 6 THEN 1 ELSE 2 END) AS periodo_label,
    m.id AS morador_id,
    m.apelido,
    COUNT(*) FILTER (WHERE pr.status = 'nao_justificada')::INT AS faltas_nao_justificadas,
    COUNT(*) FILTER (WHERE pr.status = 'justificada')::INT AS faltas_justificadas,
    COUNT(*) FILTER (WHERE pr.status = 'presente')::INT AS presencas
FROM reunioes r
JOIN presencas_reuniao pr ON pr.reuniao_id = r.id
JOIN moradores m ON m.id = pr.morador_id
GROUP BY 1, 2, 3, m.id, m.apelido;