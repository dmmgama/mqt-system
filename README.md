# MQT-SYSTEM — README PARA AGENTE IDE
**Versão:** 3.1 · **Data:** 2026-03-14
**Para:** GitHub Copilot / Cursor / agente VS Code
**Stack:** Python + openpyxl + Streamlit + Supabase (instância MVP)
**Repo:** `mqt-system` · **Ponto de entrada:** `streamlit run dashboard/app.py`

---

## ESTADO ACTUAL — branch `fix-schema-mqt`

### ✅ Tudo concluído e funcional

| Componente | Estado |
|---|---|
| Schema Supabase | ✅ Todas as migrations corridas |
| `pipeline/parser_excel.py` | ✅ Hierarquia completa + detecção de zonas |
| `pipeline/mapper_artigos.py` | ✅ Lookup correcto + OUTRO só caps 5/6/7 |
| `pipeline/ingest_mqt.py` | ✅ Substituição de snapshots + emissao + area + ordem |
| `validation/indices.py` | ✅ Regra 7.X.11 + C/Area nullable |
| `dashboard/app.py` | ✅ 4 tabs + visual hierárquico + nomes legíveis |
| `elemento_map` seed | ✅ 64 linhas, sufixos correctos por KB-07 |

### 🟡 Próxima branch: `projetos-app`
A fazer após commit e merge da branch actual em `main`.

---

## PRÓXIMA TAREFA — branch `projetos-app`

### Pré-requisito: commit da branch actual

```bash
git add -A
git commit -m "feat: visual hierárquico tab artigos + elemento labels + OUTRO só caps 5/6/7 + ordem artigos"
git checkout main
git merge fix-schema-mqt
git checkout -b projetos-app
```

### Fix H — Supabase: já corrido ✅
Colunas `fase`, `num_zonas`, `zona_config`, `piso_config`, `elem_verticais`, `deleted_at`
já existem na tabela `projects`.

### Nova app: `apps/projetos_app.py`

Funcionalidades (por esta ordem):
1. Listagem de projectos (tabela: nome, fase, nº zonas, data criação)
2. Criar projecto — ficha 4 níveis
3. Editar projecto — mesma ficha pré-preenchida
4. Apagar projecto — soft-delete (`deleted_at = now()`)

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

**Ficha — Nível 3 (por piso, opcional):**
```python
num_pisos = st.number_input("Número de pisos (opcional)", min_value=0, value=0)
piso_config = []
if num_pisos > 0:
    for i in range(num_pisos):
        with st.expander(f"Piso {i+1}"):
            nome_piso = st.text_input("Nome", key=f"pnome_{i}")
            area = st.number_input("Área (m²)", min_value=0.0, key=f"parea_{i}")
            tip_laje = st.selectbox("Tipologia laje", ["Maciça","Aligeirada","Outra"], key=f"ptip_{i}")
            bandas = st.toggle("Com bandas?", key=f"pband_{i}")
            pe = st.toggle("Pré-esforço?", key=f"ppe_{i}")
            sistema = st.selectbox("Sistema", ["Fungiforme","Vigada"], key=f"psist_{i}")
            esp = st.number_input("Espessura média laje (m)", min_value=0.0, step=0.01, key=f"pesp_{i}")
            piso_config.append({
                "nome": nome_piso, "area": area, "tipologia_laje": tip_laje,
                "bandas": bandas, "pre_esforco": pe, "sistema": sistema,
                "esp_laje": esp if esp > 0 else None
            })
```

**Ficha — Nível 4 (elementos verticais, opcional):**
```python
with st.expander("Elementos verticais (opcional)"):
    nucleos = st.toggle("Núcleos sísmicos?")
    pilares = st.selectbox("Pilares", ["Sísmicos","Secundários","Misto"])
    elem_verticais = {"nucleos_sismicos": nucleos, "pilares": pilares}
```

### Aggregator: `apps/main_app.py`

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

## SUPABASE — ESTADO ACTUAL

**Project ID:** `oajtzbvyjddyfggeusfe`
**Instância:** MVP dedicada (D08)

### Tabelas e colunas relevantes

**`mqt_artigos`** — colunas actuais:
- `id`, `snapshot_id`, `capitulo`, `subcapitulo`, `artigo_cod`, `sufixo`
- `descricao`, `unidade`, `especificacao`, `classe_material`
- `elemento_tipo`, `elemento_sufixo`, `is_nivel4`, `agrega_em`
- `nivel` (1=cap, 2=subcap, 3=artigo, 4=nivel4)
- `quant_a`, `quant_b`, `quant_c`, `quant_d`, `quant_total`
- `ordem` (INT — posição original no Excel, usado para ORDER BY)

**`mqt_snapshots`** — colunas actuais:
- `id`, `project_id`, `fase`, `data_upload`, `ficheiro_ref`
- `emissao`, `area_construcao`, `num_zonas`, `zona_labels` (JSONB)
- `status`, `created_at`

**`projects`** — colunas actuais:
- `id`, `nome`, `tipologia`, `fase_actual`, `created_at`
- `fase`, `num_zonas`, `zona_config` (JSONB), `piso_config` (JSONB)
- `elem_verticais` (JSONB), `deleted_at`

