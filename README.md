# MQT-SYSTEM — README PARA AGENTE IDE
**Versão:** 2.0 · **Data:** 2026-03-13
**Para:** GitHub Copilot / Cursor / agente VS Code
**Contexto:** Camada 1 MVP — refactor estrutural + nova app de projectos

---

## ESTRATÉGIA DE BRANCHES

```
main (commit actual — base estável)
  ├── branch/fix-schema-mqt    ← FAZER PRIMEIRO
  │     Fix E+F+G Supabase + Fix A+C+B+D código MQT
  │     Testar Amorim + CUF end-to-end
  │
  ├── branch/projetos-app      ← FAZER A SEGUIR (após branch 1 mergeada)
  │     Fix H Supabase (projects ampliado)
  │     Nova projetos_app.py + main_app.py
  │     Renomear dashboard/app.py → apps/mqt_app.py
  │
  └── merge → main             ← só após as 2 branches testadas
```

**Regra absoluta:** nunca tocar em `dashboard/app.py` durante `branch/fix-schema-mqt`.
Renomear para `apps/mqt_app.py` só em `branch/projetos-app`.

---

## ESTADO ACTUAL

| Componente | Estado | Notas |
|---|---|---|
| Schema Supabase (7 tabelas) | ✅ v1.2 activo | Migrations pendentes (Fix E/F/G/H) |
| `pipeline/parser_excel.py` | ⚠️ Fix A urgente | Não detecta zonas correctamente |
| `pipeline/mapper_artigos.py` | ⚠️ Fix C | Lookup errado (sufixo vs elemento_sufixo) |
| `pipeline/ingest_mqt.py` | ⚠️ Fix B urgente | Falha com UploadedFile; sem emissão |
| `validation/indices.py` | ⚠️ Fix D | Regra 7.X.11 não implementada |
| `dashboard/app.py` | ✅ 4 tabs | Não tocar nesta branch |
| `elemento_map` seed | ⚠️ Fix F | Re-seed completo por elemento_sufixo |

---

## BRANCH 1: fix-schema-mqt

### Ordem de execução obrigatória

```
1. Fix E  → Supabase SQL (mqt_artigos: campos novos)
2. Fix F  → Supabase SQL (elemento_map: re-seed completo)
3. Fix G  → Supabase SQL (mqt_snapshots: emissao + zonas + area)
4. Fix A  → parser_excel.py
5. Fix C  → mapper_artigos.py
6. Fix B  → ingest_mqt.py
7. Fix D  → validation/indices.py
8.          Testar CUFMQT.xlsx end-to-end
9.          Re-testar Amorim
10.         git commit -m "refactor: duplo-eixo + zonas + area_construcao + thresholds KB05"
```

---

### FIX E — mqt_artigos: campos novos

```sql
ALTER TABLE mqt_artigos
  ADD COLUMN IF NOT EXISTS nivel           SMALLINT,
  ADD COLUMN IF NOT EXISTS is_nivel4       BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS elemento_sufixo TEXT,
  ADD COLUMN IF NOT EXISTS agrega_em       TEXT;

-- Popular elemento_sufixo nos registos existentes
UPDATE mqt_artigos
  SET elemento_sufixo = split_part(artigo_cod, '.', 3)
  WHERE elemento_sufixo IS NULL
    AND artigo_cod IS NOT NULL
    AND artigo_cod NOT LIKE '%.';
```

---

### FIX F — elemento_map: re-seed completo por elemento_sufixo

A chave de mapeamento passa de `(capitulo, sufixo)` para `(capitulo, elemento_sufixo)`.
`elemento_sufixo` = 3º segmento do artigo_cod (ex: `5.5.4` → `4`).

