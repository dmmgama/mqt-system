-- ============================================================
-- MQT SYSTEM — JSJ Structural Engineering
-- Schema D04 | Tabelas Supabase MQT
-- Versão: 1.2 | Data: 2026-03-13
-- Decisão D08: instância Supabase dedicada MVP (SSOT indisponível)
-- ============================================================
-- INSTRUÇÕES:
-- 1. Correr numa instância Supabase NOVA e dedicada ao MQT (D08)
--    NÃO é a instância do SSOT
-- 2. Inclui tabela 'projects' local mínima (substitui FK SSOT no MVP)
--    Quando SSOT restaurado: apagar esta tabela + adicionar FK externa
-- 3. Correr por esta ordem (dependências FK)
-- ============================================================


-- ------------------------------------------------------------
-- 0. projects (tabela local MVP — substitui FK SSOT)
-- Mínima: só o necessário para identificar o projecto
-- MIGRAÇÃO FUTURA: apagar esta tabela + ligar FK a ssot.projects
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome            TEXT NOT NULL,
  tipologia       TEXT CHECK (tipologia IN
                    ('habitacao','servicos','misto','industrial','outro')),
  fase_actual     TEXT,
  data_mqt        DATE,
  area_total_m2   FLOAT,
  notas           TEXT,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- COMENTÁRIO: Esta tabela é temporária (MVP / D08).
-- Quando o SSOT for restaurado:
--   1. INSERT INTO ssot.projects (migrar dados)
--   2. UPDATE mqt_snapshots SET project_id = <novo_id_ssot>
--   3. DROP TABLE projects (esta)
--   4. ALTER TABLE mqt_snapshots ADD CONSTRAINT fk_ssot
--        FOREIGN KEY (project_id) REFERENCES ssot.projects(id)


-- ------------------------------------------------------------
-- 1. capitulo_map
-- Tabela estática — seed incluído no final
-- Diz ao sistema o que significa cada capítulo do MQT
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS capitulo_map (
  capitulo    TEXT PRIMARY KEY,
  tipo_qty    TEXT NOT NULL,
  unidade     TEXT NOT NULL,
  descricao   TEXT
);


-- ------------------------------------------------------------
-- 2. elemento_map
-- Mapeamento global sufixo → elemento_tipo
-- PK surrogate (BIGINT) — projeto_id pode ser NULL (mapeamento global)
-- UNIQUE (capitulo, sufixo, projeto_id) garante unicidade sem PK NULL
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS elemento_map (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  capitulo          TEXT NOT NULL,
  sufixo            TEXT NOT NULL,
  elemento_tipo     TEXT NOT NULL,
  artigo_desc_ref   TEXT,
  projeto_id        UUID REFERENCES projects(id) ON DELETE SET NULL,
  criado_por        TEXT,
  data_criacao      DATE DEFAULT CURRENT_DATE,
  notas             TEXT,
  UNIQUE (capitulo, sufixo, projeto_id)
);

-- Índice para lookup rápido por elemento_tipo
CREATE INDEX IF NOT EXISTS idx_elemento_map_tipo
  ON elemento_map(elemento_tipo);


