# 📊 Financial Intelligence Dashboard

Pipeline completo de análise de dados financeiros — da ingestão de dados públicos até um dashboard interativo com insights automatizados.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-SQLite%2FPostgreSQL-green?logo=postgresql&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-yellow?logo=powerbi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 🎯 Objetivo

Construir um sistema end-to-end que:
1. Coleta dados financeiros de APIs públicas (B3, Banco Central, CVM)
2. Armazena e transforma os dados com SQL
3. Calcula métricas financeiras (Sharpe Ratio, volatilidade, retorno ajustado)
4. Expõe um dashboard interativo no Power BI / Tableau

## 🏗️ Arquitetura

```
APIs Públicas (yfinance, BCB, CVM)
        │
        ▼
  [Ingestão Python]  ──→  data/raw/
        │
        ▼
  [ETL + SQL]        ──→  data/processed/  +  SQLite DB
        │
        ▼
  [EDA Notebooks]    ──→  notebooks/
        │
        ▼
  [Dashboard]        ──→  dashboard/  (Power BI / Tableau)
```

## 📁 Estrutura do Projeto

```
financial-intelligence-dashboard/
│
├── data/
│   ├── raw/                    # Dados brutos das APIs
│   └── processed/              # Dados limpos e transformados
│
├── notebooks/
│   ├── 01_eda_acoes.ipynb      # Análise exploratória de ações
│   ├── 02_macroeconomia.ipynb  # SELIC, IPCA, câmbio
│   └── 03_portfolio.ipynb      # Análise de portfólio e risco
│
├── src/
│   ├── ingestion/
│   │   ├── fetch_stocks.py     # Coleta de ações via yfinance
│   │   ├── fetch_bcb.py        # Coleta de indicadores do BCB
│   │   └── fetch_cvm.py        # Coleta de dados da CVM
│   │
│   ├── etl/
│   │   ├── transform.py        # Limpeza e transformação
│   │   ├── metrics.py          # Cálculo de métricas financeiras
│   │   └── load_db.py          # Carregamento no banco de dados
│   │
│   └── utils/
│       ├── db.py               # Conexão com banco de dados
│       ├── logger.py           # Configuração de logs
│       └── config.py           # Configurações globais
│
├── sql/
│   ├── schema.sql              # Criação das tabelas
│   └── queries.sql             # Queries analíticas principais
│
├── tests/
│   ├── test_ingestion.py
│   └── test_metrics.py
│
├── dashboard/                  # Arquivo .pbix ou .twbx
│
├── main.py                     # Orquestrador principal
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Como executar

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/financial-intelligence-dashboard.git
cd financial-intelligence-dashboard
```

### 2. Crie e ative o ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
cp .env.example .env
# Edite o .env com suas configurações
```

### 5. Execute o pipeline completo
```bash
python main.py
```

### 6. Execute módulos individualmente
```bash
# Apenas ingestão
python main.py --step ingest

# Apenas ETL
python main.py --step etl

# Apenas métricas
python main.py --step metrics
```

## 📈 KPIs do Dashboard

| Métrica | Descrição |
|---|---|
| Retorno Acumulado | Variação % do preço em relação ao início do período |
| Volatilidade Anualizada | Desvio padrão dos retornos diários × √252 |
| Sharpe Ratio | (Retorno médio − SELIC) / Volatilidade |
| Máximo Drawdown | Maior queda do pico ao vale |
| Correlação entre ativos | Heatmap de correlação de Pearson |
| Spread SELIC vs IPCA | Juro real ao longo do tempo |

## 🗃️ Fontes de Dados

| Fonte | Dados | Acesso |
|---|---|---|
| [yfinance](https://pypi.org/project/yfinance/) | Preços históricos B3/NYSE | Python lib |
| [API BCB (SGS)](https://www.bcb.gov.br/estatisticas/exibenota/171) | SELIC, IPCA, câmbio | REST API |
| [CVM Dados Abertos](https://dados.cvm.gov.br/) | DRE, Balanço de empresas listadas | CSV download |
| [Tesouro Direto](https://www.tesourodireto.com.br/titulos/precos-e-taxas.htm) | Taxas e preços de títulos | CSV download |

## 🧰 Stack Técnica

- **Python 3.10+** — ingestão, ETL e análise
- **Pandas / NumPy** — manipulação de dados
- **yfinance** — dados de mercado
- **SQLite / PostgreSQL** — armazenamento
- **Plotly / Seaborn** — visualizações nos notebooks
- **Power BI / Tableau** — dashboard final

## 📄 Licença

MIT License — veja [LICENSE](LICENSE) para detalhes.
