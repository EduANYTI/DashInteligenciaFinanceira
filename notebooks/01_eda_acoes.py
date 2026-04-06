# pyright: reportMissingModuleSource=false

# %% [markdown]
# # 📊 Análise Exploratória de Ações (EDA)
# **Financial Intelligence Dashboard**
#
# Este notebook realiza a análise exploratória completa
# dos dados de ações coletados, cobrindo distribuição
# de retornos, sazonalidade, correlações, drawdown e comparativo
# de performance ajustada ao risco.

# %% [markdown]
# ## 0. Setup

# %%
import warnings

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px

from src.utils.config import DATA_PROCESSED_DIR
from dashinteligenciafinanceira.src.etl.metrics import (
    compute_correlation_matrix,
)

warnings.filterwarnings("ignore")

# Estilo
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"figure.dpi": 120, "figure.figsize": (14, 5)})

print("Setup concluído ✓")

# %% [markdown]
# ## 1. Carregamento dos dados

# %%
# Preços limpos
stocks = pd.read_csv(
    DATA_PROCESSED_DIR / "stocks_clean.csv", parse_dates=["date"]
)
metrics = pd.read_csv(DATA_PROCESSED_DIR / "metrics.csv")

print(f"Ações: {stocks['ticker'].nunique()} ativos | {len(stocks):,} linhas")
print(
    f"Período: {stocks['date'].min().date()} "
    f"→ {stocks['date'].max().date()}"
)
print(f"\nAtivos disponíveis: {sorted(stocks['ticker'].unique())}")

# %%
print(stocks.head(10).to_string(index=False))

# %%
# Verifica valores nulos
print("Valores nulos por coluna:")
print(stocks.isnull().sum().to_string())

# %% [markdown]
# ## 2. Retorno Acumulado (base 100)

# %%
# Cria tabela pivô de preços de fechamento
prices = stocks.pivot_table(index="date", columns="ticker", values="close")


# Normaliza para base 100 no primeiro pregão disponível
def normalize_base100(series: pd.Series) -> pd.Series:
    first_valid = series.first_valid_index()
    return series / series[first_valid] * 100


prices_norm = prices.apply(normalize_base100)

# %%
fig = go.Figure()

for ticker in prices_norm.columns:
    fig.add_trace(go.Scatter(
        x=prices_norm.index,
        y=prices_norm[ticker],
        name=ticker,
        mode="lines",
        line=dict(width=1.5),
        hovertemplate=(
            f"<b>{ticker}</b><br>"
            "Data: %{x|%d/%m/%Y}<br>"
            "Índice: %{y:.1f}<extra></extra>"
        ),
    ))

fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)

fig.update_layout(
    title="Retorno Acumulado — Base 100",
    xaxis_title="Data",
    yaxis_title="Índice de Retorno",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=500,
)
fig.show()

# %% [markdown]
# ## 3. Distribuição dos Retornos Diários

# %%
returns = stocks.pivot_table(
    index="date", columns="ticker", values="return_daily"
)

# Painel de histogramas
n_tickers = len(returns.columns)
ncols = 3
nrows = (n_tickers + ncols - 1) // ncols

fig, axes = plt.subplots(nrows, ncols, figsize=(16, nrows * 3.5))
axes = axes.flatten()

for i, ticker in enumerate(returns.columns):
    ax = axes[i]
    data = returns[ticker].dropna() * 100
    ax.hist(data, bins=60, color="#4C72B0", edgecolor="none", alpha=0.8)
    ax.axvline(
        data.mean(),
        color="red",
        linestyle="--",
        linewidth=1,
        label=f"Média: {data.mean():.2f}%",
    )
    ax.axvline(
        data.median(),
        color="orange",
        linestyle=":",
        linewidth=1,
        label=f"Mediana: {data.median():.2f}%",
    )
    ax.set_title(ticker, fontsize=11, fontweight="bold")
    ax.set_xlabel("Retorno diário (%)")
    ax.set_ylabel("Frequência")
    ax.legend(fontsize=8)

# Esconde subplots vazios
for j in range(n_tickers, len(axes)):
    axes[j].set_visible(False)

