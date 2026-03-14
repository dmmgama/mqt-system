# MQT-SYSTEM — README PARA AGENTE IDE
**Versão:** 3.2 · **Data:** 2026-03-14
**Para:** GitHub Copilot / Cursor / agente VS Code
**Stack:** Python + openpyxl + Streamlit + Supabase (instância MVP)
**Repo:** `mqt-system` · **Ponto de entrada actual:** `streamlit run apps/main_app.py`

---

## ESTADO ACTUAL — branch `mqt-zonasdinamicas`

### ✅ Concluído e funcional (inclui tudo de `fix-schema-mqt` + `projetos-app`)

| Componente | Estado |
|---|---|
| Schema Supabase | ✅ Todas as migrations corridas |
| `pipeline/parser_excel.py` | ✅ Hierarquia completa + detecção de zonas |
| `pipeline/mapper_artigos.py` | ✅ Lookup correcto + OUTRO só caps 5/6/7 |
| `pipeline/ingest_mqt.py` | ✅ Substituição de snapshots + emissao + area + ordem + zonas dinâmicas |
| `validation/indices.py` | ✅ Regra 7.X.11 + C/Area nullable — **melhorar nesta branch** |
| `apps/mqt_app.py` | ✅ 4 tabs + visual hierárquico + colunas dinâmicas por zona |
| `apps/projetos_app.py` | ✅ Ficha 4 níveis (criar/editar/apagar/listar) |
| `apps/main_app.py` | ✅ `st.navigation()` entre Projectos + MQT |
| `elemento_map` seed | ✅ 64 linhas, sufixos correctos por KB-07 |

### 🟡 Próxima tarefa nesta branch: melhorar `validation/indices.py` + UI de índices

---

## PRÓXIMA TAREFA — branch `mqt-zonasdinamicas`

### Objectivo
Melhorar a tab Índices da app com base no KB-05 actualizado:
- Calcular e mostrar A/V, V/C, A/C, C/Area por elemento e por zona
- Comparar com thresholds de referência do KB-05
- Flags visuais 🟡/🔴 por elemento

### Lógica de índices a implementar (`validation/indices.py`)

**Índices por elemento (global e por zona):**
- `A/V` = `aco_kg / betao_m3` (kg/m³)
- `V/C` = `betao_m3 / cofragem_m2` (m³/m²) — null se cofragem = 0
- `A/C` = `aco_kg / cofragem_m2` (kg/m²) — null se cofragem = 0
- `C/Area` = `cofragem_m2 / area_zona_m2` — null se area não disponível

**Área por zona:**
- Derivada da cofragem de laje (LAJE_MACICA + LAJE_ALIG) por zona
- Campo `area_zona_m2` em `mqt_indices` já existe na DB

**Regra especial LAJE_MACICA (regra 7.X.11):**
- A/V calculado em conjunto: `kg(7.X.11) ÷ [m³(LAJE_MACICA) + m³(BANDA) + m³(CAPITEL)]`
- Artigos 7.X.12, 7.X.14, 7.X.16 = sempre zero — excluir de todos os cálculos

**Elementos sem V/C** (betonados contra terreno — cofragem = 0 por definição):
- `LAJE_FUNDO`, `MASSAME`

**Thresholds de referência** (fonte: KB-05):

| `elemento_tipo` | A/V Min | A/V Alvo | A/V Máx |
|---|---|---|---|
| FUNDACAO | 80 | 120 | 150 |
| MACIÇO | 90 | 120 | 160 |
| LAJE_FUNDO | 110 | 150 | 180 |
| VIGA_FUND | 120 | 150 | 180 |
| MASSAME | 80 | 125 | 150 |
| CONTENCAO | 120 | 200 | 250 |
| PILAR | 220 | 300 | 350 |
| NUCLEO | 150 | 250 | 300 |
| PAREDE | 120 | 200 | 250 |
| PAREDE_PISC | 150 | 200 | 280 |
| PAREDE_RES | 150 | 200 | 280 |
| MURETE | 0 | 0 | 80 |
| VIGA | 160 | 200 | 280 |
| LAJE_MACICA | 90 | 130 | 160 |
| LAJE_ALIG | 110 | 150 | 180 |
| BANDA | 120 | 150 | 200 |
| CAPITEL | 120 | 150 | 200 |
| RAMPA | 110 | 120 | 180 |
| ESCADA | 90 | 120 | 150 |

**Lógica de flags:**
- 🔴 `erro`: fora de `[Min × 0.7, Máx × 1.3]`
- 🟡 `aviso`: fora de `[Min, Máx]` mas dentro da banda alargada
- ✅ `ok`: dentro de `[Min, Máx]`
- `None`: elemento sem threshold definido (MURETE com aco=0 é ok)

**Guardar em `mqt_indices`:** um registo por `(snapshot_id, elemento_tipo, zona_idx)`.
`zona_idx = None` para o agregado global.

