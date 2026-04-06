# pyright: reportMissingImports=false, reportMissingModuleSource=false

"""
Configurações globais do projeto.
Carrega variáveis do .env e expõe como constantes tipadas.
"""

import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Diretórios ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"

for d in [DATA_RAW_DIR, DATA_PROCESSED_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Banco de dados ──────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "financial.db"))

# ── Período de coleta ────────────────────────────────────────────────────────
START_DATE: str = os.getenv("START_DATE", "2020-01-01")
END_DATE: str = os.getenv("END_DATE", "") or date.today().strftime("%Y-%m-%d")

# ── Ativos ───────────────────────────────────────────────────────────────────
TICKERS_B3: list[str] = [
    t.strip()
    for t in os.getenv(
        "TICKERS_B3",
        "PETR4.SA,VALE3.SA,ITUB4.SA,BBDC4.SA,WEGE3.SA"
    ).split(",")
    if t.strip()
]

TICKERS_US: list[str] = [
    t.strip()
    for t in os.getenv("TICKERS_US", "SPY,QQQ").split(",")
    if t.strip()
]

ALL_TICKERS: list[str] = TICKERS_B3 + TICKERS_US

# ── Banco Central (SGS) ──────────────────────────────────────────────────────
BCB_SERIES = {
    "selic_diaria":  int(os.getenv("BCB_SELIC_CODE", 11)),
    "ipca_mensal":   int(os.getenv("BCB_IPCA_CODE", 433)),
    "usd_brl":       int(os.getenv("BCB_USD_BRL_CODE", 1)),
}

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", str(LOGS_DIR / "pipeline.log"))

# ── Constantes financeiras ───────────────────────────────────────────────────
TRADING_DAYS_YEAR = 252   # dias de negociação por ano (B3)
RISK_FREE_LABEL = "selic_diaria"
