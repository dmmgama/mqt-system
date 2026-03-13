# MQT-SYSTEM — Sistema de Ingestão e Análise de Mapas de Quantidades
**Versão:** 1.0 · **Data:** 2026-03-13  

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

## INSTALAÇÃO

### 1. Clonar repositório

```bash
git clone <repo-url>
cd mqt-system
```

### 2. Criar ambiente virtual e instalar dependências

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar credenciais

Copiar `.env.template` para `.env` e preencher com as credenciais reais:

```bash
cp .env.template .env
```

Editar `.env` com os valores correctos:
- `SUPABASE_URL` — URL da instância Supabase
- `SUPABASE_SERVICE_KEY` — Service role key (não a anon key)
- `MQT_EXCEL_PATH` — Caminho UNC ou local para os ficheiros Excel MQT

⚠️ **IMPORTANTE:** O ficheiro `.env` **nunca** deve ser commitado (está no `.gitignore`).

### 4. Executar o schema de base de dados

No Supabase SQL Editor, executar o ficheiro `database/schema_mqt_d04.sql` para criar as 6 tabelas MQT.

### 5. Testar ligação

```bash
python tests/test_connection.py
```

---

## UTILIZAÇÃO

### Ingestão de um ficheiro MQT

```bash
python pipeline/ingest_mqt.py --file "caminho/para/ficheiro.xlsx" --project-id <id>
```

### Dashboard Streamlit (futuro)

```bash
streamlit run app.py
```

---

## ESTRUTURA DO PROJECTO

```
mqt-system/
├── config/              # Configuração e settings
├── database/            # Schema SQL e seeds
├── pipeline/            # Scripts de ingestão e mapeamento
├── validation/          # Cálculo de índices e validação
├── data/samples/        # Ficheiros Excel de teste (não commitados)
└── tests/               # Testes unitários
```

---

## TABELAS SUPABASE (as 6 do MQT)

```
mqt_snapshots     — 1 snapshot por projecto × fase × entrega
mqt_artigos       — artigos individuais do Excel MQT
mqt_indices       — índices calculados (kg/m³, m²/m³) + flags + notas
elemento_map      — mapeamento (capitulo, sufixo) → elemento_tipo
capitulo_map      — capítulo → tipo de quantidade + unidade (seed estático)
jsj_precos_ref    — preços unitários de referência JSJ
```

Chave de ligação ao SSOT: `mqt_snapshots.project_id` = FK para `projects.id` (SSOT).

---

## DESENVOLVIMENTO

Consultar `README_AGENTE_IDE.md` para instruções detalhadas de setup e arquitectura.

---

## LICENÇA

Uso interno JSJ. Todos os direitos reservados.
