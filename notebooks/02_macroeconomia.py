# %% [markdown]
# # 🏦 Análise Macroeconômica — BCB
# **Financial Intelligence Dashboard**
#
# Análise dos principais indicadores macroeconômicos brasileiros:
# SELIC, IPCA, câmbio USD/BRL e suas relações com o mercado de ações.

# %%
import sys
sys.path.insert(0, "..")

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.utils.config import DATA_PROCESSED_DIR

print("Setup concluído ✓")

# %% [markdown]
# ## 1. Carregamento dos dados

# %%
macro = pd.read_csv(DATA_PROCESSED_DIR / "macro_indicators.csv", parse_dates=["date"])
stocks = pd.read_csv(DATA_PROCESSED_DIR / "stocks_clean.csv", parse_dates=["date"])

print(f"Macro: {len(macro):,} linhas | {macro['date'].min().date()} → {macro['date'].max().date()}")
macro.tail()

# %% [markdown]
# ## 2. SELIC e IPCA ao longo do tempo

# %%
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    subplot_titles=("Taxa SELIC (% a.a.)", "IPCA Mensal (%)"),
    vertical_spacing=0.08,
)

if "selic_diaria" in macro.columns:
    # Converte taxa diária para equivalente anual para visualização
    macro["selic_anual_equiv"] = ((1 + macro["selic_diaria"] / 100) ** 252 - 1) * 100
    fig.add_trace(go.Scatter(
        x=macro["date"], y=macro["selic_anual_equiv"],
        name="SELIC (% a.a.)", line=dict(color="#E63946", width=1.5),
    ), row=1, col=1)

if "ipca_mensal" in macro.columns:
    fig.add_trace(go.Bar(
        x=macro["date"], y=macro["ipca_mensal"],
        name="IPCA mensal (%)",
        marker_color=macro["ipca_mensal"].apply(lambda x: "#E63946" if x > 0 else "#2A9D8F"),
    ), row=2, col=1)

    if "ipca_acumulado_12m" in macro.columns:
        fig.add_trace(go.Scatter(
            x=macro["date"], y=macro["ipca_acumulado_12m"],
            name="IPCA acumulado 12m (%)", line=dict(color="#264653", width=2),
        ), row=2, col=1)

fig.update_layout(
    title="SELIC e IPCA — Banco Central do Brasil",
    height=600,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
fig.show()

# %% [markdown]
# ## 3. Juro Real (SELIC − IPCA)

# %%
if "selic_anual_equiv" in macro.columns and "ipca_acumulado_12m" in macro.columns:
    macro_valid = macro.dropna(subset=["selic_anual_equiv", "ipca_acumulado_12m"]).copy()
    macro_valid["juro_real"] = macro_valid["selic_anual_equiv"] - macro_valid["ipca_acumulado_12m"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=macro_valid["date"],
        y=macro_valid["juro_real"],
        name="Juro Real (%)",
        fill="tozeroy",
        fillcolor="rgba(42, 157, 143, 0.15)",
        line=dict(color="#2A9D8F", width=2),
        hovertemplate="Data: %{x|%d/%m/%Y}<br>Juro Real: %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title="Juro Real Anualizado (SELIC equiv. anual − IPCA 12m)",
        xaxis_title="Data",
        yaxis_title="Taxa (%)",
        height=400,
    )
    fig.show()

# %% [markdown]
# ## 4. Câmbio USD/BRL

# %%
if "usd_brl" in macro.columns:
    usd = macro.dropna(subset=["usd_brl"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=usd["date"],
        y=usd["usd_brl"],
        name="USD/BRL",
        line=dict(color="#E9C46A", width=1.5),
        hovertemplate="Data: %{x|%d/%m/%Y}<br>USD/BRL: R$ %{y:.4f}<extra></extra>",
    ))

    # Média móvel 30 dias
    usd["ma30"] = usd["usd_brl"].rolling(30).mean()
    fig.add_trace(go.Scatter(
        x=usd["date"], y=usd["ma30"],
        name="MM 30 dias", line=dict(color="#F4A261", width=2, dash="dash"),
    ))

    fig.update_layout(
        title="Taxa de Câmbio USD/BRL",
        xaxis_title="Data",
        yaxis_title="R$ por USD",
        height=400,
        hovermode="x unified",
    )
    fig.show()

# %% [markdown]
# ## 5. Correlação Câmbio × Ações

# %%
# Seleciona um ativo para comparar com câmbio
tickers = stocks["ticker"].unique()

if "usd_brl" in macro.columns and len(tickers) > 0:
    usd_daily = macro[["date", "usd_brl"]].dropna()
    usd_daily["usd_return"] = usd_daily["usd_brl"].pct_change()

    fig = make_subplots(
        rows=1, cols=min(3, len(tickers)),
        subplot_titles=[f"{t} vs USD/BRL" for t in tickers[:3]],
    )

    for i, ticker in enumerate(tickers[:3], start=1):
        ativo = stocks[stocks["ticker"] == ticker][["date", "return_daily"]].dropna()
        merged = ativo.merge(usd_daily[["date", "usd_return"]], on="date")

        if len(merged) > 10:
            corr_val = merged["return_daily"].corr(merged["usd_return"])
            fig.add_trace(go.Scatter(
                x=merged["usd_return"] * 100,
                y=merged["return_daily"] * 100,
                mode="markers",
                marker=dict(size=4, opacity=0.4, color="#264653"),
                name=ticker,
                hovertemplate="USD: %{x:.2f}%<br>Ação: %{y:.2f}%<extra></extra>",
            ), row=1, col=i)
            fig.update_xaxes(title_text="Retorno USD/BRL (%)", row=1, col=i)
            fig.update_yaxes(title_text=f"Retorno {ticker} (%)", row=1, col=i)

    fig.update_layout(
        title="Retornos das Ações vs Variação do Câmbio",
        height=400,
        showlegend=False,
    )
    fig.show()

# %% [markdown]
# ## 6. Tabela-resumo Macro

# %%
summary = {}

if "selic_anual_equiv" in macro.columns:
    latest_selic = macro["selic_anual_equiv"].dropna().iloc[-1]
    summary["SELIC atual (equiv. a.a.)"] = f"{latest_selic:.2f}%"

if "ipca_acumulado_12m" in macro.columns:
    latest_ipca = macro["ipca_acumulado_12m"].dropna().iloc[-1]
    summary["IPCA acumulado 12m"] = f"{latest_ipca:.2f}%"

if "juro_real" in macro.columns:
    latest_jr = macro["juro_real"].dropna().iloc[-1]
    summary["Juro real atual"] = f"{latest_jr:.2f}%"

if "usd_brl" in macro.columns:
    latest_fx = macro["usd_brl"].dropna().iloc[-1]
    summary["USD/BRL atual"] = f"R$ {latest_fx:.4f}"

df_summary = pd.DataFrame(list(summary.items()), columns=["Indicador", "Valor"])
print("\n📊 Resumo Macroeconômico:")
print(df_summary.to_string(index=False))