**`elemento_map`** — PK: `(capitulo, sufixo)`, 64 linhas globais
**`mqt_indices`** — `av`, `ac`, `vc`, `betao_m3`, `aco_kg`, `cofragem_m2`, `flag`

### Seed `elemento_map` (definitivo — KB-07)

Sufixo → elemento_tipo (igual para caps 5, 6, 7):

| sufixo | elemento_tipo |
|--------|---------------|
| 1 | FUNDACAO |
| 2 | LAJE_FUNDO |
| 3 | VIGA_FUND |
| 4 | PILAR |
| 5 | NUCLEO |
| 6 | PAREDE |
| 7 | PAREDE_PISC |
| 8 | PAREDE_RES |
| 9 | CONTENCAO |
| 10 | VIGA |
| 11 | LAJE_MACICA |
| 12 | LAJE_ALIG |
| 13 | RAMPA |
| 14 | BANDA |
| 15 | CAPITEL |
| 16 | MURETE |
| 17 | ESCADA |
| 18 | MASSAME |
| 19 | MACIÇO |
| 20 | OUTRO |
| 21 | OUTRO |
| 99 | OUTRO |

---

## LÓGICA CRÍTICA JSJ

### Parser (`parser_excel.py`)
- Sheet: `02.MQT` · Header: linha 14 · Dados: linha 15+
- Classificação por segmentos do código (col 3):
  - 1 segmento → CAP (nivel=1)
  - 2 segmentos → SUBCAP (nivel=2) — com ou sem quantidades
  - 3 segmentos → ARTIGO (nivel=3)
  - 4+ segmentos → ARTIGO nivel4 (is_nivel4=True)
- Linha cod=None + desc → SPEC → guardar em `especificacao` do artigo anterior
- `elemento_sufixo` = sempre 3º segmento (chave de mapeamento)
- Zonas: pares QUANT.+PARCIAL consecutivos na linha 14 (nunca ler labels do Excel)
- `quant_total` = coluna QUANT. TOTAL ou soma das zonas

### Mapper (`mapper_artigos.py`)
- Lookup: `(capitulo, sufixo)` → `elemento_tipo`
- CAPS_COM_MAPEAMENTO = `{'5', '6', '7'}`
- nivel < 3 ou elemento_sufixo None → `elemento_tipo = None`
- Sufixo desconhecido em caps 5/6/7 → `OUTRO`
- Outros capítulos → `None` (nunca OUTRO)

### Ingestão (`ingest_mqt.py`)
- Deduplicação: se (project_id, fase, emissao) existe → apagar anterior e criar novo
- `zona_labels` herdado de `projects.zona_config`
- `ordem = idx` (posição no array) para preservar ordem do Excel
- Validação cruzada `num_zonas`: warning se divergir (não bloqueia)

### Índices (`validation/indices.py`)
- A/V Lajes+Bandas+Capitéis: `kg(7.X.11) ÷ m³(LAJE_MACICA + BANDA + CAPITEL)`
- Artigos `7.X.{12,14,15}` filtrados (sempre 0)
- C/Area só calculado se `area_construcao` disponível
- Resultado guardado em `mqt_indices` + retornado à app

### Dashboard (`dashboard/app.py`)
- `ELEMENTO_LABELS` dict no topo — reutilizado nas tabs Índices e Artigos
- Tab Artigos: tabela HTML com estilos por nível, ORDER BY `ordem`
- Tab Artigos: filtro capítulo ordenado numericamente
- Tab Ingestão: campos emissão + área (4 colunas)
- Tab Gestão: apagar snapshot → apaga mqt_indices + mqt_artigos + mqt_snapshot (por ordem)

---

## ESTRUTURA DO REPO

```
mqt-system/
├── config/settings.py              — SUPABASE_URL + SUPABASE_SERVICE_KEY
├── pipeline/
│   ├── parser_excel.py
│   ├── mapper_artigos.py
│   └── ingest_mqt.py
├── validation/
│   └── indices.py
├── database/
│   ├── schema_mqt_d04.sql          — base v1.0 (não alterar)
│   └── schema_migrations.sql      — ALTER TABLE fixes E/F/G/H
├── dashboard/
│   └── app.py                      — não renomear até branch/projetos-app
└── tests/
    ├── test_connection.py
    ├── test_parser.py
    └── test_ingest.py
```

**Target após branch/projetos-app:**
```
apps/
├── main_app.py
├── mqt_app.py      ← renomear de dashboard/app.py
└── projetos_app.py ← novo
```

---

## NOTAS OPERACIONAIS

- **Supabase key:** service_role — nunca expor ou commitar
- **Excel MQT:** nunca commitar — pasta `data/` no `.gitignore`
- **venv:** já activo — nunca recriar
- **Streamlit actual:** `streamlit run dashboard/app.py`
- **Streamlit após branch 2:** `streamlit run apps/main_app.py`
- **Projectos na DB:** amorim (ok), cuf (40 OUTRO — investigar próxima sessão)