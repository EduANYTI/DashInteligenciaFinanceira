# %% [markdown]
# # 💼 Análise de Portfólio e Risco
# **Financial Intelligence Dashboard**
#
# Análise de portfólio com alocação equalizada,
# fronteira eficiente simplificada
# e comparativo de estratégias de risco.

# %%
import sys
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.utils.config import DATA_PROCESSED_DIR, TRADING_DAYS_YEAR
from dashinteligenciafinanceira.src.etl.metrics import (
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    max_drawdown,
)

sys.path.insert(0, "..")
warnings.filterwarnings("ignore")

print("Setup concluído ✓")

# %% [markdown]
# ## 1. Carregamento

# %%
stocks = pd.read_csv(
    DATA_PROCESSED_DIR / "stocks_clean.csv", parse_dates=["date"]
)
metrics = pd.read_csv(DATA_PROCESSED_DIR / "metrics.csv")

prices = stocks.pivot_table(index="date", columns="ticker", values="close")
returns = stocks.pivot_table(
    index="date", columns="ticker", values="return_daily"
)
returns_clean = returns.dropna()

print(f"Ativos disponíveis: {list(returns_clean.columns)}")
print(
    f"Período: {returns_clean.index.min().date()} "
    f"→ {returns_clean.index.max().date()}"
)

# %% [markdown]
# ## 2. Portfólio Equalizado (Equal Weight)

# %%
n = returns_clean.shape[1]
weights_eq = np.array([1 / n] * n)

# Retorno diário do portfólio
port_return_daily = (returns_clean * weights_eq).sum(axis=1)

# Retorno acumulado
port_cumulative = (1 + port_return_daily).cumprod() * 100

# Métricas do portfólio
port_ann_return = annualized_return((port_cumulative / 100).rename("port"))
port_ann_vol = annualized_volatility(port_return_daily)
port_sharpe = sharpe_ratio(port_return_daily)
port_drawdown = max_drawdown(port_cumulative)

print("📊 Métricas do Portfólio Equalizado:")
print(f"  Retorno anualizado : {port_ann_return * 100:.2f}%")
print(f"  Volatilidade anual : {port_ann_vol * 100:.2f}%")
print(f"  Sharpe Ratio       : {port_sharpe:.3f}")
print(f"  Máximo Drawdown    : {port_drawdown * 100:.2f}%")

# %%
# Compara portfólio com ativos individuais
fig = go.Figure()

for ticker in prices.columns:
    p = prices[ticker].dropna()
    if len(p) > 10:
        norm = p / p.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm.values,
            name=ticker,
            mode="lines",
            line=dict(width=1, dash="dot"),
            opacity=0.6,
        ))

fig.add_trace(go.Scatter(
    x=port_cumulative.index,
    y=port_cumulative.values,
    name="Portfólio Equalizado",
    mode="lines",
    line=dict(width=3, color="#E63946"),
))

fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.4)
fig.update_layout(
    title="Portfólio Equalizado vs Ativos Individuais (Base 100)",
    xaxis_title="Data",
    yaxis_title="Índice de Retorno",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=500,
)
fig.show()

# %% [markdown]
# ## 3. Fronteira Eficiente (Monte Carlo)

# %%
N_PORTFOLIOS = 3_000
n_assets = len(returns_clean.columns)

mean_returns = returns_clean.mean()
cov_matrix = returns_clean.cov()

np.random.seed(42)
port_returns_mc, port_vols_mc, port_sharpes_mc, weights_mc = [], [], [], []

for _ in range(N_PORTFOLIOS):
    w = np.random.dirichlet(np.ones(n_assets))
    r = np.dot(w, mean_returns) * TRADING_DAYS_YEAR
    v = np.sqrt(w @ cov_matrix.values @ w) * np.sqrt(TRADING_DAYS_YEAR)
    s = r / v if v != 0 else 0
    port_returns_mc.append(r)
    port_vols_mc.append(v)
    port_sharpes_mc.append(s)
    weights_mc.append(w)

mc_df = pd.DataFrame({
    "retorno": port_returns_mc,
    "volatilidade": port_vols_mc,
    "sharpe": port_sharpes_mc,
})

# Portfólio de máximo Sharpe
best_idx = int(mc_df["sharpe"].to_numpy().argmax())
best = mc_df.iloc[best_idx]
best_weights = weights_mc[best_idx]

print("🏆 Portfólio de Máximo Sharpe (simulação):")
for ticker, w in zip(returns_clean.columns, best_weights):
    print(f"  {ticker}: {w * 100:.1f}%")
print(
    f"  Sharpe: {best['sharpe']:.3f} | "
    f"Retorno: {best['retorno'] * 100:.2f}% | "
    f"Vol: {best['volatilidade'] * 100:.2f}%"
)

# %%
fig = go.Figure()

# Scatter dos portfólios simulados
fig.add_trace(go.Scatter(
    x=mc_df["volatilidade"] * 100,
    y=mc_df["retorno"] * 100,
    mode="markers",
    marker=dict(
        size=4,
        color=mc_df["sharpe"],
        colorscale="RdYlGn",
        colorbar=dict(title="Sharpe"),
        opacity=0.6,
    ),
    name="Portfólios simulados",
    hovertemplate="Vol: %{x:.1f}%<br>Retorno: %{y:.1f}%<extra></extra>",
))

# Portfólio de máximo Sharpe
fig.add_trace(go.Scatter(
    x=[best["volatilidade"] * 100],
    y=[best["retorno"] * 100],
    mode="markers",
    marker=dict(size=18, color="red", symbol="star"),
    name="Máximo Sharpe",
))

# Ativos individuais
if not metrics.empty:
    fig.add_trace(go.Scatter(
        x=metrics["volatilidade_anual"] * 100,
        y=metrics["retorno_anualizado"] * 100,
        mode="markers+text",
        text=metrics["ticker"],
        textposition="top center",
        marker=dict(size=10, color="#264653", symbol="diamond"),
        name="Ativos individuais",
    ))

fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
fig.update_layout(
    title=f"Fronteira Eficiente — Monte Carlo ({N_PORTFOLIOS:,} portfólios)",
    xaxis_title="Volatilidade Anualizada (%)",
    yaxis_title="Retorno Anualizado (%)",
    height=550,
)
fig.show()

# %% [markdown]
# ## 4. Contribuição de Risco por Ativo

# %%
# Variância marginal de cada ativo no portfólio equalizado
port_variance = np.dot(weights_eq, np.dot(cov_matrix.values, weights_eq))
marginal_contrib = np.dot(cov_matrix.values, weights_eq)
risk_contrib = (
    weights_eq * marginal_contrib / port_variance * 100
)  # % da variância total

risk_df = pd.DataFrame({
    "ticker": returns_clean.columns,
    "peso_%": (weights_eq * 100).round(2),
    "contrib_risco_%": risk_contrib.round(2),
})
risk_df = risk_df.sort_values("contrib_risco_%", ascending=False)

fig = go.Figure(go.Bar(
    x=risk_df["ticker"],
    y=risk_df["contrib_risco_%"],
    marker_color="#E9C46A",
    text=risk_df["contrib_risco_%"].round(1).astype(str) + "%",
    textposition="outside",
))
fig.add_hline(
    y=100 / n,
    line_dash="dash",
    line_color="gray",
    annotation_text="Contribuição uniforme",
)
fig.update_layout(
    title="Contribuição ao Risco do Portfólio (Variância)",
    xaxis_title="Ativo",
    yaxis_title="% da Variância Total",
    height=400,
)
fig.show()

print("\nTabela de contribuição ao risco:")
print(risk_df.to_string(index=False))
