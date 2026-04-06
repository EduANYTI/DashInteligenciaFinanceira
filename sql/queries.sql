-- ============================================================
--  queries.sql — Queries analíticas principais
--  Financial Intelligence Dashboard
-- ============================================================


-- ── 1. Ranking de ativos por Sharpe Ratio ─────────────────────────────────
SELECT
    m.ticker,
    d.name                                           AS empresa,
    d.sector                                         AS setor,
    ROUND(m.sharpe_ratio,        2)                  AS sharpe_ratio,
    ROUND(m.sortino_ratio,       2)                  AS sortino_ratio,
    ROUND(m.retorno_acumulado  * 100, 2) || '%'      AS retorno_acumulado,
    ROUND(m.retorno_anualizado * 100, 2) || '%'      AS retorno_anualizado,
    ROUND(m.volatilidade_anual * 100, 2) || '%'      AS volatilidade_anual,
    ROUND(m.max_drawdown       * 100, 2) || '%'      AS max_drawdown,
    ROUND(m.var_95             * 100, 2) || '%'      AS var_95_diario
FROM fact_metrics m
LEFT JOIN dim_ticker d ON m.ticker = d.ticker
ORDER BY m.sharpe_ratio DESC NULLS LAST;


-- ── 2. Retorno acumulado por período (base 100) ────────────────────────────
WITH base AS (
    SELECT
        ticker,
        MIN(close) OVER (PARTITION BY ticker ORDER BY date
                         ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS preco_base,
        date,
        close
    FROM fact_prices
    WHERE date >= date('now', '-1 year')
),
primeiro_preco AS (
    SELECT ticker, MIN(date) AS min_date FROM fact_prices
    WHERE date >= date('now', '-1 year')
    GROUP BY ticker
),
base_preco AS (
    SELECT p.ticker, p.close AS preco_inicial
    FROM fact_prices p
    JOIN primeiro_preco pp ON p.ticker = pp.ticker AND p.date = pp.min_date
)
SELECT
    p.date,
    p.ticker,
    ROUND(p.close / bp.preco_inicial * 100, 2) AS indice_retorno
FROM fact_prices p
JOIN base_preco bp ON p.ticker = bp.ticker
WHERE p.date >= date('now', '-1 year')
ORDER BY p.ticker, p.date;


-- ── 3. Análise de correlação — top pares mais correlacionados ─────────────
SELECT
    ticker_a,
    ticker_b,
    ROUND(correlation, 4) AS correlacao
FROM fact_correlation
WHERE ticker_a < ticker_b          -- evita duplicatas
  AND ticker_a != ticker_b
ORDER BY ABS(correlation) DESC
LIMIT 20;


-- ── 4. Spread juro real (SELIC anualizada - IPCA acumulado 12m) ───────────
SELECT
    date,
    ROUND(selic_diaria,        4)  AS selic_diaria_pct_aa,
    ROUND(ipca_acumulado_12m,  2)  AS ipca_12m_pct,
    ROUND(selic_diaria - ipca_acumulado_12m / 100, 4) AS spread_juro_real,
    ROUND(usd_brl,             4)  AS usd_brl
FROM fact_macro
WHERE selic_diaria IS NOT NULL
  AND ipca_acumulado_12m IS NOT NULL
ORDER BY date DESC;


-- ── 5. Performance por setor (média das métricas) ─────────────────────────
SELECT
    d.sector                                        AS setor,
    COUNT(*)                                        AS n_ativos,
    ROUND(AVG(m.retorno_anualizado) * 100, 2)       AS retorno_anualizado_medio_pct,
    ROUND(AVG(m.volatilidade_anual) * 100, 2)       AS volatilidade_media_pct,
    ROUND(AVG(m.sharpe_ratio),       2)             AS sharpe_medio,
    ROUND(AVG(m.max_drawdown)      * 100, 2)        AS drawdown_medio_pct
FROM fact_metrics m
LEFT JOIN dim_ticker d ON m.ticker = d.ticker
WHERE d.sector IS NOT NULL AND d.sector != ''
GROUP BY d.sector
ORDER BY sharpe_medio DESC NULLS LAST;


-- ── 6. Evolução de preço e volume dos últimos 30 dias ─────────────────────
SELECT
    date,
    ticker,
    ROUND(close,        2) AS fechamento,
    ROUND(return_daily * 100, 4) AS retorno_diario_pct,
    volume,
    ROUND(volume_ma5,   0) AS volume_media_5d
FROM fact_prices
WHERE date >= date('now', '-30 days')
ORDER BY ticker, date;


-- ── 7. Dias com maior queda (top 10 piores pregões por ativo) ─────────────
SELECT
    ticker,
    date,
    ROUND(return_daily * 100, 2) AS retorno_pct,
    ROUND(close, 2) AS fechamento
FROM fact_prices
WHERE return_daily IS NOT NULL
ORDER BY return_daily ASC
LIMIT 10;


-- ── 8. Resumo executivo do portfólio ─────────────────────────────────────
SELECT
    COUNT(DISTINCT ticker)                          AS total_ativos,
    ROUND(AVG(retorno_acumulado)   * 100, 2)        AS retorno_medio_periodo_pct,
    ROUND(AVG(retorno_anualizado)  * 100, 2)        AS retorno_anualizado_medio_pct,
    ROUND(AVG(volatilidade_anual)  * 100, 2)        AS volatilidade_media_pct,
    ROUND(AVG(sharpe_ratio),        2)              AS sharpe_medio,
    ROUND(MIN(max_drawdown)        * 100, 2)        AS pior_drawdown_pct,
    (SELECT ticker FROM fact_metrics ORDER BY sharpe_ratio DESC LIMIT 1) AS melhor_sharpe,
    (SELECT ticker FROM fact_metrics ORDER BY retorno_acumulado DESC LIMIT 1) AS maior_retorno
FROM fact_metrics;
