"""
Módulo de ingestão de preços históricos de ações via yfinance.

Fontes:
  - B3: sufixo .SA  (ex: PETR4.SA)
  - NYSE/NASDAQ: sem sufixo (ex: SPY, AAPL)
"""

from pathlib import Path

import pandas as pd
import yfinance as yf
from tqdm import tqdm

from src.utils.config import ALL_TICKERS, DATA_RAW_DIR, END_DATE, START_DATE
from src.utils.logger import logger


def fetch_single_ticker(
    ticker: str,
    start: str = START_DATE,
    end: str = END_DATE,
) -> pd.DataFrame | None:
    """
    Baixa dados históricos OHLCV de um ativo.

    Args:
        ticker: Código do ativo (ex: 'PETR4.SA').
        start: Data inicial no formato 'YYYY-MM-DD'.
        end: Data final no formato 'YYYY-MM-DD'.

    Returns:
        DataFrame com colunas [date, ticker, open, high, low, close, volume]
        ou None em caso de falha.
    """
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )

        if raw.empty:
            logger.warning(f"Sem dados para {ticker} ({start} → {end})")
            return None

        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index.name = "date"
        df = df.reset_index()
        df["ticker"] = ticker
        df["date"] = pd.to_datetime(df["date"]).dt.date

        logger.info(f"{ticker}: {len(df):,} registros ({df['date'].min()} → {df['date'].max()})")
        return df[["date", "ticker", "open", "high", "low", "close", "volume"]]

    except Exception as e:
        logger.error(f"Erro ao baixar {ticker}: {e}")
        return None


def fetch_all_tickers(
    tickers: list[str] | None = None,
    start: str = START_DATE,
    end: str = END_DATE,
    save_csv: bool = True,
) -> pd.DataFrame:
    """
    Baixa dados históricos de uma lista de ativos e consolida em um DataFrame.

    Args:
        tickers: Lista de tickers. Se None, usa ALL_TICKERS do config.
        start: Data inicial.
        end: Data final.
        save_csv: Se True, salva CSV em data/raw/.

    Returns:
        DataFrame consolidado com todos os ativos.
    """
    tickers = tickers or ALL_TICKERS
    frames: list[pd.DataFrame] = []

    logger.info(f"Iniciando coleta de {len(tickers)} ativos ({start} → {end})")

    for ticker in tqdm(tickers, desc="Baixando ativos"):
        df = fetch_single_ticker(ticker, start, end)
        if df is not None:
            frames.append(df)

    if not frames:
        logger.error("Nenhum dado coletado.")
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    if save_csv:
        output_path = DATA_RAW_DIR / "stocks_raw.csv"
        result.to_csv(output_path, index=False)
        logger.info(f"CSV salvo: {output_path} ({len(result):,} linhas)")

    return result


def fetch_ticker_info(tickers: list[str] | None = None) -> pd.DataFrame:
    """
    Coleta metadados dos ativos (setor, nome, país, etc.).

    Args:
        tickers: Lista de tickers. Se None, usa ALL_TICKERS do config.

    Returns:
        DataFrame com metadados dos ativos.
    """
    tickers = tickers or ALL_TICKERS
    records = []

    logger.info(f"Coletando metadados de {len(tickers)} ativos")

    for ticker in tqdm(tickers, desc="Metadados"):
        try:
            info = yf.Ticker(ticker).info
            records.append({
                "ticker":        ticker,
                "name":          info.get("longName", ""),
                "sector":        info.get("sector", ""),
                "industry":      info.get("industry", ""),
                "country":       info.get("country", ""),
                "currency":      info.get("currency", ""),
                "market_cap":    info.get("marketCap"),
                "exchange":      info.get("exchange", ""),
            })
        except Exception as e:
            logger.warning(f"Erro nos metadados de {ticker}: {e}")
            records.append({"ticker": ticker})

    df = pd.DataFrame(records)

    output_path = DATA_RAW_DIR / "tickers_info.csv"
    df.to_csv(output_path, index=False)
    logger.info(f"Metadados salvos: {output_path}")

    return df


if __name__ == "__main__":
    fetch_all_tickers()
    fetch_ticker_info()
