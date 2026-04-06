# pyright: reportMissingImports=false, reportMissingModuleSource=false

"""
tests/test_metrics.py — Testes unitários para o módulo de métricas.
"""

import numpy as np
import pandas as pd
import pytest

from src.etl.metrics import (
    annualized_return,
    annualized_volatility,
    beta,
    cumulative_return,
    max_drawdown,
    sharpe_ratio,
    value_at_risk,
)


@pytest.fixture
def sample_prices() -> pd.Series:
    """Série de preços crescente simples (100 → 200 em 252 dias)."""
    return pd.Series(
        np.linspace(100, 200, 252),
        index=pd.date_range("2023-01-01", periods=252, freq="B"),
    )


@pytest.fixture
def sample_returns() -> pd.Series:
    """Retornos diários sintéticos com média e std conhecidos."""
    np.random.seed(42)
    returns = pd.Series(
        np.random.normal(0.001, 0.015, 252),
        index=pd.date_range("2023-01-01", periods=252, freq="B"),
    )
    return returns


class TestCumulativeReturn:
    def test_doubling(self, sample_prices):
        result = cumulative_return(sample_prices)
        assert abs(result - 1.0) < 0.01  # 100% de retorno

    def test_empty_series(self):
        assert np.isnan(cumulative_return(pd.Series(dtype=float)))

    def test_single_value(self):
        assert np.isnan(cumulative_return(pd.Series([100.0])))


class TestAnnualizedReturn:
    def test_positive_return(self, sample_prices):
        result = annualized_return(sample_prices)
        assert result > 0

    def test_nan_on_empty(self):
        assert np.isnan(annualized_return(pd.Series(dtype=float)))


class TestAnnualizedVolatility:
    def test_positive(self, sample_returns):
        result = annualized_volatility(sample_returns)
        assert result > 0

    def test_zero_returns(self):
        zero = pd.Series([0.0] * 252)
        result = annualized_volatility(zero)
        assert result == 0.0


class TestMaxDrawdown:
    def test_no_drawdown(self, sample_prices):
        result = max_drawdown(sample_prices)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_known_drawdown(self):
        prices = pd.Series([100, 80, 60, 80, 100])
        result = max_drawdown(prices)
        assert result == pytest.approx(-0.40, abs=0.01)


class TestVaR:
    def test_negative_var(self, sample_returns):
        result = value_at_risk(sample_returns, 0.95)
        assert result < 0

    def test_var_range(self, sample_returns):
        result = value_at_risk(sample_returns, 0.95)
        assert -0.10 < result < 0


class TestSharpeRatio:
    def test_positive_sharpe(self, sample_returns):
        result = sharpe_ratio(sample_returns, risk_free_daily=0.0)
        assert isinstance(result, float)

    def test_higher_rf_lower_sharpe(self, sample_returns):
        s1 = sharpe_ratio(sample_returns, risk_free_daily=0.0)
        s2 = sharpe_ratio(sample_returns, risk_free_daily=0.001)
        assert s1 > s2


class TestBeta:
    def test_beta_vs_itself(self, sample_returns):
        result = beta(sample_returns, sample_returns)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_beta_negative_correlation(self, sample_returns):
        inverse = -sample_returns
        result = beta(inverse, sample_returns)
        assert result < 0
