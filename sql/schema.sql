-- ============================================================
--  schema.sql — Estrutura do banco de dados
--  Financial Intelligence Dashboard
-- ============================================================

-- Dimensão: metadados dos ativos
CREATE TABLE IF NOT EXISTS dim_ticker (
    ticker       TEXT PRIMARY KEY,
    name         TEXT,
    sector       TEXT,
    industry     TEXT,
    country      TEXT,
    currency     TEXT,
    market_cap   REAL,
    exchange     TEXT
);

-- Fato: preços históricos diários
CREATE TABLE IF NOT EXISTS fact_prices (
    date         DATE    NOT NULL,
    ticker       TEXT    NOT NULL,
    open         REAL,
    high         REAL,
    low          REAL,
    close        REAL    NOT NULL,
    volume       INTEGER,
    return_daily REAL,
    log_return   REAL,
    volume_ma5   REAL,
    PRIMARY KEY (date, ticker),
    FOREIGN KEY (ticker) REFERENCES dim_ticker(ticker)
);

-- Fato: métricas financeiras calculadas por ativo
CREATE TABLE IF NOT EXISTS fact_metrics (
    ticker              TEXT    PRIMARY KEY,
    data_inicio         DATE,
    data_fim            DATE,
    n_dias              INTEGER,
    preco_inicial       REAL,
    preco_final         REAL,
    retorno_acumulado   REAL,
    retorno_anualizado  REAL,
    volatilidade_anual  REAL,
    max_drawdown        REAL,
    var_95              REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    beta                REAL,
    FOREIGN KEY (ticker) REFERENCES dim_ticker(ticker)
);

-- Fato: indicadores macroeconômicos BCB
CREATE TABLE IF NOT EXISTS fact_macro (
    date                DATE PRIMARY KEY,
    selic_diaria        REAL,
    ipca_mensal         REAL,
    usd_brl             REAL,
    selic_diaria_pct    REAL,
    ipca_acumulado_12m  REAL
);

-- Fato: correlações (formato longo para facilitar viz)
CREATE TABLE IF NOT EXISTS fact_correlation (
    ticker_a    TEXT NOT NULL,
    ticker_b    TEXT NOT NULL,
    correlation REAL,
    PRIMARY KEY (ticker_a, ticker_b)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_prices_ticker ON fact_prices(ticker);
CREATE INDEX IF NOT EXISTS idx_prices_date   ON fact_prices(date);
CREATE INDEX IF NOT EXISTS idx_macro_date    ON fact_macro(date);