```sql
-- Limpar seed global antigo (preservar overrides de projecto específico)
DELETE FROM elemento_map WHERE projeto_id IS NULL;

-- Re-seed: um registo por (capitulo, elemento_sufixo)
-- Válido para qualquer classe de material (classe irrelevante para o mapeamento)
INSERT INTO elemento_map (capitulo, sufixo, elemento_tipo, artigo_desc_ref, projeto_id)
VALUES
-- CAP 5, 6, 7 — sufixos padrão JSJ
('5', '1',  'FUNDACAO',    'Fundações',                       NULL),
('5', '2',  'LAJE_FUNDO',  'Laje de fundo',                   NULL),
('5', '3',  'VIGA_FUND',   'Vigas de fundação',               NULL),
('5', '4',  'PILAR',       'Pilares',                         NULL),
('5', '5',  'NUCLEO',      'Núcleos',                         NULL),
('5', '6',  'PAREDE',      'Paredes',                         NULL),
('5', '7',  'PAREDE_PISC', 'Paredes de piscinas',             NULL),
('5', '8',  'PAREDE_RES',  'Paredes de reservatórios',        NULL),
('5', '9',  'CONTENCAO',   'Paredes de contenção',            NULL),
('5', '10', 'VIGA',        'Vigas',                           NULL),
('5', '11', 'LAJE_MACICA', 'Lajes maciças e dobras',          NULL),
('5', '12', 'LAJE_ALIG',   'Lajes aligeiradas',               NULL),
('5', '13', 'RAMPA',       'Lajes de rampas',                 NULL),
('5', '14', 'BANDA',       'Bandas',                          NULL),
('5', '15', 'CAPITEL',     'Capitéis',                        NULL),
('5', '16', 'MURETE',      'Muretes e platibandas',           NULL),
('5', '17', 'ESCADA',      'Escadas betonadas in situ',       NULL),
('5', '18', 'MASSAME',     'Massame',                         NULL),
('5', '19', 'MACIÇO',      'Maciços e plintos',               NULL),
('5', '20', 'OUTRO',       'Caixas técnicas',                 NULL),
('5', '21', 'OUTRO',       'Lâmina reforço alvenaria',        NULL),
('5', '99', 'OUTRO',       'Outros elementos',                NULL),
-- CAP 6 — mesmos sufixos
('6', '1',  'FUNDACAO',    'Cofragem fundações',              NULL),
('6', '2',  'LAJE_FUNDO',  'Cofragem laje de fundo',          NULL),
('6', '3',  'VIGA_FUND',   'Cofragem vigas fundação',         NULL),
('6', '4',  'PILAR',       'Cofragem pilares',                NULL),
('6', '5',  'NUCLEO',      'Cofragem núcleos',                NULL),
('6', '6',  'PAREDE',      'Cofragem paredes',                NULL),
('6', '7',  'PAREDE_PISC', 'Cofragem paredes piscinas',       NULL),
('6', '8',  'PAREDE_RES',  'Cofragem paredes reservatórios',  NULL),
('6', '9',  'CONTENCAO',   'Cofragem contenção',              NULL),
('6', '10', 'VIGA',        'Cofragem vigas',                  NULL),
('6', '11', 'LAJE_MACICA', 'Cofragem lajes maciças',          NULL),
('6', '12', 'LAJE_ALIG',   'Cofragem lajes aligeiradas',      NULL),
('6', '13', 'RAMPA',       'Cofragem rampas',                 NULL),
('6', '14', 'BANDA',       'Cofragem bandas',                 NULL),
('6', '15', 'CAPITEL',     'Cofragem capitéis',               NULL),
('6', '16', 'MURETE',      'Cofragem muretes',                NULL),
('6', '17', 'ESCADA',      'Cofragem escadas',                NULL),
('6', '99', 'OUTRO',       'Cofragem outros',                 NULL),
-- CAP 7 — mesmos sufixos
('7', '1',  'FUNDACAO',    'Aço fundações',                   NULL),
('7', '2',  'LAJE_FUNDO',  'Aço laje de fundo',               NULL),
('7', '3',  'VIGA_FUND',   'Aço vigas fundação',              NULL),
('7', '4',  'PILAR',       'Aço pilares',                     NULL),
('7', '5',  'NUCLEO',      'Aço núcleos',                     NULL),
('7', '6',  'PAREDE',      'Aço paredes',                     NULL),
('7', '7',  'PAREDE_PISC', 'Aço paredes piscinas',            NULL),
('7', '8',  'PAREDE_RES',  'Aço paredes reservatórios',       NULL),
('7', '9',  'CONTENCAO',   'Aço contenção',                   NULL),
('7', '10', 'VIGA',        'Aço vigas',                       NULL),
('7', '11', 'LAJE_MACICA', 'Aço lajes+bandas+capitéis',       NULL),
('7', '12', 'LAJE_ALIG',   'Aço lajes aligeiradas (sempre 0)',NULL),
('7', '13', 'RAMPA',       'Aço rampas',                      NULL),
('7', '14', 'BANDA',       'Aço bandas (sempre 0)',           NULL),
('7', '15', 'CAPITEL',     'Aço capitéis (sempre 0)',         NULL),
('7', '16', 'MURETE',      'Aço muretes',                     NULL),
('7', '17', 'ESCADA',      'Aço escadas',                     NULL),
('7', '18', 'MASSAME',     'Aço massame',                     NULL),
('7', '19', 'MACIÇO',      'Aço maciços e plintos',           NULL),
('7', '20', 'OUTRO',       'Aço caixas técnicas',             NULL),
('7', '21', 'OUTRO',       'Aço lâmina reforço',              NULL),
('7', '99', 'OUTRO',       'Aço outros elementos',            NULL)
ON CONFLICT DO NOTHING;
```