-- ------------------------------------------------------------
-- 3. mqt_snapshots
-- Uma linha por entrega de MQT (projecto × fase × data)
-- project_id → FK para tabela 'projects' local (MVP/D08)
--              será migrado para FK SSOT em Camada 2
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mqt_snapshots (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  fase          TEXT NOT NULL CHECK (fase IN ('EP','Anteprojeto','CE','Execucao')),
  data_upload   DATE NOT NULL DEFAULT CURRENT_DATE,
  ficheiro_ref  TEXT,
  uploaded_by   TEXT,
  status        TEXT NOT NULL DEFAULT 'activo'
                  CHECK (status IN ('activo','substituido','rascunho')),
  revisao       TEXT,
  notas         TEXT,
  created_at    TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Índice para listar snapshots por projecto
CREATE INDEX IF NOT EXISTS idx_mqt_snapshots_project
  ON mqt_snapshots(project_id);


-- ------------------------------------------------------------
-- 4. mqt_artigos
-- Uma linha por artigo × snapshot
-- 3 dimensões: elemento_tipo + classe_material + zona A/B/C
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mqt_artigos (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id       UUID NOT NULL REFERENCES mqt_snapshots(id) ON DELETE CASCADE,
  capitulo          TEXT NOT NULL,
  subcapitulo       TEXT,
  artigo_cod        TEXT NOT NULL,
  sufixo            TEXT,
  descricao         TEXT,
  unidade           TEXT,
  classe_material   TEXT,
  elemento_tipo     TEXT,
  quant_a           FLOAT,
  quant_b           FLOAT,
  quant_c           FLOAT,
  quant_total       FLOAT
);

-- Índices para queries frequentes
CREATE INDEX IF NOT EXISTS idx_mqt_artigos_snapshot
  ON mqt_artigos(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_mqt_artigos_elemento
  ON mqt_artigos(elemento_tipo);
CREATE INDEX IF NOT EXISTS idx_mqt_artigos_capitulo
  ON mqt_artigos(capitulo);
CREATE INDEX IF NOT EXISTS idx_mqt_artigos_classe
  ON mqt_artigos(classe_material);


-- ------------------------------------------------------------
-- 5. mqt_indices
-- Índices calculados e persistidos por snapshot × elemento
-- Não recalcular automaticamente se notas/flag editados manualmente
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mqt_indices (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id     UUID NOT NULL REFERENCES mqt_snapshots(id) ON DELETE CASCADE,
  elemento_tipo   TEXT NOT NULL,
  betao_m3        FLOAT,
  aco_kg          FLOAT,
  cofragem_m2     FLOAT,
  av              FLOAT,   -- kg aço / m³ betão
  ac              FLOAT,   -- kg aço / m² cofragem
  vc              FLOAT,   -- m³ betão / m² cofragem
  flag            TEXT NOT NULL DEFAULT 'ok'
                    CHECK (flag IN ('ok','alerta','erro')),
  notas           TEXT,
  calculado_em    TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mqt_indices_snapshot
  ON mqt_indices(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_mqt_indices_elemento
  ON mqt_indices(elemento_tipo);


-- ------------------------------------------------------------
-- 6. jsj_precos_ref
-- Base de preços unitários JSJ
-- Actualizar manualmente após cada adjudicação
-- NUNCA ligar directamente a um snapshot
-- Estimativa = quant_total × preco_unit (calcular na app, não persistir)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jsj_precos_ref (
  artigo_cod          TEXT PRIMARY KEY,
  elemento_tipo       TEXT,
  capitulo            TEXT,
  classe_material     TEXT,
  descricao_ref       TEXT,
  unidade             TEXT,
  preco_unit          FLOAT NOT NULL,
  fonte               TEXT,
  data_actualizacao   DATE NOT NULL DEFAULT CURRENT_DATE,
  notas               TEXT
);

CREATE INDEX IF NOT EXISTS idx_jsj_precos_elemento
  ON jsj_precos_ref(elemento_tipo);


-- ============================================================
-- SEED — capitulo_map (dados fixos, correr uma vez)
-- ============================================================
INSERT INTO capitulo_map (capitulo, tipo_qty, unidade, descricao) VALUES
  ('3',  'mov_terras',    'm3',       'Movimentação de Terras'),
  ('4',  'fund_indireta', 'ml/m3/kg', 'Fundações Indirectas'),
  ('5',  'betao',         'm3',       'Betões'),
  ('6',  'cofragem',      'm2',       'Cofragem'),
  ('7',  'aco_ord',       'kg',       'Armaduras Ordinárias'),
  ('8',  'aco_activo',    'kg',       'Armaduras Activas (Pré-esforço)'),
  ('9',  'prefabricado',  'm3',       'Elementos Pré-fabricados'),
  ('10', 'aco_estrutural','kg',       'Estrutura Metálica'),
  ('11', 'madeira',       'm3',       'Estrutura de Madeira'),
  ('12', 'pavimento',     'm2/m3',    'Pavimento Térreo'),
  ('13', 'molde_alig',    'm2',       'Moldes de Aligeiramento'),
  ('15', 'diversos',      'vg',       'Diversos')
ON CONFLICT (capitulo) DO NOTHING;


-- ============================================================
-- SEED — elemento_map (mapeamento global caps 5, 6, 7)
-- sufixo → elemento_tipo para artigos standard JSJ
-- ============================================================
INSERT INTO elemento_map (capitulo, sufixo, elemento_tipo, artigo_desc_ref, projeto_id) VALUES

-- CAP 5 — Betões
('5', '1',    'FUNDACAO',       'Fundações',                          NULL),
('5', '1.1',  'FUNDACAO',       'Fundações',                          NULL),
('5', '1.2',  'MACIÇO_ESTACAS', 'Maciços de Encabeçamento de Estacas',NULL),
('5', '2',    'LAJE_FUNDO',     'Laje de fundo',                      NULL),
('5', '3',    'VIGA_FUND',      'Vigas de Fundação',                   NULL),
('5', '4',    'PILAR',          'Pilares',                            NULL),
('5', '5',    'NUCLEO',         'Núcleos',                            NULL),
('5', '6',    'PAREDE',         'Paredes',                            NULL),
('5', '7',    'PAREDE_PISC',    'Paredes de Piscinas',                NULL),
('5', '8',    'PAREDE_RES',     'Paredes de Reservatórios',           NULL),
('5', '9',    'CONTENCAO',      'Paredes de Contenção',               NULL),
('5', '10',   'VIGA',           'Vigas',                              NULL),
('5', '11',   'LAJE_MACICA',    'Lajes maciças e dobras',             NULL),
('5', '12',   'LAJE_ALIG',      'Lajes aligeiradas',                  NULL),
('5', '13',   'RAMPA',          'Lajes de rampas',                    NULL),
('5', '14',   'LAJE_PISC',      'Lajes de Piscinas',                  NULL),
('5', '15',   'BANDA',          'Bandas',                             NULL),
('5', '16',   'CAPITEL',        'Capitéis',                           NULL),
('5', '17',   'MURETE',         'Muretes e Platibandas',              NULL),
('5', '18',   'ESCADA',         'Escadas betonadas in situ',          NULL),
('5', '19',   'MASSAME',        'Massame de betão esquartelado',      NULL),
('5', '20',   'MACIÇO',         'Maciços e Plintos',                  NULL),
('5', '99',   'OUTRO',          'Outros elementos',                   NULL),

-- CAP 6 — Cofragem (sufixos sem subclasse de secção)
('6', '1',    'FUNDACAO',       'Fundações',                          NULL),
('6', '1.1',  'FUNDACAO',       'Fundações',                          NULL),
('6', '1.2',  'MACIÇO_ESTACAS', 'Maciços de Encabeçamento de Estacas',NULL),
('6', '2',    'LAJE_FUNDO',     'Laje de Fundo',                      NULL),
('6', '3',    'VIGA_FUND',      'Vigas de Fundação',                   NULL),
('6', '4',    'PILAR',          'Pilares',                            NULL),
('6', '4.1',  'PILAR',          'Pilares secção rectangular',         NULL),
('6', '4.2',  'PILAR',          'Pilares secção circular',            NULL),
('6', '5',    'NUCLEO',         'Núcleos',                            NULL),
('6', '5.1',  'NUCLEO',         'Núcleos secção rectangular',         NULL),
('6', '5.2',  'NUCLEO',         'Núcleos secção circular',            NULL),
('6', '6',    'PAREDE',         'Paredes',                            NULL),
('6', '6.1',  'PAREDE',         'Paredes secção rectangular',         NULL),
('6', '6.2',  'PAREDE',         'Paredes secção circular',            NULL),
('6', '7',    'PAREDE_PISC',    'Paredes de Piscinas',                NULL),
('6', '8',    'PAREDE_RES',     'Paredes de Reservatórios',           NULL),
('6', '9',    'CONTENCAO',      'Paredes de Contenção',               NULL),
('6', '10',   'VIGA',           'Vigas',                              NULL),
('6', '10.1', 'VIGA',           'Vigas',                              NULL),
('6', '10.2', 'VIGA',           'Vigas curvas',                       NULL),
('6', '11',   'LAJE_MACICA',    'Lajes maciças e dobras',             NULL),
('6', '12',   'LAJE_ALIG',      'Lajes aligeiradas',                  NULL),
('6', '13',   'RAMPA',          'Rampas',                             NULL),
('6', '14',   'LAJE_PISC',      'Lajes de Piscinas',                  NULL),
('6', '15',   'BANDA',          'Bandas',                             NULL),
('6', '16',   'CAPITEL',        'Capitéis',                           NULL),
('6', '17',   'MURETE',         'Muretes e Platibandas',              NULL),
('6', '18',   'ESCADA',         'Escadas betonadas in situ',          NULL),
('6', '19',   'MACIÇO',         'Maciços e Plintos',                  NULL),
('6', '99',   'OUTRO',          'Outros elementos',                   NULL),

-- CAP 7 — Armaduras Ordinárias
('7', '1',    'FUNDACAO',       'Fundações',                          NULL),
('7', '1.1',  'FUNDACAO',       'Fundações',                          NULL),
('7', '1.2',  'MACIÇO_ESTACAS', 'Maciços de Encabeçamento de Estacas',NULL),
('7', '2',    'LAJE_FUNDO',     'Laje de fundo',                      NULL),
('7', '3',    'VIGA_FUND',      'Vigas de Fundação',                   NULL),
('7', '4',    'PILAR',          'Pilares',                            NULL),
('7', '5',    'NUCLEO',         'Núcleos',                            NULL),
('7', '6',    'PAREDE',         'Paredes',                            NULL),
('7', '7',    'PAREDE_PISC',    'Paredes de Piscinas',                NULL),
('7', '8',    'PAREDE_RES',     'Paredes de Reservatórios',           NULL),
('7', '9',    'CONTENCAO',      'Paredes de Contenção',               NULL),
('7', '10',   'VIGA',           'Vigas',                              NULL),
('7', '11',   'LAJE_MACICA',    'Lajes maciças e dobras',             NULL),
('7', '12',   'LAJE_ALIG',      'Lajes aligeiradas',                  NULL),
('7', '13',   'RAMPA',          'Lajes de rampas',                    NULL),
('7', '14',   'LAJE_PISC',      'Lajes de Piscinas',                  NULL),
('7', '15',   'BANDA',          'Bandas',                             NULL),
('7', '16',   'CAPITEL',        'Capitéis',                           NULL),
('7', '17',   'MURETE',         'Muretes e Platibandas',              NULL),
('7', '18',   'ESCADA',         'Escadas betonadas in situ',          NULL),
('7', '19',   'MASSAME',        'Massame',                            NULL),
('7', '21',   'MACIÇO',         'Maciços e Plintos',                  NULL),
('7', '99',   'OUTRO',          'Outros elementos',                   NULL)

-- CAP 8 — Pré-esforço
INSERT INTO elemento_map 
  (capitulo, sufixo, elemento_tipo, artigo_desc_ref, projeto_id)
VALUES
('8', '1',   'PRE_ESFORCO', 'Pré-esforço Fundações',       NULL),
('8', '4',   'PRE_ESFORCO', 'Pré-esforço Pilares',         NULL),
('8', '10',  'PRE_ESFORCO', 'Pré-esforço Vigas',           NULL),
('8', '11',  'PRE_ESFORCO', 'Pré-esforço Lajes maciças',   NULL),
('8', '15',  'PRE_ESFORCO', 'Pré-esforço Bandas',          NULL),
('8', '99',  'PRE_ESFORCO', 'Pré-esforço outros',          NULL),
-- CAP 10 — Aço estrutural
('10', '1',  'ACO_ESTRUTURAL', 'Vigas metálicas',           NULL),
('10', '2',  'ACO_ESTRUTURAL', 'Pilares metálicos',         NULL),
('10', '99', 'ACO_ESTRUTURAL', 'Estrutura metálica outros', NULL),
-- CAP 11 — Madeira lamelada
('11', '1',  'MADEIRA', 'Vigas madeira lamelada',           NULL),
('11', '2',  'MADEIRA', 'Pilares madeira lamelada',         NULL),
('11', '99', 'MADEIRA', 'Madeira outros',                   NULL)

ON CONFLICT DO NOTHING;