import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict, Any


def _safe_save(fig, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _numeric_stats(series: pd.Series) -> Dict[str, Any]:
    s = series.dropna().astype(float)
    if s.empty:
        return {"count": 0}
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "min": float(s.min()),
        "max": float(s.max()),
        "std": float(s.std()) if s.count() > 1 else 0.0,
    }


def _categorical_stats(series: pd.Series, top_n: int = 10) -> Dict[str, Any]:
    s = series.fillna("<NA>")
    vc = s.value_counts().head(top_n)
    return {"count": int(s.count()), "top": vc.to_dict()}


def create_graphs(df: pd.DataFrame, output_dir: str) -> List[Dict[str, Any]]:
    os.makedirs(output_dir, exist_ok=True)
    outputs: List[Dict[str, Any]] = []

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    for col in numeric_cols[:3]:
        series = df[col]
        stats = _numeric_stats(series)

        fig, ax = plt.subplots(figsize=(6, 4))
        try:
            series.dropna().astype(float).hist(bins=20, ax=ax)
        except Exception:
            ax.text(0.5, 0.5, "Unable to plot histogram", ha="center")
        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Count")
        path_hist = os.path.join(output_dir, f"hist_{col}.png")
        _safe_save(fig, path_hist)
        outputs.append({"path": path_hist, "desc": f"Histogram of {col}", "type": "hist", "column": col, "stats": stats})

        fig, ax = plt.subplots(figsize=(4, 4))
        try:
            ax.boxplot(series.dropna().astype(float))
            ax.set_title(f"Boxplot of {col}")
            path_box = os.path.join(output_dir, f"box_{col}.png")
            _safe_save(fig, path_box)
            outputs.append({"path": path_box, "desc": f"Boxplot of {col}", "type": "box", "column": col, "stats": stats})
        except Exception:
            pass

    if len(numeric_cols) >= 2:
        xcol, ycol = numeric_cols[0], numeric_cols[1]
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(df[xcol].dropna(), df[ycol].dropna(), s=12, alpha=0.6)
        ax.set_xlabel(xcol)
        ax.set_ylabel(ycol)
        ax.set_title(f"Scatter: {xcol} vs {ycol}")
        path_scatter = os.path.join(output_dir, f"scatter_{xcol}_vs_{ycol}.png")
        _safe_save(fig, path_scatter)
        outputs.append({"path": path_scatter, "desc": f"Scatter of {xcol} vs {ycol}", "type": "scatter", "column": f"{xcol}|{ycol}", "stats": {"x": _numeric_stats(df[xcol]), "y": _numeric_stats(df[ycol])}})

    for col in cat_cols[:3]:
        vc = df[col].fillna("<NA>").value_counts().head(15)
        fig, ax = plt.subplots(figsize=(6, 4))
        vc.plot(kind="bar", ax=ax)
        ax.set_title(f"Top values for {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Count")
        path = os.path.join(output_dir, f"bar_{col}.png")
        _safe_save(fig, path)
        outputs.append({"path": path, "desc": f"Top values for {col}", "type": "bar", "column": col, "stats": _categorical_stats(df[col])})

    if not outputs:
        fig, ax = plt.subplots(figsize=(4, 2))
        ax.text(0.5, 0.5, "No plottable columns", ha="center", va="center")
        ax.axis("off")
        path = os.path.join(output_dir, "placeholder.png")
        _safe_save(fig, path)
        outputs.append({"path": path, "desc": "No plottable columns", "type": "placeholder", "column": None, "stats": {}})

    return outputs
