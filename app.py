# pyright: reportMissingImports=false, reportMissingModuleSource=false
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
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

PX_TEMPLATE = "plotly_white"


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


def format_number(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(float(value)) >= 1_000_000:
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inject_css() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.3rem;
                padding-bottom: 1.2rem;
            }

            .main-title {
                font-size: 2.2rem;
                font-weight: 800;
                margin-bottom: 0.2rem;
                color: #0F172A;
            }

            .subtitle {
                color: #475569;
                margin-bottom: 1rem;
                font-size: 1rem;
            }

            .glass-card {
                background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 18px;
                padding: 18px 18px 14px 18px;
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
                margin-bottom: 1rem;
            }

            .metric-label {
                color: #64748B;
                font-size: 0.88rem;
                margin-bottom: 0.35rem;
            }

            .metric-value {
                color: #0F172A;
                font-size: 1.8rem;
                font-weight: 800;
                line-height: 1.1;
            }

            .metric-help {
                color: #94A3B8;
                font-size: 0.82rem;
                margin-top: 0.25rem;
            }

            [data-testid="stSidebar"] {
                border-right: 1px solid rgba(148, 163, 184, 0.18);
            }

            div[data-baseweb="tab-list"] {
                gap: 8px;
            }

            button[data-baseweb="tab"] {
                border-radius: 10px;
                padding: 10px 16px;
                border: 1px solid rgba(148, 163, 184, 0.22);
                background: #F8FAFC;
            }

            button[data-baseweb="tab"][aria-selected="true"] {
                background: linear-gradient(135deg, #DBEAFE 0%, #E0F2FE 100%);
                color: #0F172A;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def filter_by_sidebar(
    metrics_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
    metric_ticker_col: str | None,
    stocks_ticker_col: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    all_tickers: list[str] = []

    if stocks_ticker_col and not stocks_df.empty:
        all_tickers.extend(stocks_df[stocks_ticker_col].dropna().astype(str).unique().tolist())
    if metric_ticker_col and not metrics_df.empty:
        all_tickers.extend(metrics_df[metric_ticker_col].dropna().astype(str).unique().tolist())

    unique_tickers = sorted(set(all_tickers))

    with st.sidebar:
        st.markdown("## Filtros")
        selected_tickers = st.multiselect(
            "Ativos",
            options=unique_tickers,
            default=unique_tickers[:5] if len(unique_tickers) > 5 else unique_tickers,
            help="Selecione os ativos que deseja visualizar em todo o dashboard.",
        )

        date_range = None
        if "date" in stocks_df.columns and not stocks_df["date"].dropna().empty:
            min_date = stocks_df["date"].dropna().min().date()
            max_date = stocks_df["date"].dropna().max().date()
            date_range = st.date_input(
                "Período",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

    filtered_metrics = metrics_df.copy()
    filtered_stocks = stocks_df.copy()

    if selected_tickers:
        if metric_ticker_col and not filtered_metrics.empty:
            filtered_metrics = filtered_metrics[
                filtered_metrics[metric_ticker_col].astype(str).isin(selected_tickers)
            ]
        if stocks_ticker_col and not filtered_stocks.empty:
            filtered_stocks = filtered_stocks[
                filtered_stocks[stocks_ticker_col].astype(str).isin(selected_tickers)
            ]

    if (
        date_range
        and isinstance(date_range, tuple)
        and len(date_range) == 2
        and "date" in filtered_stocks.columns
    ):
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered_stocks = filtered_stocks[
            filtered_stocks["date"].between(start_date, end_date)
        ]

    return filtered_metrics, filtered_stocks, selected_tickers


def render_kpi_card(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_overview_cards(
    metrics_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
    metric_ticker_col: str | None,
    stocks_ticker_col: str | None,
) -> None:
    return_col = find_metric_column(
        stocks_df,
        ["return", "daily_return", "retorno", "pct_change", "retorno_diario"],
    )
    sharpe_col = find_metric_column(
        metrics_df,
        ["sharpe", "sharpe_ratio"],
    )

    unique_assets = 0
    if stocks_ticker_col and not stocks_df.empty:
        unique_assets = int(stocks_df[stocks_ticker_col].nunique())
    elif metric_ticker_col and not metrics_df.empty:
        unique_assets = int(metrics_df[metric_ticker_col].nunique())

    avg_return = None
    if return_col and not stocks_df.empty:
        avg_return = stocks_df[return_col].dropna().mean()

    best_asset = "—"
    if sharpe_col and metric_ticker_col and not metrics_df.empty:
        best_row = metrics_df[[metric_ticker_col, sharpe_col]].dropna()
        if not best_row.empty:
            best_asset = (
                best_row.sort_values(sharpe_col, ascending=False)
                .iloc[0][metric_ticker_col]
            )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Registros de métricas", format_number(len(metrics_df)), "Linhas disponíveis em metrics.csv")
    with c2:
        render_kpi_card("Registros de preços", format_number(len(stocks_df)), "Linhas disponíveis em stocks_clean.csv")
    with c3:
        render_kpi_card("Ativos únicos", format_number(unique_assets), "Quantidade de tickers filtrados")
    with c4:
        if avg_return is not None:
            render_kpi_card("Retorno médio diário", f"{avg_return:.2%}".replace(".", ","), "Baseado no período filtrado")
        else:
            render_kpi_card("Melhor ativo", str(best_asset), "Maior Sharpe quando disponível")


def build_price_chart(stocks_df: pd.DataFrame, ticker_col: str) -> None:
    stocks_df = coerce_date_column(stocks_df)
    price_col = find_metric_column(
        stocks_df,
        ["close", "adj close", "adj_close", "preco_fechamento", "price", "last_price"],
    )

    if "date" not in stocks_df.columns or price_col is None or stocks_df.empty:
        st.info("Não foi possível montar o gráfico de preços com os dados atuais.")
        return

    filtered = stocks_df.sort_values("date").copy()

    fig = px.line(
        filtered,
        x="date",
        y=price_col,
        color=ticker_col,
        template=PX_TEMPLATE,
        title="Evolução de preços",
        labels={"date": "Data", price_col: "Preço", ticker_col: "Ativo"},
    )
    fig.update_traces(line=dict(width=3))
    fig.update_layout(
        height=430,
        legend_title_text="Ativo",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def build_returns_chart(stocks_df: pd.DataFrame, ticker_col: str) -> None:
    stocks_df = coerce_date_column(stocks_df)
    return_col = find_metric_column(
        stocks_df,
        ["return", "daily_return", "retorno", "pct_change", "retorno_diario"],
    )

    if "date" not in stocks_df.columns or return_col is None or stocks_df.empty:
        st.info("Não foi possível montar o gráfico de retornos com os dados atuais.")
        return

    tickers = sorted(stocks_df[ticker_col].dropna().astype(str).unique().tolist())
    if not tickers:
        st.info("Nenhum ativo disponível para a série de retornos.")
        return

    selected = st.selectbox("Ativo para série de retornos", options=tickers, index=0)
    filtered = stocks_df[stocks_df[ticker_col].astype(str) == str(selected)].copy()
    filtered = filtered.sort_values("date")
    filtered["sentimento"] = filtered[return_col].apply(lambda x: "Positivo" if pd.notna(x) and x >= 0 else "Negativo")

    fig = px.bar(
        filtered,
        x="date",
        y=return_col,
        color="sentimento",
        template=PX_TEMPLATE,
        title=f"Retornos diários — {selected}",
        labels={"date": "Data", return_col: "Retorno"},
    )
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=60, b=10), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)


def build_metrics_section(metrics_df: pd.DataFrame, ticker_col: str | None) -> None:
    st.subheader("Métricas dos ativos")
    if metrics_df.empty:
        st.info("metrics.csv não encontrado ou vazio.")
        return

    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    numeric_cols = metrics_df.select_dtypes(include="number").columns.tolist()
    if ticker_col and numeric_cols:
        lowered = {c.lower(): c for c in numeric_cols}
        preferred_metric = None
        for candidate in ["sharpe", "sharpe_ratio", "volatility", "volatilidade", "return", "retorno"]:
            if candidate in lowered:
                preferred_metric = lowered[candidate]
                break

        metric_choice = st.selectbox(
            "Métrica para ranking",
            options=numeric_cols,
            index=numeric_cols.index(preferred_metric) if preferred_metric in numeric_cols else 0,
        )

        ranking = metrics_df[[ticker_col, metric_choice]].dropna().sort_values(metric_choice, ascending=False)

        fig = px.bar(
            ranking,
            x=metric_choice,
            y=ticker_col,
            orientation="h",
            template=PX_TEMPLATE,
            title=f"Ranking por {metric_choice}",
            labels={ticker_col: "Ativo", metric_choice: "Valor"},
        )
        fig.update_layout(height=max(380, 60 + (len(ranking) * 28)), margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig, use_container_width=True)


def build_correlation_heatmap(corr_df: pd.DataFrame) -> None:
    st.subheader("Matriz de correlação")
    if corr_df.empty:
        st.info("correlation_matrix.csv não encontrado ou vazio.")
        return

    corr_df = corr_df.copy()

    if corr_df.columns[0].lower() in {"index", "ticker", "ativo", "unnamed: 0"}:
        corr_df = corr_df.set_index(corr_df.columns[0])

    numeric = corr_df.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.dropna(axis=0, how="all").dropna(axis=1, how="all")

    if numeric.empty:
        st.info("Não foi possível interpretar a matriz de correlação.")
        return

    fig = px.imshow(
        numeric,
        text_auto=True,
        aspect="auto",
        template=PX_TEMPLATE,
        title="Correlação entre ativos",
        zmin=-1,
        zmax=1,
    )
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, use_container_width=True)


def build_data_preview(metrics_df: pd.DataFrame, stocks_df: pd.DataFrame) -> None:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Prévia — metrics.csv")
        if metrics_df.empty:
            st.info("Sem dados para exibir.")
        else:
            st.dataframe(metrics_df.head(10), use_container_width=True, hide_index=True)

    with c2:
        st.markdown("#### Prévia — stocks_clean.csv")
        if stocks_df.empty:
            st.info("Sem dados para exibir.")
        else:
            st.dataframe(stocks_df.head(10), use_container_width=True, hide_index=True)


def build_top_insights(
    metrics_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
    metric_ticker_col: str | None,
) -> None:
    st.subheader("Insights rápidos")

    sharpe_col = find_metric_column(metrics_df, ["sharpe", "sharpe_ratio"])
    vol_col = find_metric_column(metrics_df, ["volatility", "volatilidade"])
    return_col = find_metric_column(stocks_df, ["return", "daily_return", "retorno", "pct_change", "retorno_diario"])

    insight_1 = "Sem destaque identificado."
    insight_2 = "Sem destaque identificado."
    insight_3 = "Sem destaque identificado."

    if sharpe_col and metric_ticker_col and not metrics_df.empty:
        best = metrics_df[[metric_ticker_col, sharpe_col]].dropna().sort_values(sharpe_col, ascending=False)
        if not best.empty:
            row = best.iloc[0]
            insight_1 = f"Melhor relação risco/retorno: **{row[metric_ticker_col]}** com **{row[sharpe_col]:.2f}** de Sharpe."

    if vol_col and metric_ticker_col and not metrics_df.empty:
        vol = metrics_df[[metric_ticker_col, vol_col]].dropna().sort_values(vol_col, ascending=True)
        if not vol.empty:
            row = vol.iloc[0]
            insight_2 = f"Menor volatilidade observada em **{row[metric_ticker_col]}** com **{row[vol_col]:.2f}**."

    if return_col and not stocks_df.empty:
        avg_return = stocks_df[return_col].dropna().mean()
        if pd.notna(avg_return):
            direction = "positivo" if avg_return >= 0 else "negativo"
            insight_3 = f"O retorno médio diário do recorte atual está **{direction}** em **{avg_return:.2%}**."

    a, b, c = st.columns(3)
    with a:
        st.info(insight_1)
    with b:
        st.info(insight_2)
    with c:
        st.info(insight_3)


def main() -> None:
    inject_css()

    st.markdown('<div class="main-title">📈 Financial Intelligence Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Uma visão mais moderna, limpa e executiva dos arquivos gerados pelo pipeline.</div>',
        unsafe_allow_html=True,
    )

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

    filtered_metrics, filtered_stocks, selected_tickers = filter_by_sidebar(
        metrics_df,
        stocks_df,
        metric_ticker_col,
        stocks_ticker_col,
    )

    build_overview_cards(
        filtered_metrics,
        filtered_stocks,
        metric_ticker_col,
        stocks_ticker_col,
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Visão executiva", "Preços e retornos", "Métricas", "Correlação"]
    )

    with tab1:
        build_top_insights(filtered_metrics, filtered_stocks, metric_ticker_col)
        build_data_preview(filtered_metrics, filtered_stocks)

    with tab2:
        if stocks_ticker_col:
            c1, c2 = st.columns(2)
            with c1:
                build_price_chart(filtered_stocks, stocks_ticker_col)
            with c2:
                build_returns_chart(filtered_stocks, stocks_ticker_col)
        else:
            st.info("Não foi encontrada uma coluna de ticker em stocks_clean.csv.")

    with tab3:
        build_metrics_section(filtered_metrics, metric_ticker_col)

    with tab4:
        build_correlation_heatmap(corr_df)

    with st.sidebar:
        st.markdown("---")
        st.markdown("## Arquivos usados")
        st.code(f"{metrics_path}\n{stocks_path}\n{corr_path}", language="text")
        st.markdown("## Execução")
        st.code("python main.py\nstreamlit run app.py", language="bash")
        if selected_tickers:
            st.caption(f"{len(selected_tickers)} ativo(s) selecionado(s).")


if __name__ == "__main__":
    main()
