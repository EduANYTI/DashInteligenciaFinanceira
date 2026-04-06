"""
Módulo de cálculo de métricas financeiras.

Métricas implementadas:
  - Retorno acumulado e anualizado
  - Volatilidade anualizada
  - Sharpe Ratio
  - Sortino Ratio
  - Máximo Drawdown
  - Correlação entre ativos
  - Beta em relação ao benchmark
  - Value at Risk (VaR)
"""

import numpy as np
import pandas as pd

from src.utils.config import TRADING_DAYS_YEAR
from src.utils.logger import logger


# ── Retornos ──────────────────────────────────────────────────────────────────

def cumulative_return(prices: pd.Series) -> float:
    """Retorno acumulado total do período."""
    prices = prices.dropna()
    if len(prices) < 2:
        return np.nan
    return (prices.iloc[-1] / prices.iloc[0]) - 1


def annualized_return(prices: pd.Series, trading_days: int = TRADING_DAYS_YEAR) -> float:
    """
    Retorno anualizado (CAGR).

    Fórmula: (preço_final / preço_inicial)^(252/n_dias) - 1
    """
    prices = prices.dropna()
    n = len(prices)
    if n < 2:
        return np.nan
    total = prices.iloc[-1] / prices.iloc[0]
    return total ** (trading_days / n) - 1


# ── Risco ─────────────────────────────────────────────────────────────────────

def annualized_volatility(returns: pd.Series, trading_days: int = TRADING_DAYS_YEAR) -> float:
    """Volatilidade anualizada (desvio padrão dos retornos × √252)."""
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    return returns.std() * np.sqrt(trading_days)


def max_drawdown(prices: pd.Series) -> float:
    """
    Máximo Drawdown: maior queda percentual do pico ao vale.

    Retorna valor negativo (ex: -0.35 = queda máxima de 35%).
    """
    prices = prices.dropna()
    if prices.empty:
        return np.nan
    rolling_max = prices.cummax()
    drawdown = (prices - rolling_max) / rolling_max
    return drawdown.min()


def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Value at Risk histórico.

    Args:
        returns: Série de retornos diários.
        confidence: Nível de confiança (padrão 95%).

    Returns:
        VaR como número negativo (ex: -0.02 = perda máxima esperada de 2%).
    """
    returns = returns.dropna()
    if returns.empty:
        return np.nan
    return float(np.percentile(returns, (1 - confidence) * 100))


# ── Índices ajustados ao risco ────────────────────────────────────────────────

def sharpe_ratio(
    returns: pd.Series,
    risk_free_daily: float = 0.0,
    trading_days: int = TRADING_DAYS_YEAR,
) -> float:
    """
    Sharpe Ratio anualizado.

    Fórmula: (retorno_médio_diário - rf) / vol_diária × √252

    Args:
        returns: Série de retornos diários.
        risk_free_daily: Taxa livre de risco diária (taxa SELIC diária).
        trading_days: Dias de negociação por ano.

    Returns:
        Sharpe Ratio. Acima de 1.0 é considerado bom; acima de 2.0, excelente.
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    excess = returns - risk_free_daily
    if excess.std() == 0:
        return np.nan
    return (excess.mean() / excess.std()) * np.sqrt(trading_days)


def sortino_ratio(
    returns: pd.Series,
    risk_free_daily: float = 0.0,
    trading_days: int = TRADING_DAYS_YEAR,
) -> float:
    """
    Sortino Ratio — penaliza apenas retornos negativos (downside risk).

    Mais conservador que o Sharpe para ativos com assimetria.
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    excess = returns - risk_free_daily
    downside = returns[returns < 0].std()
    if downside == 0:
        return np.nan
    return (excess.mean() / downside) * np.sqrt(trading_days)


def beta(
    asset_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """
    Beta em relação ao benchmark.

    Beta > 1: ativo mais volátil que o mercado.
    Beta < 1: ativo menos volátil.
    Beta < 0: movimentos inversos ao mercado.
    """
    aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return np.nan
    a = aligned.iloc[:, 0]
    b = aligned.iloc[:, 1]
    cov = np.cov(a, b)[0, 1]
    var = np.var(b)
    return cov / var if var != 0 else np.nan


# ── Cálculo em lote ────────────────────────────────────────────────────────────

def compute_all_metrics(
    prices_pivot: pd.DataFrame,
    returns_pivot: pd.DataFrame,
    risk_free_series: pd.Series | None = None,
    benchmark_ticker: str | None = None,
) -> pd.DataFrame:
    """
    Calcula todas as métricas para cada ativo no DataFrame pivô.

    Args:
        prices_pivot: DataFrame de preços (datas × tickers).
        returns_pivot: DataFrame de retornos diários (datas × tickers).
        risk_free_series: Série de taxa livre de risco diária (SELIC).
        benchmark_ticker: Ticker do benchmark para cálculo de Beta.

    Returns:
        DataFrame com uma linha por ativo e todas as métricas como colunas.
    """
    tickers = prices_pivot.columns.tolist()
    rf_mean = risk_free_series.mean() if risk_free_series is not None else 0.0

    logger.info(f"Calculando métricas para {len(tickers)} ativos...")

    records = []
    for ticker in tickers:
        prices  = prices_pivot[ticker].dropna()
        returns = returns_pivot[ticker].dropna()

        benchmark_ret = (
            returns_pivot[benchmark_ticker].dropna()
            if benchmark_ticker and benchmark_ticker in returns_pivot.columns
            else None
        )

        record = {
            "ticker":                ticker,
            "data_inicio":           prices.index.min() if not prices.empty else None,
            "data_fim":              prices.index.max() if not prices.empty else None,
            "n_dias":                len(prices),
            "preco_inicial":         round(float(prices.iloc[0]),  2) if not prices.empty else None,
            "preco_final":           round(float(prices.iloc[-1]), 2) if not prices.empty else None,
            "retorno_acumulado":     round(cumulative_return(prices), 4),
            "retorno_anualizado":    round(annualized_return(prices), 4),
            "volatilidade_anual":    round(annualized_volatility(returns), 4),
            "max_drawdown":          round(max_drawdown(prices), 4),
            "var_95":                round(value_at_risk(returns, 0.95), 4),
            "sharpe_ratio":          round(sharpe_ratio(returns, rf_mean), 4),
            "sortino_ratio":         round(sortino_ratio(returns, rf_mean), 4),
            "beta":                  round(beta(returns, benchmark_ret), 4) if benchmark_ret is not None else None,
        }
        records.append(record)

    df = pd.DataFrame(records)
    logger.info(f"Métricas calculadas para {len(df)} ativos.")
    return df


def compute_correlation_matrix(returns_pivot: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a matriz de correlação entre todos os ativos.

    Args:
        returns_pivot: DataFrame de retornos diários.

    Returns:
        DataFrame com a matriz de correlação de Pearson.
    """
    corr = returns_pivot.corr(method="pearson")
    logger.info(f"Matriz de correlação calculada: {corr.shape[0]}×{corr.shape[1]}")
    return corr
