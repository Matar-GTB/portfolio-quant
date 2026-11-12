"""Backtest mensuel hors échantillon. Exécuter depuis tout répertoire."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
BOUNDS = [(0.10, 0.60), (0.20, 0.70), (0, 0.25), (0, 0.20)]
REFERENCE = np.array([0.40, 0.40, 0.10, 0.10])
METHODS = ["Markowitz", "Variance minimale", "Risk parity", "Sharpe maximal", "Référence fixe"]
RF, COST, WINDOW, AVERSION = 0.02, 0.001, 60, 4

def allocation(method, mu, cov):
    if method == "Référence fixe":
        return REFERENCE.copy()

    def objective(w):
        variance = w @ cov @ w
        if method == "Variance minimale":
            return 100 * variance
        if method == "Markowitz":
            return AVERSION * variance / 2 - w @ mu
        if method == "Sharpe maximal":
            return -(w @ mu - RF) / np.sqrt(variance)
        contributions = w * (cov @ w) / variance
        return np.sum((contributions - 0.25) ** 2)

    fit = minimize(objective, REFERENCE, method="SLSQP", bounds=BOUNDS,
                   constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
                   options={"ftol": 1e-11, "maxiter": 300})
    w = fit.x
    limits = np.array(BOUNDS)
    if not (fit.success and abs(w.sum()-1) < 1e-7 and
            np.all(w >= limits[:, 0]-1e-7) and np.all(w <= limits[:, 1]+1e-7)):
        raise ValueError(f"{method}: {fit.message}")
    return w

def run():
    prices = pd.read_csv(ROOT / "data/prices.csv", index_col=0)
    assert list(prices) == ["SPY", "AGG", "GLD", "VNQ"]
    assert (prices > 0).all().all() and prices.index.is_unique
    returns = prices.pct_change().dropna()
    records, weights = [], []
    drifted = {}
    for i in range(WINDOW, len(returns)):
        history = returns.iloc[i-WINDOW:i]
        mu, cov = history.mean().to_numpy()*12, history.cov().to_numpy()*12
        realized = returns.iloc[i].to_numpy()
        for method in METHODS:
            w = allocation(method, mu, cov)
            turnover = abs(w - drifted[method]).sum() / 2 if method in drifted else 0
            gross = w @ realized
            net = (1-COST*turnover)*(1+gross)-1
            records.append([returns.index[i], method, net, turnover])
            weights.append([returns.index[i], method, *w])
            drifted[method] = w*(1+realized)/(1+gross)
    log = pd.DataFrame(records, columns=["Mois", "Stratégie", "Rendement net", "Rotation"])
    targets = pd.DataFrame(weights, columns=["Mois", "Stratégie", *prices])
    gains = log.pivot(index="Mois", columns="Stratégie", values="Rendement net")[METHODS]
    wealth = pd.concat([pd.DataFrame([[100]*len(METHODS)], columns=METHODS,
                                     index=[returns.index[WINDOW-1]]), 100*(1+gains).cumprod()])
    vol = gains.std()*np.sqrt(12)
    summary = pd.DataFrame({"Rendement annualisé": (wealth.iloc[-1]/100)**(12/len(gains))-1,
                            "Volatilité": vol, "Sharpe": (gains.mean()*12-RF)/vol,
                            "Drawdown maximal": (wealth/wealth.cummax()-1).min(),
                            "Rotation annuelle": log.groupby("Stratégie")["Rotation"].sum()*12/len(gains)})
    OUT.mkdir(exist_ok=True)
    summary.to_csv(OUT/"synthese.csv", index_label="Stratégie")
    wealth.to_csv(OUT/"capital.csv", index_label="Mois")
    targets.to_csv(OUT/"poids.csv", index=False)
    log.to_csv(OUT/"transactions.csv", index=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    wealth.set_axis(pd.to_datetime(wealth.index)).plot(ax=ax, linewidth=1.8)
    ax.set(title="Allocation multi-actifs en USD", ylabel="Capital net · base 100", xlabel="")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(OUT/"performance.png", dpi=160)
    print(summary.round(4).to_string())

if __name__ == "__main__":
    run()
