# pyright: reportMissingImports=false, reportMissingModuleSource=false

"""
Gerenciamento de conexão com o banco de dados (SQLite ou PostgreSQL).
Utiliza SQLAlchemy para abstração do banco.
"""

from contextlib import contextmanager
from typing import Generator, Literal

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.utils.config import DB_PATH
from src.utils.logger import logger


def get_engine(db_url: str | None = None) -> Engine:
    """
    Retorna engine SQLAlchemy.

    Args:
        db_url: URL de conexão. Se None, usa SQLite local definido em config.

    Returns:
        Engine SQLAlchemy configurado.
    """
    url = db_url or f"sqlite:///{DB_PATH}"
    engine = create_engine(url, echo=False)
    logger.debug(f"Engine criado: {url}")
    return engine


@contextmanager
def get_connection(db_url: str | None = None) -> Generator:
    """Context manager para conexões seguras."""
    engine = get_engine(db_url)
    with engine.connect() as conn:
        yield conn


def execute_query(sql: str, db_url: str | None = None) -> pd.DataFrame:
    """
    Executa uma query SELECT e retorna DataFrame.

    Args:
        sql: Query SQL.
        db_url: URL de conexão (opcional).

    Returns:
        DataFrame com os resultados.
    """
    engine = get_engine(db_url)
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def save_dataframe(
    df: pd.DataFrame,
    table_name: str,
    if_exists: Literal["fail", "replace", "append"] = "replace",
    db_url: str | None = None,
) -> None:
    """
    Salva um DataFrame no banco de dados.

    Args:
        df: DataFrame a ser salvo.
        table_name: Nome da tabela destino.
        if_exists: 'replace', 'append' ou 'fail'.
        db_url: URL de conexão (opcional).
    """
    engine = get_engine(db_url)
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)
    logger.info(f"Tabela '{table_name}' salva com {len(df):,} linhas.")
