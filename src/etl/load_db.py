"""
Módulo de carregamento dos dados transformados no banco de dados.

Fluxo:
  data/processed/*.csv  →  SQLite (ou PostgreSQL)  →  Power BI / Tableau

Tabelas criadas:
  - dim_ticker         : metadados dos ativos
  - fact_prices        : preços históricos diários
  - fact_metrics       : métricas financeiras calculadas
  - fact_macro         : indicadores macroeconômicos BCB
  - fact_correlation   : matriz de correlação (formato longo)
"""

import pandas as pd

from src.utils.db import get_engine, save_dataframe
from src.utils.logger import logger


def load_all(
    stocks_df: pd.DataFrame | None = None,
    tickers_info_df: pd.DataFrame | None = None,
    metrics_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
    corr_matrix: pd.DataFrame | None = None,
    db_url: str | None = None,
) -> None:
    """
    Carrega todos os DataFrames no banco de dados.

    Args:
        stocks_df: Preços históricos limpos.
        tickers_info_df: Metadados dos ativos.
        metrics_df: Métricas financeiras calculadas.
        macro_df: Indicadores macroeconômicos.
        corr_matrix: Matriz de correlação (pivô).
        db_url: URL de conexão. Se None, usa config padrão.
    """
    if tickers_info_df is not None and not tickers_info_df.empty:
        save_dataframe(
            tickers_info_df,
            "dim_ticker",
            if_exists="replace",
            db_url=db_url,
        )

    if stocks_df is not None and not stocks_df.empty:
        save_dataframe(
            stocks_df,
            "fact_prices",
            if_exists="replace",
            db_url=db_url,
        )

    if metrics_df is not None and not metrics_df.empty:
        save_dataframe(
            metrics_df,
            "fact_metrics",
            if_exists="replace",
            db_url=db_url,
        )

    if macro_df is not None and not macro_df.empty:
        save_dataframe(
            macro_df,
            "fact_macro",
            if_exists="replace",
            db_url=db_url,
        )

    if corr_matrix is not None and not corr_matrix.empty:
        corr_long = _pivot_to_long(corr_matrix)
        save_dataframe(
            corr_long,
            "fact_correlation",
            if_exists="replace",
            db_url=db_url,
        )

    logger.info("Carregamento no banco de dados concluído.")


def _pivot_to_long(corr_matrix: pd.DataFrame) -> pd.DataFrame:
    """
    Converte matriz de correlação de formato pivô para formato longo.

    Útil para visualização no Power BI / Tableau.

    Ex:
      Pivô:         PETR4  VALE3
            PETR4   1.00   0.42
            VALE3   0.42   1.00

      Longo:
        ticker_a  ticker_b  correlation
        PETR4     PETR4     1.00
        PETR4     VALE3     0.42
        ...
    """
    df = corr_matrix.reset_index()
    df = df.melt(
        id_vars=df.columns[0],
        var_name="ticker_b",
        value_name="correlation",
    )
    df.columns = ["ticker_a", "ticker_b", "correlation"]
    return df


def verify_db(db_url: str | None = None) -> None:
    """Verifica as tabelas e contagens no banco de dados."""
    from sqlalchemy import inspect
    engine = get_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    logger.info(f"Tabelas no banco: {tables}")

    for table in tables:
        from src.utils.db import execute_query
        count_df = execute_query(f"SELECT COUNT(*) as n FROM {table}", db_url)
        n = count_df["n"].iloc[0]
        logger.info(f"  {table}: {n:,} linhas")