plt.suptitle(
    "Distribuição dos Retornos Diários por Ativo",
    fontsize=14,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.show()

# %%
# Estatísticas descritivas dos retornos
desc = (returns * 100).describe().T
desc.columns = [
    "n",
    "média_%",
    "std_%",
    "min_%",
    "p25_%",
    "mediana_%",
    "p75_%",
    "max_%",
]
desc = desc.round(4)
print(desc.to_string())

# %% [markdown]
# ## 4. Volatilidade Rolante (252 dias)

# %%
vol_rolling = returns.rolling(252).std() * np.sqrt(252) * 100  # %

fig = go.Figure()
for ticker in vol_rolling.columns:
    fig.add_trace(go.Scatter(
        x=vol_rolling.index,
        y=vol_rolling[ticker],
        name=ticker,
        mode="lines",
        line=dict(width=1.5),
        hovertemplate=(
            f"<b>{ticker}</b><br>"
            "%{x|%d/%m/%Y}: %{y:.1f}%<extra></extra>"
        ),
    ))

fig.update_layout(
    title="Volatilidade Anualizada Rolante (252 dias)",
    xaxis_title="Data",
    yaxis_title="Volatilidade (%)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=450,
)
fig.show()

# %% [markdown]
# ## 5. Mapa de Correlação

# %%
corr = compute_correlation_matrix(returns)

# Heatmap com Plotly (interativo)
fig = px.imshow(
    corr,
    color_continuous_scale="RdBu_r",
    zmin=-1,
    zmax=1,
    title="Matriz de Correlação de Pearson — Retornos Diários",
    aspect="auto",
)
fig.update_layout(height=550)
fig.show()

# %%
# Pares mais correlacionados (excluindo diagonal)
corr_long = (
    corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    .stack()
    .reset_index()
)
corr_long.columns = ["ativo_a", "ativo_b", "correlacao"]
corr_long = corr_long.sort_values("correlacao", ascending=False)
print("Top 10 pares mais correlacionados:")
print(corr_long.head(10).to_string(index=False))

# %% [markdown]
# ## 6. Drawdown

# %%


def calc_drawdown_series(prices: pd.Series) -> pd.Series:
    rolling_max = prices.cummax()
    return (prices - rolling_max) / rolling_max * 100


dd = prices.apply(calc_drawdown_series)

fig = go.Figure()
for ticker in dd.columns:
    fig.add_trace(go.Scatter(
        x=dd.index,
        y=dd[ticker],
        name=ticker,
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(220,50,50,0.05)",
        line=dict(width=1),
        hovertemplate=(
            f"<b>{ticker}</b><br>"
            "%{x|%d/%m/%Y}: %{y:.1f}%<extra></extra>"
        ),
    ))

fig.update_layout(
    title="Drawdown por Ativo",
    xaxis_title="Data",
    yaxis_title="Drawdown (%)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=450,
)
fig.show()

# %% [markdown]
# ## 7. Risco × Retorno (Fronteira)

# %%
if not metrics.empty:
    fig = px.scatter(
        metrics,
        x="volatilidade_anual",
        y="retorno_anualizado",
        text="ticker",
        size="sharpe_ratio",
        color="sharpe_ratio",
        color_continuous_scale="RdYlGn",
        title="Risco × Retorno Anualizado — Tamanho = Sharpe Ratio",
        labels={
            "volatilidade_anual": "Volatilidade Anualizada",
            "retorno_anualizado": "Retorno Anualizado",
            "sharpe_ratio": "Sharpe Ratio",
        },
        hover_data=["max_drawdown", "sharpe_ratio"],
    )

    fig.update_traces(textposition="top center", marker=dict(sizemin=8))
    fig.update_xaxes(tickformat=".1%")
    fig.update_yaxes(tickformat=".1%")
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(
        x=metrics["volatilidade_anual"].mean(),
        line_dash="dot",
        line_color="lightblue",
        annotation_text="Volatilidade média",
    )
    fig.update_layout(height=520)
    fig.show()

# %% [markdown]
# ## 8. Ranking Final de Métricas

# %%
if not metrics.empty:
    display_cols = [
        "ticker",
        "retorno_acumulado",
        "retorno_anualizado",
        "volatilidade_anual",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "var_95",
    ]
    df_display = metrics[display_cols].copy()

    pct_cols = [
        "retorno_acumulado",
        "retorno_anualizado",
        "volatilidade_anual",
        "max_drawdown",
        "var_95",
    ]
    for col in pct_cols:
        df_display[col] = (df_display[col] * 100).round(2).astype(str) + "%"

    df_display[["sharpe_ratio", "sortino_ratio"]] = (
        df_display[["sharpe_ratio", "sortino_ratio"]].round(2)
    )
    df_display = df_display.sort_values("sharpe_ratio", ascending=False)
    print("Ranking por Sharpe Ratio:")
    print(df_display.to_string(index=False))

# %% [markdown]
# ## 9. Sazonalidade — Retorno Médio por Mês

# %%
stocks_monthly = stocks.copy()
stocks_monthly["month"] = stocks_monthly["date"].dt.month
stocks_monthly["month_name"] = stocks_monthly["date"].dt.strftime("%b")

monthly_avg = (
    stocks_monthly.groupby(["ticker", "month", "month_name"])["return_daily"]
    .mean()
    .reset_index()
)
monthly_avg["return_pct"] = monthly_avg["return_daily"] * 100

pivot_monthly = monthly_avg.pivot_table(
    index="ticker", columns="month", values="return_pct"
)
month_labels = [
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
]
pivot_monthly.columns = month_labels[: len(pivot_monthly.columns)]

fig, ax = plt.subplots(figsize=(16, max(4, len(pivot_monthly) * 0.7)))
sns.heatmap(
    pivot_monthly,
    annot=True,
    fmt=".2f",
    cmap="RdYlGn",
    center=0,
    linewidths=0.5,
    ax=ax,
    cbar_kws={"label": "Retorno médio diário (%)"},
)
ax.set_title(
    "Sazonalidade — Retorno Médio Diário por Mês (%)",
    fontsize=13,
    fontweight="bold",
)
ax.set_xlabel("")
ax.set_ylabel("")
plt.tight_layout()
plt.show()

print(
    "\nNota: valores representam o retorno médio DIÁRIO no mês "
    "(%, não acumulado no mês)."
)
