"""
Módulo de ingestão de indicadores macroeconômicos via API do Banco Central do Brasil.

API SGS (Sistema Gerenciador de Séries Temporais):
  https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados

Principais séries:
  11  → SELIC (taxa diária)
  433 → IPCA (variação mensal)
  1   → USD/BRL (taxa de câmbio)
  12  → CDI (taxa diária)
"""

import time

import pandas as pd
import requests
from tqdm import tqdm

from src.utils.config import BCB_SERIES, DATA_RAW_DIR, END_DATE, START_DATE
from src.utils.logger import logger

BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"


def fetch_bcb_series(
    series_code: int,
    series_name: str,
    start: str = START_DATE,
    end: str = END_DATE,
) -> pd.DataFrame | None:
    """
    Busca uma série temporal do Banco Central.

    Args:
        series_code: Código da série no SGS.
        series_name: Nome descritivo da série.
        start: Data inicial no formato 'DD/MM/YYYY' ou 'YYYY-MM-DD'.
        end: Data final.

    Returns:
        DataFrame com colunas [date, {series_name}] ou None em caso de falha.
    """
    # Converte para formato DD/MM/YYYY exigido pela API do BCB
    start_fmt = _to_bcb_date(start)
    end_fmt   = _to_bcb_date(end)

    url = BCB_API_URL.format(code=series_code)
    params = {
        "formato": "json",
        "dataInicial": start_fmt,
        "dataFinal":   end_fmt,
    }

    logger.info(f"Coletando série BCB {series_code} ({series_name}): {start_fmt} → {end_fmt}")

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            logger.warning(f"Série {series_code}: sem dados no período.")
            return None

        df = pd.DataFrame(data)
        df.columns = ["date", series_name]
        df["date"] = pd.to_datetime(df["date"], dayfirst=True).dt.date
        df[series_name] = pd.to_numeric(df[series_name], errors="coerce")
        df = df.dropna(subset=[series_name])

        logger.info(f"Série {series_code}: {len(df):,} registros coletados.")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de conexão na série {series_code}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado na série {series_code}: {e}")
        return None


def fetch_all_bcb_series(
    series: dict[str, int] | None = None,
    start: str = START_DATE,
    end: str = END_DATE,
    save_csv: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Busca todas as séries BCB configuradas e salva individualmente.

    Args:
        series: Dicionário {nome: codigo}. Se None, usa BCB_SERIES do config.
        start: Data inicial.
        end: Data final.
        save_csv: Se True, salva CSVs em data/raw/.

    Returns:
        Dicionário {nome: DataFrame} com todas as séries coletadas.
    """
    series = series or BCB_SERIES
    results: dict[str, pd.DataFrame] = {}

    for name, code in tqdm(series.items(), desc="Séries BCB"):
        df = fetch_bcb_series(code, name, start, end)
        if df is not None:
            results[name] = df
            if save_csv:
                path = DATA_RAW_DIR / f"bcb_{name}.csv"
                df.to_csv(path, index=False)
                logger.info(f"CSV salvo: {path}")
        time.sleep(0.5)  # respeita rate limit da API

    return results


def build_macro_table(
    series: dict[str, pd.DataFrame] | None = None,
    save_csv: bool = True,
) -> pd.DataFrame:
    """
    Consolida todas as séries BCB em uma tabela macro com merge por data.

    Args:
        series: Dicionário {nome: DataFrame}. Se None, executa fetch.
        save_csv: Se True, salva resultado em data/processed/.

    Returns:
        DataFrame consolidado com todas as séries alinhadas por data.
    """
    if series is None:
        series = fetch_all_bcb_series()

    if not series:
        logger.error("Nenhuma série BCB disponível para consolidar.")
        return pd.DataFrame()

    # Merge progressivo por data
    result: pd.DataFrame | None = None
    for name, df in series.items():
        if result is None:
            result = df
        else:
            result = result.merge(df, on="date", how="outer")

    result = result.sort_values("date").reset_index(drop=True)

    if save_csv:
        from src.utils.config import DATA_PROCESSED_DIR
        path = DATA_PROCESSED_DIR / "macro_indicators.csv"
        result.to_csv(path, index=False)
        logger.info(f"Tabela macro salva: {path} ({len(result):,} linhas)")

    return result


def _to_bcb_date(date_str: str) -> str:
    """Converte 'YYYY-MM-DD' para 'DD/MM/YYYY' esperado pela API do BCB."""
    if "-" in date_str and date_str.index("-") == 4:
        parts = date_str.split("-")
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return date_str


if __name__ == "__main__":
    series = fetch_all_bcb_series()
    build_macro_table(series)
