# MQT-SYSTEM — README PARA AGENTE IDE
**Versão:** 1.3 · **Data:** 2026-03-13  
**Para:** GitHub Copilot / Cursor / agente VS Code  
**Contexto:** Pipeline completo funcional — próximo passo: Streamlit dashboard

---

## ESTADO ACTUAL DO PROJECTO

| Componente | Estado |
|---|---|
| Repositório Git (`mqt-system`) | ✅ Criado |
| `.env` + credenciais Supabase | ✅ Configurado |
| `config/settings.py` | ✅ Feito |
| `requirements.txt` + venv | ✅ Instalado |
| Schema Supabase (7 tabelas) | ✅ Corrido — instância MVP activa |
| `tests/test_connection.py` | ✅ Passou |
| `pipeline/parser_excel.py` | ✅ Funcional — 50 artigos parseados |
| `pipeline/mapper_artigos.py` | ✅ Funcional — 90% mapeados (45/50) |
| `pipeline/ingest_mqt.py` | ✅ Funcional — bulk insert Supabase OK |
| `validation/indices.py` | ✅ Funcional — índices calculados e persistidos |
| Streamlit dashboard | 🔜 **PRÓXIMO PASSO** |

### Dados reais na DB

- **Projecto de teste:** AMORIM_TESTE
- **Snapshot ID:** `5dff81b4-abdf-43d2-bef3-c62c93e158b1`
- **mqt_artigos:** 50 linhas inseridas
- **mqt_indices:** calculados para todos os elemento_tipo com betão/aço/cofragem

---

## O QUE É ESTE PROJECTO

Sistema Python para ingestão, validação e análise de **Mapas de Quantidades (MQT)** de projetos de estruturas de engenharia civil (Portugal).

- Lê ficheiros Excel MQT do servidor da empresa
- Normaliza artigos por elemento estrutural (PILAR, VIGA, LAJE_MACICA, etc.)
- Calcula índices de validação: A/V (kg aço/m³ betão), A/C (kg/m²), V/C (m³/m²)
- Persiste tudo em Supabase para consulta via dashboard

---

## STACK TÉCNICA

| Componente | Tecnologia |
|---|---|
| Base de dados | Supabase (Postgres) — instância dedicada MVP (D08) |
| Ingestão | Python 3.11+ + openpyxl |
| Credenciais | python-dotenv (.env local, nunca commitar) |
| Interface | Streamlit — **a implementar agora** |
| Repositório | Git separado do SSOT |

---

## ESTRUTURA DE PASTAS

```
mqt-system/
├── .env                        ← credenciais (NÃO commitar)
├── .gitignore
├── requirements.txt
├── README.md
├── config/
│   └── settings.py             ← ✅ lê .env, expõe SUPABASE_URL, SUPABASE_SERVICE_KEY
├── database/
│   ├── schema_mqt_d04.sql      ← ✅ schema 7 tabelas + seeds (já corrido)
│   └── seeds/
│       └── capitulo_map.sql
├── pipeline/
│   ├── __init__.py
│   ├── parser_excel.py         ← ✅ parse Excel → lista de artigos
│   ├── mapper_artigos.py       ← ✅ lookup elemento_map Supabase
│   └── ingest_mqt.py           ← ✅ pipeline completo → Supabase
├── validation/
│   ├── __init__.py
│   └── indices.py              ← ✅ calcula A/V, A/C, V/C + persiste mqt_indices
├── dashboard/
│   └── app.py                  ← 🔜 Streamlit app (a criar)
├── data/
│   └── samples/
└── tests/
    ├── test_connection.py      ← ✅
    ├── test_parser.py          ← ✅
    └── test_ingest.py          ← ✅
```

---

## PRÓXIMO PASSO — `dashboard/app.py` (Streamlit)

### Objectivo

Dashboard de validação de MQT. O utilizador carrega um Excel, o sistema ingere e mostra os índices com flags.

### Páginas / secções (single-page, tabs ou sidebar)

**Tab 1 — Ingestão**
- Input: path do ficheiro Excel (text input) + nome projecto + fase (selectbox: EP/Anteprojeto/CE/Execucao)
- Botão "Processar MQT"
- Ao clicar:
  1. Criar projecto em `projects` se não existir (lookup por nome)
  2. Correr `ingest_mqt()` 
  3. Correr `calcular_indices()`
  4. Mostrar: "✅ X artigos ingeridos | Y mapeados | Z OUTRO"