---

### FIX G — mqt_snapshots: campos novos

```sql
ALTER TABLE mqt_snapshots
  ADD COLUMN IF NOT EXISTS emissao         TEXT,         -- 'E01', 'E02', 'E03'...
  ADD COLUMN IF NOT EXISTS area_construcao NUMERIC,
  ADD COLUMN IF NOT EXISTS num_zonas       SMALLINT DEFAULT 1,
  ADD COLUMN IF NOT EXISTS zona_labels     JSONB;
-- Exemplo zona_labels: {"a":"Fundações","b":"Piso Térreo","c":"Pisos Elevados"}
```

---

### FIX A — parser_excel.py: detecção de zonas por pares QUANT.+PARCIAL

Substituir `_detect_layout()` pela versão abaixo.

**Lógica:**
- Ler linha 14 (header)
- Identificar pares QUANT.+PARCIAL consecutivos — cada par = 1 zona
- NÃO tentar ler labels de zona do Excel (labels vêm da ficha de projecto)
- Fallback: se não encontra pares, assume 1 zona (QUANT. simples)

```python
def _detect_layout(ws) -> dict:
    header_row = ws[14]
    quant_cols = []
    quant_total_col = None
    preco_unit_col = None
    total_eur_col = None
    prev_was_quant = False
    prev_quant_idx = None

    for i, cell in enumerate(header_row[:24]):
        val = str(cell.value or '').strip().upper().replace('\n', ' ')
        if val in ('QUANT.', 'QUANT'):
            prev_was_quant = True
            prev_quant_idx = i
        elif val == 'PARCIAL':
            if prev_was_quant and prev_quant_idx is not None:
                quant_cols.append(prev_quant_idx)
            prev_was_quant = False
            prev_quant_idx = None
        elif 'QUANT. TOTAL' in val or 'QUANT.TOTAL' in val or 'QUANT TOTAL' in val:
            quant_total_col = i
            prev_was_quant = False
        elif 'P. UNIT' in val or 'P.UNIT' in val:
            preco_unit_col = i
            prev_was_quant = False
        elif val in ('TOTAL €', 'TOTAL'):
            total_eur_col = i
            prev_was_quant = False
        else:
            prev_was_quant = False
            prev_quant_idx = None

    # Fallback: layout 1 zona sem PARCIAL intercalado
    if not quant_cols:
        for i, cell in enumerate(header_row[:24]):
            val = str(cell.value or '').strip().upper()
            if val in ('QUANT.', 'QUANT'):
                quant_cols = [i]
                break

    return {
        'quant_cols': quant_cols,       # ex: [6,8,10] para 3 zonas
        'quant_total': quant_total_col,
        'preco_unit': preco_unit_col,
        'total_eur': total_eur_col,
        'num_zonas': len(quant_cols) if quant_cols else 1,
    }
```

No `parse_mqt()`, após chamar `_detect_layout()`:

```python
zonas_keys = ['a', 'b', 'c', 'd']
zonas = [_get_cell_float(row[c]) for c in layout['quant_cols']]
quant_a = zonas[0] if len(zonas) > 0 else None
quant_b = zonas[1] if len(zonas) > 1 else None
quant_c = zonas[2] if len(zonas) > 2 else None
quant_d = zonas[3] if len(zonas) > 3 else None

col_qt = layout['quant_total']
quant_total = _get_cell_float(row[col_qt]) if col_qt is not None else None
if quant_total is None:
    quant_total = round(sum(z or 0 for z in zonas), 4) or None
```

