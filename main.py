"""
main.py — Orquestrador do pipeline Financial Intelligence Dashboard.

Uso:
  python main.py                  # pipeline completo
  python main.py --step ingest    # apenas ingestão
  python main.py --step etl       # apenas ETL + métricas
  python main.py --step verify    # verifica banco de dados
"""

import argparse
import sys
import time

import pandas as pd

from src.utils.logger import logger
from src.utils.config import DATA_PROCESSED_DIR, TICKERS_B3


def run_ingestion() -> dict:
    """Executa a etapa de ingestão de dados."""
    from src.ingestion.fetch_stocks import fetch_all_tickers, fetch_ticker_info
    from src.ingestion.fetch_bcb import fetch_all_bcb_series, build_macro_table

    logger.info("=" * 60)
    logger.info("ETAPA 1/3 — INGESTÃO DE DADOS")
    logger.info("=" * 60)

    stocks_df = fetch_all_tickers()
    tickers_info_df = fetch_ticker_info()
    bcb_series = fetch_all_bcb_series()
    macro_df = build_macro_table(bcb_series)

    return {
        "stocks_df":       stocks_df,
        "tickers_info_df": tickers_info_df,
        "macro_df":        macro_df,
    }


def run_etl(data: dict) -> dict:
    """Executa a etapa de transformação e cálculo de métricas."""
    from src.etl.transform import (
        build_price_pivot,
        build_returns_pivot,
        clean_stocks,
        normalize_macro,
        save_processed,
    )
    from src.etl.metrics import (
        compute_all_metrics,
        compute_correlation_matrix,
    )

    logger.info("=" * 60)
    logger.info("ETAPA 2/3 — ETL E MÉTRICAS")
    logger.info("=" * 60)

    stocks_df = data["stocks_df"]
    macro_df = data["macro_df"]

    if stocks_df.empty:
        logger.error("Sem dados de ações para processar.")
        return data

    # Limpeza
    clean_df = clean_stocks(stocks_df)
    prices = build_price_pivot(clean_df)
    returns = build_returns_pivot(clean_df)
    norm_macro = normalize_macro(macro_df) if not macro_df.empty else macro_df

    # Taxa livre de risco (SELIC diária)
    rf_series = None
    if "selic_diaria_pct" in norm_macro.columns:
        rf_series = norm_macro.set_index("date")["selic_diaria_pct"]
        rf_series.index = pd.to_datetime(rf_series.index)

    # Benchmark (primeiro ativo B3 disponível como proxy)
    b3_available = [t for t in TICKERS_B3 if t in prices.columns]
    benchmark = b3_available[0] if b3_available else None

    metrics_df = compute_all_metrics(prices, returns, rf_series, benchmark)
    corr_matrix = compute_correlation_matrix(returns)

    # Salva CSVs processados
    save_processed(clean_df, "stocks_clean.csv")
    save_processed(metrics_df, "metrics.csv")
    save_processed(corr_matrix.reset_index(), "correlation_matrix.csv")

    return {
        **data,
        "clean_df": clean_df,
        "metrics_df": metrics_df,
        "corr_matrix": corr_matrix,
    }


def run_load(data: dict) -> None:
    """Executa a etapa de carregamento no banco de dados."""
    from src.etl.load_db import load_all, verify_db

    logger.info("=" * 60)
    logger.info("ETAPA 3/3 — CARREGAMENTO NO BANCO")
    logger.info("=" * 60)

    load_all(
        stocks_df=data.get("clean_df"),
        tickers_info_df=data.get("tickers_info_df"),
        metrics_df=data.get("metrics_df"),
        macro_df=data.get("macro_df"),
        corr_matrix=data.get("corr_matrix"),
    )

    verify_db()


def run_pipeline() -> None:
    """Executa o pipeline completo."""
    start = time.time()
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║  Financial Intelligence Dashboard — Pipeline ║")
    logger.info("╚══════════════════════════════════════════════╝")

    data = run_ingestion()
    data = run_etl(data)
    run_load(data)

    elapsed = time.time() - start
    logger.info(f"Pipeline concluído em {elapsed:.1f}s ✓")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Financial Intelligence Dashboard — Pipeline de dados"
    )
    parser.add_argument(
        "--step",
        choices=["ingest", "etl", "load", "verify", "all"],
        default="all",
        help="Etapa do pipeline a executar (padrão: all)",
    )
    args = parser.parse_args()

    if args.step == "all":
        run_pipeline()

    elif args.step == "ingest":
        run_ingestion()

    elif args.step == "etl":
        # Tenta carregar dados já salvos
        stocks_path = DATA_PROCESSED_DIR.parent / "raw" / "stocks_raw.csv"
        macro_path = DATA_PROCESSED_DIR / "macro_indicators.csv"
        stocks_df = (
            pd.read_csv(stocks_path)
            if stocks_path.exists()
            else pd.DataFrame()
        )
        macro_df = (
            pd.read_csv(macro_path)
            if macro_path.exists()
            else pd.DataFrame()
        )
        run_etl(
            {
                "stocks_df": stocks_df,
                "macro_df": macro_df,
                "tickers_info_df": pd.DataFrame(),
            }
        )

    elif args.step == "load":
        logger.error(
            "Step 'load' exige dados processados em memória. "
            "Use '--step all' para executar o fluxo completo."
        )
        sys.exit(1)

    elif args.step == "verify":
        from src.etl.load_db import verify_db
        verify_db()

    else:
        logger.error(f"Step desconhecido: {args.step}")
        sys.exit(1)


if __name__ == "__main__":
    main()
