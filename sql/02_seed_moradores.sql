INSERT INTO moradores (apelido, turma, ativo) VALUES
    ('Porteiro', '022', TRUE),
    ('Garçom', '023', TRUE),
    ('Bop', '023', TRUE),
    ('Peruana', '024', TRUE),
    ('Dug', '024', TRUE),
    ('Kiko', '024', TRUE),
    ('Sapo', '024', TRUE),
    ('Coragem', '025', TRUE),
    ('Cremoso', '025', TRUE),
    ('Bettina', '025', TRUE),
    ('Dolemeia', '026', TRUE),
    ('Piton', '026', TRUE),
    ('Aposto', '026', TRUE),
    ('Vorta', '026', TRUE)
ON CONFLICT (apelido) DO NOTHING;