Incluir no resultado do parse (nível snapshot):
```python
'num_zonas': layout['num_zonas'],
# zona_labels NÃO é responsabilidade do parser — vem de projects.zona_config
```

Limpar aspas no artigo_cod:
```python
artigo_cod = str(artigo_cod_value).strip().strip("'\"")
```

---

### FIX C — mapper_artigos.py: lookup por elemento_sufixo

Substituir lookup de `(capitulo, sufixo)` por `(capitulo, elemento_sufixo)`.
`elemento_sufixo` = 3º segmento do `artigo_cod`.

```python
# ANTES:
sufixo = artigo['sufixo']
resultado = elemento_map.get((capitulo, sufixo))

# DEPOIS:
elemento_sufixo = artigo['elemento_sufixo']  # já calculado no parser
resultado = elemento_map.get((capitulo, elemento_sufixo))
```

---

### FIX B — ingest_mqt.py

**1. Aceitar file-like object (UploadedFile Streamlit):**

```python
# ANTES:
excel_file = Path(excel_path)
if not excel_file.exists():
    raise FileNotFoundError(...)
ficheiro_ref = excel_file.name

# DEPOIS:
if hasattr(excel_path, 'read'):
    ficheiro_ref = getattr(excel_path, 'name', 'upload.xlsx')
else:
    excel_file = Path(excel_path)
    if not excel_file.exists():
        raise FileNotFoundError(f"Ficheiro não encontrado: {excel_path}")
    ficheiro_ref = excel_file.name
```

**2. Deduplicação por (project_id, fase, emissao):**

```python
existing = supabase_client.table('mqt_snapshots')\
    .select('id')\
    .eq('project_id', project_id)\
    .eq('fase', fase)\
    .eq('emissao', emissao)\
    .execute()
if existing.data:
    print(f"⚠️  Snapshot já existe para esta fase/emissão.")
    return existing.data[0]['id']
```

**3. Herdar zona_labels de projects.zona_config:**

```python
project = supabase_client.table('projects')\
    .select('zona_config, num_zonas')\
    .eq('id', project_id)\
    .single()\
    .execute()

zona_config = project.data.get('zona_config') or []
zona_labels = {z['key']: z.get('label') or z.get('tipo') for z in zona_config}
project_num_zonas = project.data.get('num_zonas', 1)
```

**4. Validação cruzada num_zonas (warning, não erro):**

```python
parser_num_zonas = parsed_data.get('num_zonas', 1)
if parser_num_zonas != project_num_zonas:
    st.warning(f"⚠️ Atenção: MQT tem {parser_num_zonas} zona(s) detectada(s) "
               f"mas o projecto está configurado com {project_num_zonas}. "
               f"Confirmar se o ficheiro está correcto.")
```

**5. Persistir campos novos no snapshot_data:**

```python
snapshot_data = {
    ...
    'emissao': emissao,
    'area_construcao': area_construcao if area_construcao and area_construcao > 0 else None,
    'num_zonas': parser_num_zonas,
    'zona_labels': zona_labels,
    'ficheiro_ref': ficheiro_ref,
}
```

**6. Campo `area_construcao` na tab Ingestão (dashboard/app.py):**

```python
area_construcao = st.number_input(
    "Área de Construção (m²)",
    min_value=0.0,
    step=10.0,
    help="Área estrutural total do edifício."
)
emissao = st.selectbox("Emissão", ["E01","E02","E03","E04","E05"])
if area_construcao == 0:
    st.warning("⚠️ Área não definida — índice C/Area não será calculado.")
```

---

### FIX D — validation/indices.py

**1. Regra 7.X.11 — ignorar artigos com aço sempre zero:**

```python
ARTIGOS_ACO_ZERO = {'12', '14', '16'}  # elemento_sufixo a ignorar no cap 7

def _filtrar_artigos_aco(artigos):
    return [
        a for a in artigos
        if not (a['capitulo'] == '7' and a['elemento_sufixo'] in ARTIGOS_ACO_ZERO)
    ]
```

**2. A/V Lajes+Bandas+Capitéis — denominador conjunto:**

