from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Tenta usar a configuração do projeto; se não der, usa caminhos padrão.
try:
    from src.utils.config import DATA_PROCESSED_DIR  # type: ignore
except Exception:
    DATA_PROCESSED_DIR = Path("data/processed")


st.set_page_config(
    page_title="Financial Intelligence Dashboard",
    layout="wide",
)


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def find_processed_file(name: str) -> Path:
    direct = Path(DATA_PROCESSED_DIR) / name
    if direct.exists():
        return direct

    fallbacks = [
        Path("data/processed") / name,
        Path("src/data/processed") / name,
        Path(name),
    ]
    for path in fallbacks:
        if path.exists():
            return path
    return direct


def coerce_date_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["date", "Date", "DATA", "data"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
            if col != "date":
                out = out.rename(columns={col: "date"})
            break
    return out


def find_ticker_column(df: pd.DataFrame) -> str | None:
    for col in ["ticker", "Ticker", "TICKER", "symbol", "ativo"]:
        if col in df.columns:
            return col
    return None


def find_metric_column(df: pd.DataFrame, preferred: list[str]) -> str | None:
    lowered = {c.lower(): c for c in df.columns}
    for name in preferred:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def show_missing_files_notice(
    metrics_path: Path,
    stocks_path: Path,
    corr_path: Path,
) -> None:
    st.warning(
        "Nenhum arquivo processado foi encontrado ainda. "
        "Rode primeiro `python main.py` para gerar os CSVs "
        "e depois execute `streamlit run app.py`."
    )
    st.code(
        f"metrics.csv -> {metrics_path}\n"
        f"stocks_clean.csv -> {stocks_path}\n"
        f"correlation_matrix.csv -> {corr_path}",
        language="text",
    )


def build_price_chart(stocks_df: pd.DataFrame, ticker_col: str) -> None:
    if stocks_df.empty or ticker_col is None:
        return

    stocks_df = coerce_date_column(stocks_df)
    price_col = find_metric_column(
        stocks_df,
        [
            "close",
            "adj close",
            "adj_close",
            "preco_fechamento",
            "price",
            "last_price",
        ],
    )
    if "date" not in stocks_df.columns or price_col is None:
        return

    tickers = sorted(
        stocks_df[ticker_col].dropna().astype(str).unique().tolist()
    )
    selected = st.multiselect(
        "Selecione os ativos para o gráfico de preços",
        options=tickers,
        default=tickers[:3],
    )
    if not selected:
        st.info(
            "Selecione pelo menos um ativo para visualizar "
            "o gráfico de preços."
        )
        return

    filtered = stocks_df[
        stocks_df[ticker_col].astype(str).isin(selected)
    ].copy()
    filtered = filtered.sort_values("date")

    fig = px.line(
        filtered,
        x="date",
        y=price_col,
        color=ticker_col,
        title="Evolução de preços",
    )
    st.plotly_chart(fig, use_container_width=True)


def build_returns_chart(stocks_df: pd.DataFrame, ticker_col: str) -> None:
    if stocks_df.empty or ticker_col is None:
        return

    stocks_df = coerce_date_column(stocks_df)
    return_col = find_metric_column(
        stocks_df,
        ["return", "daily_return", "retorno", "pct_change", "retorno_diario"],
    )
    if "date" not in stocks_df.columns or return_col is None:
        return

    tickers = sorted(
        stocks_df[ticker_col].dropna().astype(str).unique().tolist()
    )
    default_ticker = tickers[0] if tickers else None
    selected = st.selectbox(
        "Ativo para série de retornos",
        options=tickers,
        index=0 if tickers else None,
    )
    if not selected and not default_ticker:
        return

    filtered = stocks_df[
        stocks_df[ticker_col].astype(str) == str(selected)
    ].copy()
    filtered = filtered.sort_values("date")

    fig = px.bar(
        filtered,
        x="date",
        y=return_col,
        title=f"Retornos diários — {selected}",
    )
    st.plotly_chart(fig, use_container_width=True)


def build_metrics_section(
    metrics_df: pd.DataFrame,
    ticker_col: str | None,
) -> None:
    st.subheader("Métricas dos ativos")
    if metrics_df.empty:
        st.info("metrics.csv não encontrado ou vazio.")
        return

    filtered = metrics_df.copy()
    if ticker_col:
        tickers = sorted(
            filtered[ticker_col].dropna().astype(str).unique().tolist()
        )
        selected = st.multiselect(
            "Filtrar métricas por ativo",
            tickers,
            default=tickers,
        )
        if selected:
            filtered = filtered[
                filtered[ticker_col].astype(str).isin(selected)
            ]

    st.dataframe(filtered, use_container_width=True)

    numeric_cols = filtered.select_dtypes(include="number").columns.tolist()
    if ticker_col and numeric_cols:
        preferred_metric = None
        for candidate in [
            "sharpe",
            "sharpe_ratio",
            "volatility",
            "volatilidade",
            "return",
            "retorno",
        ]:
            if candidate in [c.lower() for c in numeric_cols]:
                actual = {c.lower(): c for c in numeric_cols}[candidate]
                preferred_metric = actual
                break
        metric_choice = st.selectbox(
            "Métrica para ranking",
            options=numeric_cols,
            index=(
                numeric_cols.index(preferred_metric)
                if preferred_metric in numeric_cols
                else 0
            ),
        )
        ranking = filtered[[ticker_col, metric_choice]].dropna().sort_values(
            metric_choice,
            ascending=False,
        )
        fig = px.bar(
            ranking,
            x=ticker_col,
            y=metric_choice,
            title=f"Ranking por {metric_choice}",
        )
        st.plotly_chart(fig, use_container_width=True)


def build_correlation_heatmap(corr_df: pd.DataFrame) -> None:
    st.subheader("Matriz de correlação")
    if corr_df.empty:
        st.info("correlation_matrix.csv não encontrado ou vazio.")
        return

    corr_df = corr_df.copy()

    if corr_df.columns[0].lower() in {
        "index",
        "ticker",
        "ativo",
        "unnamed: 0",
    }:
        corr_df = corr_df.set_index(corr_df.columns[0])

    numeric = corr_df.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.dropna(axis=0, how="all").dropna(axis=1, how="all")

    if numeric.empty:
        st.info("Não foi possível interpretar a matriz de correlação.")
        return

    fig = px.imshow(
        numeric,
        text_auto=False,
        aspect="auto",
        title="Correlação entre ativos",
    )
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.title("Financial Intelligence Dashboard")
    st.caption("Visualização dos arquivos processados gerados pelo pipeline.")

    metrics_path = find_processed_file("metrics.csv")
    stocks_path = find_processed_file("stocks_clean.csv")
    corr_path = find_processed_file("correlation_matrix.csv")

    metrics_df = load_csv(metrics_path)
    stocks_df = load_csv(stocks_path)
    corr_df = load_csv(corr_path)

    if metrics_df.empty and stocks_df.empty and corr_df.empty:
        show_missing_files_notice(metrics_path, stocks_path, corr_path)
        return

    metrics_df = coerce_date_column(metrics_df)
    stocks_df = coerce_date_column(stocks_df)

    metric_ticker_col = find_ticker_column(metrics_df)
    stocks_ticker_col = find_ticker_column(stocks_df)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Linhas em métricas", len(metrics_df))
    with c2:
        st.metric("Linhas em preços", len(stocks_df))
    with c3:
        if stocks_ticker_col and not stocks_df.empty:
            st.metric("Ativos únicos", stocks_df[stocks_ticker_col].nunique())
        elif metric_ticker_col and not metrics_df.empty:
            st.metric("Ativos únicos", metrics_df[metric_ticker_col].nunique())
        else:
            st.metric("Ativos únicos", 0)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Visão geral",
        "Preços",
        "Métricas",
        "Correlação",
    ])

    with tab1:
        st.subheader("Prévia dos dados")
        if not metrics_df.empty:
            st.markdown("**metrics.csv**")
            st.dataframe(metrics_df.head(10), use_container_width=True)
        if not stocks_df.empty:
            st.markdown("**stocks_clean.csv**")
            st.dataframe(stocks_df.head(10), use_container_width=True)

    with tab2:
        if stocks_ticker_col:
            build_price_chart(stocks_df, stocks_ticker_col)
            build_returns_chart(stocks_df, stocks_ticker_col)
        else:
            st.info(
                "Não foi encontrada uma coluna de ticker "
                "em stocks_clean.csv."
            )

    with tab3:
        build_metrics_section(metrics_df, metric_ticker_col)

    with tab4:
        build_correlation_heatmap(corr_df)

    with st.sidebar:
        st.header("Arquivos usados")
        st.code(
            f"{metrics_path}\n{stocks_path}\n{corr_path}",
            language="text",
        )
        st.markdown("### Como executar")
        st.code("python main.py\nstreamlit run app.py", language="bash")


if __name__ == "__main__":
    main()
