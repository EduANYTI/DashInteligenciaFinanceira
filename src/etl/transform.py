"""
Módulo de transformação e limpeza dos dados brutos.

Responsabilidades:
  - Remover duplicatas e valores ausentes
  - Normalizar tipos de dados e datas
  - Calcular retornos diários
  - Padronizar nomes de colunas
"""

import pandas as pd
import numpy as np

from src.utils.config import DATA_PROCESSED_DIR
from src.utils.logger import logger


def clean_stocks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e normaliza o DataFrame de ações.

    Args:
        df: DataFrame bruto de preços (saída de fetch_stocks.py).

    Returns:
        DataFrame limpo com retornos calculados.
    """
    logger.info(f"Iniciando limpeza de ações: {len(df):,} linhas brutas")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Remove duplicatas
    df = df.drop_duplicates(subset=["date", "ticker"])
    logger.debug(f"Após deduplicação: {len(df):,} linhas")

    # Remove preços zerados ou negativos
    df = df[df["close"] > 0]

    # Remove outliers extremos (variação diária > 50% — provável erro)
    df = df.sort_values(["ticker", "date"])
    df["_pct_chg"] = df.groupby("ticker")["close"].pct_change().abs()
    outliers = df["_pct_chg"] > 0.5
    if outliers.sum() > 0:
        logger.warning(
            f"Removendo {outliers.sum()} outliers de variação extrema"
        )
    df = df[~outliers].drop(columns=["_pct_chg"])

    # Calcula retorno simples diário
    df["return_daily"] = df.groupby("ticker")["close"].pct_change()

    # Calcula log-retorno diário
    df["log_return"] = np.log(
        df["close"] / df.groupby("ticker")["close"].shift(1)
    )

    # Calcula variação do volume
    df["volume_ma5"] = (
        df.groupby("ticker")["volume"]
        .transform(lambda x: x.rolling(5, min_periods=1).mean())
    )

    df = df.dropna(subset=["close"])
    df = df.reset_index(drop=True)

    logger.info(
        f"Limpeza concluída: {len(df):,} linhas, "
        f"{df['ticker'].nunique()} ativos"
    )
    return df


def build_price_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria tabela pivô de preços de fechamento
    (linhas = datas, colunas = tickers).

    Args:
        df: DataFrame limpo de ações.

    Returns:
        DataFrame pivotado.
    """
    pivot = df.pivot_table(index="date", columns="ticker", values="close")
    pivot = pivot.sort_index()
    logger.info(
        f"Tabela pivô criada: {pivot.shape[0]} datas × "
        f"{pivot.shape[1]} ativos"
    )
    return pivot


def build_returns_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria tabela pivô de retornos diários.

    Args:
        df: DataFrame limpo de ações.

    Returns:
        DataFrame pivotado de retornos.
    """
    pivot = df.pivot_table(
        index="date", columns="ticker", values="return_daily"
    )
    return pivot.sort_index()


def normalize_macro(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza a tabela de indicadores macroeconômicos.

    Converte:
      - SELIC diária: de % ao ano para % ao dia
      - IPCA mensal: mantém como está
      - USD/BRL: mantém como está

    Args:
        df: DataFrame bruto de indicadores BCB.

    Returns:
        DataFrame normalizado.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Converte SELIC: % a.a. → taxa diária equivalente
    if "selic_diaria" in df.columns:
        # Taxa diária = (1 + taxa_anual/100)^(1/252) - 1
        df["selic_diaria_pct"] = (
            (1 + df["selic_diaria"] / 100) ** (1 / 252) - 1
        )

    # Converte IPCA: % mensal → mantém, mas cria coluna acumulada
    if "ipca_mensal" in df.columns:
        df["ipca_acumulado_12m"] = (
            (1 + df["ipca_mensal"] / 100)
            .rolling(12, min_periods=1)
            .apply(lambda x: x.prod() - 1) * 100
        )

    df = df.sort_values("date").reset_index(drop=True)
    logger.info(f"Macro normalizado: {len(df):,} linhas")
    return df


def save_processed(df: pd.DataFrame, filename: str) -> None:
    """Salva DataFrame na pasta data/processed/."""
    path = DATA_PROCESSED_DIR / filename
    df.to_csv(path, index=False)
    logger.info(f"Salvo: {path} ({len(df):,} linhas)")