```python
ELEMENTOS_LAJE_CONJUNTO = {'LAJE_MACICA', 'BANDA', 'CAPITEL'}

def _calc_av_lajes_conjunto(artigos_betao, artigos_aco):
    kg = sum(
        a['quant_total'] or 0
        for a in artigos_aco
        if a['capitulo'] == '7' and a['elemento_sufixo'] == '11'
    )
    m3 = sum(
        a['quant_total'] or 0
        for a in artigos_betao
        if a['elemento_tipo'] in ELEMENTOS_LAJE_CONJUNTO
    )
    return round(kg / m3, 1) if m3 > 0 else None
```

**3. C/Area — calcular só se área disponível:**

```python
area = snapshot.get('area_construcao')
if area and area > 0:
    c_area = round(total_cofragem / area, 3)
else:
    c_area = None  # não calcular, não dar falso positivo
```

---

### TESTE APÓS BRANCH 1

```
1. Upload CUFMQT.xlsx no dashboard tab Ingestão
   → Esperado: warning se num_zonas divergir do projecto
   → Esperado: ~84 artigos, >85% mapeados
2. Tab Índices: tabela completa com flags
3. Amorim: re-ingerir e confirmar A/V Lajes+Bandas+Capitéis = 127 kg/m³
4. git commit + merge para main
```

---

## BRANCH 2: projetos-app

### FIX H — Supabase: ampliar tabela projects

```sql
ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS fase           TEXT,
  ADD COLUMN IF NOT EXISTS num_zonas      SMALLINT DEFAULT 1,
  ADD COLUMN IF NOT EXISTS zona_config    JSONB,
  ADD COLUMN IF NOT EXISTS num_pisos      SMALLINT,
  ADD COLUMN IF NOT EXISTS piso_config    JSONB,
  ADD COLUMN IF NOT EXISTS elem_verticais JSONB,
  ADD COLUMN IF NOT EXISTS deleted_at     TIMESTAMPTZ;

-- Garantir cascade delete: snapshots apagados quando projecto apagado
-- (verificar se FK já tem ON DELETE CASCADE; se não, adicionar)
```

Exemplos JSONB:

`zona_config`:
```json
[
  {"key":"a","tipo":"Fundações","label":"Fundações"},
  {"key":"b","tipo":"Pisos Enterrados","label":"Cave -1"},
  {"key":"c","tipo":"Pisos Elevados","label":"Pisos 1-8"}
]
```

`piso_config`:
```json
[
  {"nome":"Cave -1","area":1200,"tipologia_laje":"Aligeirada",
   "bandas":true,"pre_esforco":false,"sistema":"Fungiforme","esp_laje":0.25},
  {"nome":"Piso 1","area":950,"tipologia_laje":"Maciça",
   "bandas":false,"pre_esforco":true,"sistema":"Vigada","esp_laje":0.20}
]
```

`elem_verticais`:
```json
{"nucleos_sismicos":true,"pilares":"Secundários"}
```

---

### Nova app: apps/projetos_app.py

Funcionalidades (por esta ordem de implementação):
1. **Listagem** de projectos (tabela: nome, fase, nº zonas, data criação)
2. **Criar projecto** — ficha 4 níveis (ver abaixo)
3. **Editar projecto** — mesma ficha pré-preenchida
4. **Apagar projecto** — confirmação explícita + soft-delete (`deleted_at = now()`)

**Ficha — Nível 1 (obrigatório):**
```python
nome = st.text_input("Nome do projecto")
fase = st.selectbox("Fase", ["EP", "PB", "PEX", "AT"])
num_zonas = st.number_input("Número de zonas", min_value=1, max_value=5, value=1)
```

**Ficha — Nível 2 (por zona, obrigatório se num_zonas > 1):**
```python
TIPOS_ZONA = ["Fundações","Pisos Enterrados","Piso Térreo",
              "Pisos Elevados","Cobertura","Outras"]
zona_keys = ['a','b','c','d','e']
zona_config = []
for i in range(num_zonas):
    col1, col2 = st.columns(2)
    tipo = col1.selectbox(f"Zona {zona_keys[i].upper()} — tipo", TIPOS_ZONA, key=f"tipo_{i}")
    label = col2.text_input(f"Label (opcional)", key=f"label_{i}")
    zona_config.append({"key": zona_keys[i], "tipo": tipo, "label": label or tipo})
```

