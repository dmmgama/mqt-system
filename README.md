# MQT-SYSTEM — README PARA AGENTE IDE
**Versão:** 1.0 · **Data:** 2026-03-13  
**Para:** GitHub Copilot / Cursor / agente VS Code  
**Contexto:** Setup inicial do repositório `mqt-system`

---

## O QUE É ESTE PROJECTO

Sistema Python para ingestão, validação e análise de **Mapas de Quantidades (MQT)** de projetos de estruturas de engenharia civil (Portugal).

- Lê ficheiros Excel MQT de um servidor de empresa (path local)
- Escreve dados normalizados numa instância **Supabase existente** (partilhada com outro sistema — SSOT)
- **NÃO toca nas tabelas do SSOT** — apenas escreve nas 6 tabelas MQT novas
- Futuro: Streamlit dashboard, análise com LLM API

---

## STACK TÉCNICA

| Componente | Tecnologia |
|---|---|
| Base de dados | Supabase (Postgres) — instância existente |
| Ingestão | Python 3.11+ + pandas + openpyxl |
| Credenciais | python-dotenv (.env local, nunca commitar) |
| Interface futura | Streamlit |
| Repositório | Git separado do SSOT |

---

## ESTRUTURA DE PASTAS A CRIAR

```
mqt-system/
├── .env                        ← credenciais (NÃO commitar — está no .gitignore)
├── .gitignore
├── requirements.txt
├── README.md                   ← este ficheiro
├── config/
│   └── settings.py             ← lê .env, expõe constantes
├── database/
│   ├── schema_mqt_d04.sql      ← schema das 6 tabelas (copiar ficheiro externo)
│   └── seeds/
│       └── capitulo_map.sql    ← seed estático (copiar ficheiro externo)
├── pipeline/
│   ├── __init__.py
│   ├── ingest_mqt.py           ← script principal de ingestão
│   ├── parser_excel.py         ← leitura e normalização do Excel MQT
│   └── mapper_artigos.py       ← lógica artigo_cod → (capitulo, sufixo) → elemento_tipo
├── validation/
│   ├── __init__.py
│   └── indices.py              ← cálculo de índices (kg/m³, m²/m³) + flags
├── data/
│   └── samples/                ← Excels de teste ANONIMIZADOS (não commitar dados reais)
└── tests/
    └── test_parser.py
```

---

## INSTRUÇÕES DE SETUP (executar por ordem)

### 1. Inicializar repositório Git

```bash
mkdir mqt-system
cd mqt-system
git init
git branch -M main
```

### 2. Criar .gitignore

Criar ficheiro `.gitignore` com o seguinte conteúdo:

```
.env
*.env
data/
__pycache__/
*.pyc
.DS_Store
*.xlsx
*.xls
```

> ⚠️ CRÍTICO: O `.env` com credenciais Supabase e os ficheiros Excel reais (pasta `data/`) **nunca** devem ser commitados.

### 3. Criar requirements.txt

```
supabase==2.3.0
pandas==2.2.0
openpyxl==3.1.2
python-dotenv==1.0.0
streamlit==1.32.0
```

### 4. Instalar dependências

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Criar .env (NÃO commitar)

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...    # service role key (não a anon key)
MQT_EXCEL_PATH=\\\\servidor\\partilha\\MQT   # UNC path ou path local
```

### 6. Criar config/settings.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
MQT_EXCEL_PATH = os.getenv("MQT_EXCEL_PATH")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Credenciais Supabase em falta no .env")
```

### 7. Testar ligação Supabase

Criar `tests/test_connection.py`:

```python
from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

def test_connection():
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    # Testar que as tabelas MQT existem
    result = client.table("mqt_snapshots").select("id").limit(1).execute()
    print("✅ Ligação Supabase OK")
    print(f"   mqt_snapshots: {result}")

if __name__ == "__main__":
    test_connection()
```

Executar: `python tests/test_connection.py`

> ⚠️ Este teste só funciona DEPOIS de o `schema_mqt_d04.sql` ter sido corrido no Supabase SQL Editor.

---

## TABELAS SUPABASE (as 6 do MQT)

Estas tabelas são NOVAS — adicionadas ao schema Supabase existente (SSOT).  
**Não modificar** as tabelas existentes do SSOT: `projects`, `blocks`, `floors`, `zones`, `geo_horizons`, `project_files`.

```
mqt_snapshots     — 1 snapshot por projecto × fase × entrega
mqt_artigos       — artigos individuais do Excel MQT
mqt_indices       — índices calculados (kg/m³, m²/m³) + flags + notas
elemento_map      — mapeamento (capitulo, sufixo) → elemento_tipo
capitulo_map      — capítulo → tipo de quantidade + unidade (seed estático)
jsj_precos_ref    — preços unitários de referência JSJ
```

Chave de ligação ao SSOT: `mqt_snapshots.project_id` = FK para `projects.id` (SSOT).

### Lógica de mapeamento artigos (IMPORTANTE)