### UI tab Índices (`apps/mqt_app.py`)

Estrutura sugerida:
1. Selector de snapshot (já existente)
2. Tabela global: elemento | betao_m3 | aco_kg | cofragem_m2 | A/V | V/C | A/C | flag
3. Se num_zonas > 1: tabs por zona com mesma tabela filtrada por `zona_idx`
4. Destacar visualmente linhas com flag 🔴/🟡
5. Índices globais de projecto: S/A, V/A, C/A (linha de rodapé ou card separado)

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
- `emissao`, `area_construcao`, `num_zonas`, `zona_labels` (JSONB), `zona_config` (JSONB)
- `status`, `revisao`, `notas`, `uploaded_by`, `created_at`

**`projects`** — colunas actuais:
- `id`, `nome`, `tipologia`, `fase_actual`, `data_mqt`, `area_total_m2`, `notas`, `created_at`
- `fase`, `num_zonas`, `zona_config` (JSONB)
- `num_pisos`, `piso_config` (JSONB)
- `elem_verticais` (JSONB), `deleted_at`

**`mqt_indices`** — colunas actuais:
- `id`, `snapshot_id`, `elemento_tipo`
- `betao_m3`, `aco_kg`, `cofragem_m2`
- `av`, `ac`, `vc`
- `flag`, `notas`, `calculado_em`
- `zona_idx` (SMALLINT — NULL = global, 0..N = zona específica)
- `area_zona_m2` (DOUBLE — área da zona derivada de cofragem de laje)

**`elemento_map`** — PK: `(capitulo, sufixo)`, 64 linhas globais
**`capitulo_map`** — 12 linhas
**`jsj_precos_ref`** — vazio (Camada 2)

### Seed `elemento_map` (definitivo — KB-07)

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
- Zonas: definidas na ficha de projecto; número de colunas QUANT. determinado por `num_zonas`
- `quant_total` = coluna QUANT. TOTAL ou soma das zonas

### Mapper (`mapper_artigos.py`)
- Lookup: `(capitulo, sufixo)` → `elemento_tipo`
- CAPS_COM_MAPEAMENTO = `{'5', '6', '7'}`
- nivel < 3 ou elemento_sufixo None → `elemento_tipo = None`
- Sufixo desconhecido em caps 5/6/7 → `OUTRO`
- Outros capítulos → `None` (nunca OUTRO)

### Ingestão (`ingest_mqt.py`)
- Deduplicação: se (project_id, fase, emissao) existe → apagar anterior e criar novo
- `zona_labels` e `zona_config` herdados de `projects.zona_config`
- `ordem = idx` (posição no array) para preservar ordem do Excel
- Número de colunas de zona determinado por `num_zonas` da ficha de projecto
- Validação cruzada `num_zonas`: warning se divergir (não bloqueia)

### Índices (`validation/indices.py`)
- A/V Lajes+Bandas+Capitéis: `kg(7.X.11) ÷ m³(LAJE_MACICA + BANDA + CAPITEL)`
- Artigos `7.X.{12,14,16}` filtrados (sempre 0)
- C/Area calculado a partir de cofragem de laje por zona (`area_zona_m2`)
- Resultado guardado em `mqt_indices` com `zona_idx` (NULL = global)
- Flags: `ok` / `aviso` / `erro` por comparação com thresholds KB-05

### App MQT (`apps/mqt_app.py`)
- `ELEMENTO_LABELS` dict no topo — reutilizado nas tabs Índices e Artigos
- Tab Artigos: tabela HTML com estilos por nível, ORDER BY `ordem`
- Tab Artigos: filtro capítulo ordenado numericamente; colunas de zona dinâmicas (por `num_zonas`)
- Tab Ingestão: campos emissão + área + configuração de zonas
- Tab Gestão: apagar snapshot → apaga mqt_indices + mqt_artigos + mqt_snapshot (por ordem)

---

## ESTRUTURA DO REPO

```
mqt-system/
├── config/settings.py
├── pipeline/
│   ├── parser_excel.py
│   ├── mapper_artigos.py
│   └── ingest_mqt.py
├── validation/
│   └── indices.py              ← melhorar nesta branch
├── database/
│   ├── schema_mqt_d04.sql
│   └── schema_migrations.sql
├── apps/
│   ├── main_app.py             ← ponto de entrada actual
│   ├── mqt_app.py              ← renomeado de dashboard/app.py
│   └── projetos_app.py
└── tests/
    ├── test_connection.py
    ├── test_parser.py
    └── test_ingest.py
```

**Ponto de entrada:** `streamlit run apps/main_app.py`

---

## NOTAS OPERACIONAIS

- **Supabase key:** service_role — nunca expor ou commitar
- **Excel MQT:** nunca commitar — pasta `data/` no `.gitignore`
- **venv:** já activo — nunca recriar