- Mostrar lista de artigos OUTRO (aviso amarelo) para o utilizador verificar

**Tab 2 — Índices**
- Selectbox: escolher projecto + snapshot (fase + data)
- Tabela de índices por elemento_tipo:

| Elemento | Betão m³ | Aço kg | A/V kg/m³ | Cofragem m² | V/C m³/m² | Flag |
|----------|----------|--------|-----------|-------------|-----------|------|

- Flag colorida: 🟢 ok / 🟡 alerta / 🔴 erro
- Por agora flags são todas 'ok' — thresholds automáticos em iteração futura

**Tab 3 — Artigos**
- Tabela completa dos artigos do snapshot seleccionado
- Filtros: por capitulo, por elemento_tipo
- Colunas: artigo_cod, descricao, unidade, elemento_tipo, quant_a, quant_b, quant_c, quant_total

### Notas de implementação

- Criar pasta `dashboard/` e ficheiro `dashboard/app.py`
- Correr com: `streamlit run dashboard/app.py`
- Supabase client inicializado uma vez com `@st.cache_resource`
- Queries Supabase para Tab 2:
  ```python
  # Projectos disponíveis
  client.table("projects").select("id, nome").execute()
  
  # Snapshots do projecto
  client.table("mqt_snapshots")
        .select("id, fase, data_upload, status")
        .eq("project_id", project_id)
        .execute()
  
  # Índices do snapshot
  client.table("mqt_indices")
        .select("*")
        .eq("snapshot_id", snapshot_id)
        .execute()
  
  # Artigos do snapshot
  client.table("mqt_artigos")
        .select("artigo_cod, descricao, unidade, elemento_tipo, quant_a, quant_b, quant_c, quant_total")
        .eq("snapshot_id", snapshot_id)
        .execute()
  ```
- Usar `st.dataframe()` para tabelas — não `st.table()`
- Não usar `st.form()` — usar botões directos com `st.button()`

### Dados de teste disponíveis

Projecto AMORIM_TESTE já na DB com snapshot e índices calculados.
Usar para validar o dashboard antes de testar com Excel novo.

---

## PIPELINE — Referência Rápida

```python
# Ingestão completa de um Excel novo:
from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from pipeline.ingest_mqt import ingest_mqt
from validation.indices import calcular_indices

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
snapshot_id = ingest_mqt('path/to/MQT.xlsx', project_id, 'EP', client)
indices = calcular_indices(snapshot_id, client)
```

---

## TABELAS SUPABASE

```
projects          — projectos (local MVP, substituirá FK SSOT em Camada 2)
mqt_snapshots     — 1 linha por projecto × fase × entrega
mqt_artigos       — artigos individuais (50 linhas no Amorim)
mqt_indices       — índices calculados por elemento_tipo + flag
elemento_map      — (capitulo, sufixo) → elemento_tipo  [~82 rows com caps 8/10/11]
capitulo_map      — capítulo → tipo quantidade + unidade [12 rows]
jsj_precos_ref    — preços unitários JSJ [vazio — preencher manualmente]
```

### elemento_tipo válidos
```
FUNDACAO | MACIÇO_ESTACAS | LAJE_FUNDO | VIGA_FUND | PILAR | NUCLEO |
PAREDE | PAREDE_PISC | PAREDE_RES | CONTENCAO | VIGA | LAJE_MACICA |
LAJE_ALIG | RAMPA | LAJE_PISC | BANDA | CAPITEL | MURETE | ESCADA |
MASSAME | MACIÇO | FUND_INDIRETA | PRE_ESFORCO | ACO_ESTRUTURAL |
MADEIRA | MOLDE_ALIG | OUTRO
```

---

## NOTAS IMPORTANTES

- **Supabase key:** `service_role` (não `anon`) — nunca expor no frontend
- **Instância:** Dedicada ao MQT (D08) — não é a do SSOT
- **Excel:** Fica no servidor da empresa — nunca commitar
- **Dados reais:** Pasta `data/` no `.gitignore`
- **Estimativas de custo:** On-the-fly apenas — nunca persistidas
- **SSOT:** Tabelas `projects/blocks/floors/zones` não existem nesta instância