**Ficha — Nível 3 (por piso, totalmente opcional):**
```python
num_pisos = st.number_input("Número de pisos (opcional)", min_value=0, value=0)
piso_config = []
if num_pisos > 0:
    for i in range(num_pisos):
        with st.expander(f"Piso {i+1}"):
            nome_piso = st.text_input("Nome", key=f"pnome_{i}")
            area = st.number_input("Área (m²)", min_value=0.0, key=f"parea_{i}")
            tip_laje = st.selectbox("Tipologia laje",
                                    ["Maciça","Aligeirada","Outra"], key=f"ptip_{i}")
            bandas = st.toggle("Com bandas?", key=f"pband_{i}")
            pe = st.toggle("Pré-esforço?", key=f"ppe_{i}")
            sistema = st.selectbox("Sistema", ["Fungiforme","Vigada"], key=f"psist_{i}")
            esp = st.number_input("Espessura média laje (m) — opcional",
                                  min_value=0.0, step=0.01, key=f"pesp_{i}")
            piso_config.append({
                "nome": nome_piso, "area": area,
                "tipologia_laje": tip_laje, "bandas": bandas,
                "pre_esforco": pe, "sistema": sistema,
                "esp_laje": esp if esp > 0 else None
            })
```

**Ficha — Nível 4 (elementos verticais, totalmente opcional):**
```python
with st.expander("Elementos verticais (opcional)"):
    nucleos = st.toggle("Núcleos sísmicos?")
    pilares = st.selectbox("Pilares", ["Sísmicos","Secundários","Misto"])
    elem_verticais = {"nucleos_sismicos": nucleos, "pilares": pilares}
```

**Regra:** guardar sempre, mesmo com níveis 3 e 4 vazios (None/[]).

---

### Aggregator: apps/main_app.py

```python
import streamlit as st

pg = st.navigation([
    st.Page("apps/projetos_app.py", title="Projectos", icon="🏗️"),
    st.Page("apps/mqt_app.py",      title="MQT",       icon="📊"),
])
pg.run()
```

Renomear `dashboard/app.py` → `apps/mqt_app.py` (sem alterações de conteúdo).

**Ponto de entrada após esta branch:** `streamlit run apps/main_app.py`

---

## ESTRUTURA DO REPO (estado target após ambas as branches)

```
mqt-system/
├── .env                         ← credenciais Supabase (não commitar)
├── .gitignore
├── requirements.txt
├── README.md
├── config/
│   └── settings.py              ✅ partilhado
├── pipeline/
│   ├── parser_excel.py          ← Fix A
│   ├── mapper_artigos.py        ← Fix C
│   └── ingest_mqt.py            ← Fix B
├── validation/
│   └── indices.py               ← Fix D
├── database/
│   ├── schema_mqt_d04.sql       ✅ v1.2 base
│   └── schema_migrations.sql   ← NOVO: todos os ALTER TABLE (Fix E/F/G/H)
├── apps/                        ← NOVO (branch/projetos-app)
│   ├── main_app.py
│   ├── mqt_app.py               ← renomear dashboard/app.py
│   └── projetos_app.py          ← NOVO
├── dashboard/
│   └── app.py                   ✅ não tocar até branch/projetos-app
└── tests/
    ├── test_connection.py       ✅
    ├── test_parser.py           ✅
    └── test_ingest.py           ✅
```

---

## TABELAS SUPABASE (estado target após ambas as branches)

```
projects          — ficha completa (zona_config, piso_config, elem_verticais, fase)
mqt_snapshots     — 1 por projecto × fase × emissão (zona_labels, area_construcao)
mqt_artigos       — artigos individuais (elemento_sufixo, is_nivel4, agrega_em, nivel)
mqt_indices       — A/V, A/C, V/C por elemento_tipo + flag + notas
elemento_map      — (capitulo, elemento_sufixo) → elemento_tipo [~50 rows após Fix F]
capitulo_map      — capítulo → tipo_qty + unidade [12 rows, estático]
jsj_precos_ref    — preços unitários JSJ [vazio — preencher]
```

---

## NOTAS

- **Supabase key:** service_role (nunca expor)
- **Excel:** nunca commitar — pasta `data/` no `.gitignore`
- **venv:** já activo — nunca recriar
- **Streamlit durante branch/fix-schema-mqt:** `streamlit run dashboard/app.py`
- **Streamlit após branch/projetos-app:** `streamlit run apps/main_app.py`
- **Projectos na DB:** AMORIM_TESTE e AmorimNovo (re-ingerir após fixes), CUF (pendente)
