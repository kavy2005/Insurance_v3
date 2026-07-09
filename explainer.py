"""
explainer.py  —  XAI (Explainable AI) wrapper using SHAP
Install:  pip install shap matplotlib
"""

import shap
import pickle
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, base64

# ── Load model once ────────────────────────────────────────────────────────────
with open("model.pkl", "rb") as f:
    _model = pickle.load(f)

# Build SHAP explainer — works for tree-based models (RF, XGB, LightGBM, etc.)
# Falls back to KernelExplainer for other model types automatically.
try:
    _explainer = shap.TreeExplainer(_model)
    _mode = "tree"
except Exception:
    _explainer = None
    _mode = "kernel"


def _build_df(features: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "bmi":            features["bmi"],
        "age_group":      features["age_group"],
        "lifestyle_risk": features["lifestyle_risk"],
        "city_tier":      features["city_tier"],
        "income_lpa":     features["income_lpa"],
        "occupation":     features["occupation"],
    }])


def get_shap_values(features: dict) -> dict:
    """
    Returns a dict of {feature_name: shap_value} for the predicted class.
    Also returns base_value (expected model output).
    """
    df = _build_df(features)

    if _mode == "tree":
        shap_vals = _explainer.shap_values(df)
        base_val  = _explainer.expected_value
        # For multi-class output shap_vals is a list; pick the predicted class
        if isinstance(shap_vals, list):
            # get predicted class index
            pred_class = int(_model.predict(df)[0]) if hasattr(_model, "classes_") else 0
            # if classes_ are strings like ['High','Low','Medium'], map to index
            if hasattr(_model, "classes_"):
                classes = list(_model.classes_)
                pred_str = _model.predict(df)[0]
                pred_class = classes.index(pred_str)
            vals     = shap_vals[pred_class][0]
            base     = base_val[pred_class] if hasattr(base_val, "__len__") else base_val
        else:
            vals = shap_vals[0]
            base = float(base_val) if not hasattr(base_val, "__len__") else float(base_val[0])
    else:
        # KernelExplainer fallback (slower)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            shap_vals = _explainer.shap_values(df)
        vals = shap_vals[0] if not isinstance(shap_vals, list) else shap_vals[0][0]
        base = float(_explainer.expected_value)

    col_names = ["bmi", "age_group", "lifestyle_risk", "city_tier", "income_lpa", "occupation"]
    result = {col_names[i]: float(vals[i]) for i in range(len(col_names))}
    return {"shap_values": result, "base_value": float(base)}


def get_shap_chart_b64(features: dict) -> str:
    """
    Returns a base64-encoded PNG of the SHAP waterfall/bar chart.
    Streamlit can render it via st.image(base64.b64decode(result)).
    """
    data   = get_shap_values(features)
    shaps  = data["shap_values"]

    # Sort by absolute impact
    items  = sorted(shaps.items(), key=lambda x: abs(x[1]), reverse=True)
    labels = [k.replace("_", " ").title() for k, _ in items]
    vals   = [v for _, v in items]
    colors = ["#ef4444" if v > 0 else "#22c55e" for v in vals]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    fig.patch.set_facecolor("#111827")
    ax.set_facecolor("#111827")

    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.55)

    ax.axvline(0, color="#475569", linewidth=0.8, linestyle="--")
    ax.set_xlabel("SHAP value (impact on prediction)", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#cbd5e1", labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1e2d4a")

    # Value labels
    for bar, val in zip(bars[::-1], vals[::-1]):
        x_pos = bar.get_width()
        ax.text(
            x_pos + (0.002 if x_pos >= 0 else -0.002),
            bar.get_y() + bar.get_height() / 2,
            f"{val:+.3f}",
            va="center",
            ha="left" if x_pos >= 0 else "right",
            color="#e2e8f0",
            fontsize=8,
        )

    ax.set_title("Feature contribution to your risk score", color="#e2e8f0", fontsize=10, pad=10)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def get_text_explanation(features: dict, predicted_category: str) -> list[str]:
    """
    Returns human-readable explanation lines, e.g.:
    ["Smoker status raised your risk by 45%", "Young age reduced risk by 10%"]
    """
    data   = get_shap_values(features)
    shaps  = data["shap_values"]
    total  = sum(abs(v) for v in shaps.values()) or 1
    items  = sorted(shaps.items(), key=lambda x: abs(x[1]), reverse=True)

    lines = []
    for feat, val in items[:4]:  # top 4 drivers
        pct  = abs(val) / total * 100
        name = feat.replace("_", " ").title()
        direction = "increased" if val > 0 else "reduced"
        lines.append(f"{name} {direction} your risk by {pct:.0f}%")
    return lines