O código de artigo do Excel (ex: `5.5.4`, `6.2.4.1`, `7.1.1.2`) é parseado assim:

```
5.5.4   → capitulo=5, subcapitulo=5.5, sufixo=4
6.2.4.1 → capitulo=6, subcapitulo=6.2, sufixo=4.1
7.1.1.2 → capitulo=7, subcapitulo=7.1, sufixo=1.2
```

- **capitulo** = 1º segmento → identifica tipo de trabalho (5=betão, 6=cofragem, 7=aço)
- **subcapitulo** = 1º + 2º segmento → classe de material (ex: C25/30, C30/37)
- **sufixo** = restantes segmentos → identifica o elemento estrutural

O sufixo é a chave para o `elemento_map`. O mesmo sufixo `.4` no capítulo `5` mapeia sempre para `PILAR` independentemente da classe de betão.

### Lista de elemento_tipo válidos

```
FUNDACAO | MACIÇO_ESTACAS | LAJE_FUNDO | VIGA_FUND | PILAR | NUCLEO |
PAREDE | PAREDE_PISC | PAREDE_RES | CONTENCAO | VIGA | LAJE_MACICA |
LAJE_ALIG | RAMPA | LAJE_PISC | BANDA | CAPITEL | MURETE | ESCADA |
MASSAME | MACIÇO | FUND_INDIRETA | PRE_ESFORCO | MOLDE_ALIG | OUTRO
```

### Capítulos do MQT JSJ

| cap | tipo | unidade | descrição |
|-----|------|---------|-----------|
| 3 | mov_terras | m³ | Movimentação de Terras |
| 4 | fund_indireta | ml/m³/kg | Fundações Indirectas |
| 5 | betao | m³ | Betões |
| 6 | cofragem | m² | Cofragem |
| 7 | aco_ord | kg | Armaduras Ordinárias |
| 8 | aco_activo | kg | Armaduras Activas (Pré-esforço) |
| 9 | prefabricado | m³ | Pré-fabricados |
| 10 | aco_estrutural | kg | Estrutura Metálica |
| 11 | madeira | m³ | Estrutura de Madeira |
| 12 | pavimento | m²/m³ | Pavimento Térreo |
| 13 | molde_alig | m² | Moldes de Aligeiramento |
| 15 | diversos | vg | Diversos |

---

## DIMENSÕES DOS ARTIGOS

Cada artigo tem 3 dimensões de quantidade:
- `quant_a` — Fundações (pisos tipo `fundacao`)
- `quant_b` — Piso térreo (pisos tipo `terreo`)
- `quant_c` — Pisos elevados (pisos tipo `elevado` + `cobertura`)
- `quant_total` — Soma automática (a + b + c)

Esta separação permite benchmark por zona estrutural, não apenas por projecto global.

---

## FICHEIROS EXTERNOS A COPIAR (fornecidos separadamente)

Após criar a estrutura de pastas, copiar estes ficheiros para os locais indicados:

| Ficheiro | Destino |
|---------|---------|
| `schema_mqt_d04.sql` | `database/schema_mqt_d04.sql` |
| `KB-01_Contexto_Empresa.md` | Referência só — não entra no repo |
| `KB-03_Decisoes_Arquitecturais.md` | Referência só — não entra no repo |
| `KB-05_Indices_Referencia.md` | Referência só — não entra no repo |

> O `schema_mqt_d04.sql` deve ser corrido no **Supabase SQL Editor** ANTES de qualquer teste de ligação.

---

## PRÓXIMOS PASSOS DE DESENVOLVIMENTO (por ordem)

1. **[AGORA]** Setup estrutura + Git + .env + requirements → testar ligação Supabase
2. **[A SEGUIR]** Implementar `parser_excel.py` — ler Excel MQT real (projecto Amorim)
3. **[A SEGUIR]** Implementar `mapper_artigos.py` — parse artigo_cod + lookup elemento_map
4. **[A SEGUIR]** Implementar `ingest_mqt.py` — pipeline completo Excel → Supabase
5. **[DEPOIS]** `validation/indices.py` — cálculo índices + flags automáticas
6. **[DEPOIS]** Streamlit dashboard básico — visualização snapshots + índices

---

## NOTAS IMPORTANTES

- **Python mínimo:** 3.11
- **Supabase key:** Usar `service_role` key (não `anon`) — o pipeline corre server-side
- **Excel:** O ficheiro Excel MQT fica SEMPRE no servidor da empresa. O script lê via path (local ou UNC). Nunca mover o Excel para o repo.
- **Dados reais:** Nunca commitar Excels reais. A pasta `data/` está no `.gitignore`.
- **Tabelas SSOT:** `projects`, `blocks`, `floors`, `zones`, `geo_horizons`, `project_files` — **só leitura** para este sistema.
- **Estimativas de custo** (preço × quantidade) são calculadas on-the-fly — nunca persistidas na DB.
- **Alerta de preços:** Se `jsj_precos_ref.data_actualizacao` > 12 meses, mostrar aviso de preço desactualizado na interface.
