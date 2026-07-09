"""
frontend.py  —  InsureIQ v3 Frontend
All 5 features: What-If Optimizer, AI Report Parser, Wearable Sync, SHAP XAI, Social Benchmarking
Run: streamlit run frontend.py
"""

import streamlit as st
import requests
import random
import base64
from datetime import datetime

import database as db

st.set_page_config(
    page_title="InsureIQ v3 — Health Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
API = "http://localhost:5000"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
:root{--bg:#0a0f1e;--surface:#111827;--card:#1a2236;--border:#1e2d4a;--accent:#2563eb;--accent2:#38bdf8;--text:#e2e8f0;--muted:#64748b;--low:#22c55e;--medium:#f59e0b;--high:#ef4444;}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg) !important;color:var(--text) !important;font-family:'DM Sans',sans-serif;}
[data-testid="stSidebar"]{background:var(--surface) !important;border-right:1px solid var(--border);}
h1,h2,h3,h4{font-family:'Syne',sans-serif !important;}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.4rem 1.6rem;margin-bottom:1rem;}
.gradient-text{background:linear-gradient(135deg,#60a5fa,#38bdf8,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:'Syne',sans-serif;font-weight:800;}
.badge{display:inline-block;padding:3px 12px;border-radius:999px;font-size:.78rem;font-weight:600;}
.badge-low{background:#14532d;color:var(--low);}
.badge-medium{background:#451a03;color:var(--medium);}
.badge-high{background:#450a0a;color:var(--high);}
.badge-blue{background:#1e3a8a;color:var(--accent2);}
.badge-purple{background:#3b0764;color:#c084fc;}
[data-testid="metric-container"]{background:var(--card) !important;border:1px solid var(--border) !important;border-radius:12px !important;padding:.8rem 1rem !important;}
[data-testid="metric-container"] label{color:var(--muted) !important;}
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stSelectbox>div>div{background:var(--card) !important;border:1px solid var(--border) !important;color:var(--text) !important;border-radius:8px !important;}
.stButton>button{background:linear-gradient(135deg,#2563eb,#1d4ed8) !important;color:#fff !important;border:none !important;border-radius:8px !important;font-family:'Syne',sans-serif !important;font-weight:700 !important;}
.stButton>button:hover{opacity:.85 !important;}
hr{border-color:var(--border) !important;}
.scenario-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1rem 1.2rem;margin-bottom:.7rem;transition:border-color .2s;}
.scenario-card.winner{border-color:#22c55e;}
.timeline-item{border-left:3px solid var(--accent);padding-left:1rem;margin-bottom:1rem;}
.policy-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.2rem 1.4rem;position:relative;overflow:hidden;}
.policy-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#2563eb,#38bdf8);}
.wearable-ring{width:120px;height:120px;border-radius:50%;border:8px solid var(--border);display:flex;flex-direction:column;align-items:center;justify-content:center;margin:0 auto;}
.feature-badge{font-size:.72rem;font-weight:700;padding:2px 10px;border-radius:20px;display:inline-block;letter-spacing:.04em;}
.feature-badge-1{background:#1e3a5f;color:#60a5fa;}
.feature-badge-2{background:#3b0764;color:#c084fc;}
.feature-badge-3{background:#064e3b;color:#34d399;}
.feature-badge-4{background:#451a03;color:#fbbf24;}
.feature-badge-5{background:#1e1b4b;color:#a78bfa;}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
HEALTH_FACTS = [
    "Drinking 2L of water daily can boost metabolism by up to 30%.",
    "Walking 10,000 steps a day reduces heart disease risk by ~20%.",
    "Adults who sleep fewer than 6 hrs/night are 4x more likely to catch a cold.",
    "Strength training twice a week reduces all-cause mortality risk by 23%.",
    "Quitting smoking at 40 adds ~9 years to expected lifespan.",
    "A Mediterranean diet cuts heart attack risk by up to 30%.",
    "15 minutes of meditation daily lowers cortisol levels significantly.",
    "High blood pressure is called the silent killer — get it checked yearly.",
]

OCCUPATIONS = ["private_job","government_job","business_owner","freelancer","student","retired","unemployed"]
TIER1 = ["Mumbai","Delhi","Bangalore","Chennai","Kolkata","Hyderabad","Pune"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def is_logged_in(): return st.session_state.get("user_id") is not None
def logout():
    for k in ["user_id","username","email","page","last_prediction","wearable_data"]:
        st.session_state.pop(k, None)
    st.rerun()

def cat_color(cat):
    return {"Low":"#22c55e","Medium":"#f59e0b","High":"#ef4444"}.get(cat,"#60a5fa")
def cat_emoji(cat):
    return {"Low":"✅","Medium":"⚠️","High":"🚨"}.get(cat,"")


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown('<p class="gradient-text" style="font-size:1.6rem;margin:0">InsureIQ</p>', unsafe_allow_html=True)
        st.caption("Health Intelligence Platform v3")
        st.divider()

        if is_logged_in():
            st.markdown(f"👤 **{st.session_state.get('username')}**")
            st.caption(st.session_state.get("email",""))
            st.divider()

            pages = [
                ("🏠","Home","home"),
                ("🔮","Premium Predictor","predictor"),
                ("🎯","What-If Optimizer","optimizer"),
                ("🧬","AI Report Scanner","report"),
                ("⌚","Wearable Sync","wearable"),
                ("🌐","Community Benchmark","community"),
                ("👤","Profile","profile"),
            ]
            for icon, label, key in pages:
                if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
                    st.session_state["page"] = key
                    st.rerun()

            # Show wearable score in sidebar if synced
            if st.session_state.get("wearable_data"):
                wd = st.session_state["wearable_data"]
                st.divider()
                score = wd.get("lifestyle_score", 0)
                badge = wd.get("lifestyle_badge","—")
                color = wd.get("badge_color","#64748b")
                st.markdown(f"""
                <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.7rem;text-align:center">
                    <p style="margin:0;font-size:.72rem;color:#64748b">WEARABLE SCORE</p>
                    <p style="margin:.2rem 0;font-size:1.6rem;font-weight:800;color:{color}">{score}</p>
                    <p style="margin:0;font-size:.75rem;color:{color}">{badge}</p>
                </div>""", unsafe_allow_html=True)

            st.divider()
            if st.session_state.get("username") == "admin":
                if st.button("🛠️  Admin Panel", use_container_width=True):
                    st.session_state["page"] = "admin"
                    st.rerun()
            if st.button("🚪  Logout", use_container_width=True):
                logout()
        else:
            if st.button("🔑  Login", use_container_width=True):
                st.session_state["page"] = "login"
                st.rerun()
            if st.button("📝  Sign Up", use_container_width=True):
                st.session_state["page"] = "signup"
                st.rerun()

        st.divider()
        st.caption("v3.0 · FastAPI + Streamlit + SHAP + Claude AI")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════
def page_home():
    st.markdown('<h1 class="gradient-text">Health Intelligence Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("Your personal hub — predict, optimize, understand, and benchmark your health risk.")
    st.divider()

    # Feature highlights
    st.markdown("### What's New in v3")
    f1,f2,f3,f4,f5 = st.columns(5)
    for col, num, icon, label, cls in [
        (f1,"1","🎯","What-If Optimizer","feature-badge-1"),
        (f2,"2","🧬","AI Report Scanner","feature-badge-2"),
        (f3,"3","⌚","Wearable Sync","feature-badge-3"),
        (f4,"4","📊","SHAP Explainer","feature-badge-4"),
        (f5,"5","🌐","Social Benchmark","feature-badge-5"),
    ]:
        col.markdown(f"""
        <div class="card" style="text-align:center;padding:1rem .8rem">
            <div style="font-size:1.8rem">{icon}</div>
            <span class="feature-badge {cls}">Feature {num}</span>
            <p style="margin:.5rem 0 0;font-size:.82rem;color:#94a3b8">{label}</p>
        </div>""", unsafe_allow_html=True)

    st.divider()

    col_l, col_r = st.columns([1.1,1], gap="large")
    with col_l:
        st.markdown("### 💡 Daily Health Facts")
        for fact in random.sample(HEALTH_FACTS, 4):
            st.markdown(f'<div class="card" style="padding:.85rem 1rem"><span style="font-size:.92rem">{fact}</span></div>', unsafe_allow_html=True)
        if st.button("🔄  Refresh Facts"):
            st.rerun()

    with col_r:
        st.markdown("### 🚀 Quick Actions")
        if is_logged_in():
            actions = [
                ("🔮","Run Prediction","predictor","Get your premium category now"),
                ("🎯","Optimize Risk","optimizer","Find what changes help most"),
                ("🧬","Scan Report","report","Upload blood test PDF"),
                ("⌚","Sync Wearable","wearable","Import fitness data"),
                ("🌐","See Benchmark","community","Compare with your city"),
            ]
            for icon, label, page, desc in actions:
                c1, c2 = st.columns([3,1])
                c1.markdown(f"""
                <div style="padding:.5rem 0">
                    <strong style="font-family:'Syne',sans-serif">{icon} {label}</strong>
                    <p style="margin:0;font-size:.8rem;color:#64748b">{desc}</p>
                </div>""", unsafe_allow_html=True)
                if c2.button("Go →", key=f"home_{page}"):
                    st.session_state["page"] = page
                    st.rerun()
        else:
            st.warning("🔒 Login or Sign Up to access all features.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PREDICTOR (with SHAP XAI — Feature 4)
# ══════════════════════════════════════════════════════════════════════════════
def page_predictor():
    st.markdown('<h1 class="gradient-text">🔮 Premium Predictor</h1>', unsafe_allow_html=True)
    st.markdown('<span class="feature-badge feature-badge-4">Feature 4: SHAP Explainability included</span>', unsafe_allow_html=True)
    st.divider()

    # Pre-fill from report scanner if available
    prefill = st.session_state.get("report_prefill", {})
    if prefill:
        st.success("✅ Form pre-filled from your uploaded medical report! Review and adjust if needed.")

    with st.form("predict_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            age    = st.number_input("Age (years)",     min_value=1,   max_value=119, value=prefill.get("age", 28))
            weight = st.number_input("Weight (kg)",     min_value=10.0, max_value=250.0, value=float(prefill.get("weight", 72.0)), step=0.5)
            height = st.number_input("Height (metres)", min_value=0.5,  max_value=2.49, value=float(prefill.get("height", 1.72)), step=0.01)
        with c2:
            income = st.number_input("Income (LPA)",    min_value=0.1,  value=8.0, step=0.5)
            smoker_str = st.selectbox("Do you smoke?", ["No","Yes"], index=1 if prefill.get("smoker") else 0)
            city_options = TIER1 + ["Other — type below"]
            city_sel = st.selectbox("City", city_options)
            city = st.text_input("Enter city", value="Jaipur") if city_sel == "Other — type below" else city_sel
        with c3:
            occupation = st.selectbox("Occupation", OCCUPATIONS)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class="card" style="padding:.7rem 1rem">
                <p style="margin:0;font-size:.82rem;color:#94a3b8">
                BMI, lifestyle risk, age group & city tier are computed automatically.
                SHAP explanation is shown after prediction.
                </p>
            </div>""", unsafe_allow_html=True)
        submitted = st.form_submit_button("⚡  Predict + Explain", use_container_width=True)

    if submitted:
        payload = {
            "age": int(age), "weight": float(weight), "height": float(height),
            "income_lpa": float(income), "smoker": smoker_str == "Yes",
            "city": city, "occupation": occupation,
        }
        try:
            resp = requests.post(f"{API}/predict", json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                cat  = data["predicted_category"]
                tips = data.get("health_tips", {})
                pols = data.get("policies", [])
                derived = data.get("derived_features", {})
                shap_text = data.get("shap_explanation", [])
                shap_b64  = data.get("shap_chart_b64")

                # Store for optimizer
                st.session_state["last_prediction"] = {**payload, "bmi": derived.get("bmi"), "predicted_category": cat}

                # Result banner
                color = cat_color(cat)
                emoji = cat_emoji(cat)
                st.markdown(f"""
                <div class="card" style="border-color:{color};text-align:center;padding:2rem">
                    <p style="font-size:1rem;color:#94a3b8;margin:0">Predicted Premium Category</p>
                    <p style="font-size:3rem;font-family:'Syne',sans-serif;font-weight:800;color:{color};margin:.3rem 0">
                        {emoji} {cat.upper()}
                    </p>
                </div>""", unsafe_allow_html=True)

                # Derived metrics
                m1,m2,m3,m4 = st.columns(4)
                m1.metric("BMI", derived.get("bmi","—"))
                m2.metric("Age Group", derived.get("age_group","—").replace("_"," ").title())
                m3.metric("Lifestyle Risk", derived.get("lifestyle_risk","—").title())
                m4.metric("City Tier", f"Tier {derived.get('city_tier','—')}")

                st.divider()

                # ── SHAP Explanation (Feature 4) ──────────────────────────────
                st.markdown("### 📊 Why This Category? (AI Explanation)")
                st.markdown('<span class="feature-badge feature-badge-4">SHAP Explainable AI</span>', unsafe_allow_html=True)

                if shap_b64:
                    img_bytes = base64.b64decode(shap_b64)
                    st.image(img_bytes, use_container_width=True, caption="Feature contribution to your risk score")
                else:
                    # Text fallback
                    for i, line in enumerate(shap_text, 1):
                        color_line = "#ef4444" if "increased" in line or "raised" in line else "#22c55e"
                        st.markdown(f"""
                        <div class="card" style="padding:.7rem 1rem;border-left:3px solid {color_line};border-radius:0 8px 8px 0">
                            <span style="font-size:.9rem">{i}. {line}</span>
                        </div>""", unsafe_allow_html=True)

                st.divider()

                col_tips, col_pol = st.columns([1.1,1], gap="large")

                with col_tips:
                    st.markdown("### 🌱 Health Improvement Guide")
                    st.markdown(f"**{tips.get('headline','')}**")
                    for tip in tips.get("tips",[]):
                        st.markdown(f'<div class="card" style="padding:.65rem 1rem"><span style="font-size:.9rem">• {tip}</span></div>', unsafe_allow_html=True)

                    # Quick link to optimizer
                    st.markdown("---")
                    if st.button("🎯 Go to What-If Optimizer →"):
                        st.session_state["page"] = "optimizer"
                        st.rerun()

                with col_pol:
                    st.markdown("### 📋 Recommended Policy")
                    for pol in pols:
                        st.markdown(f"""
                        <div class="policy-card">
                            <h3 style="margin:0 0 .3rem;font-family:'Syne',sans-serif">{pol['name']}</h3>
                            <span class="badge badge-blue">Coverage: ₹{pol['coverage']}</span>
                            <p style="margin:.7rem 0 .3rem;font-size:.85rem;color:#94a3b8">Premium range: ₹{pol['premium_range']}</p>
                            <ul style="margin:.5rem 0 0;padding-left:1.2rem;font-size:.88rem">
                                {''.join(f"<li>{h}</li>" for h in pol['highlights'])}
                            </ul>
                        </div>""", unsafe_allow_html=True)

                # Save to DB
                bmi_val = derived.get("bmi", round(weight/(height**2), 2))
                db.save_prediction(st.session_state["user_id"], {**payload,"bmi":bmi_val}, cat)
                st.success("✅ Prediction saved to your profile.")
            else:
                st.error(f"API Error {resp.status_code}: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("server not running.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: WHAT-IF OPTIMIZER (Feature 1)
# ══════════════════════════════════════════════════════════════════════════════
def page_optimizer():
    st.markdown('<h1 class="gradient-text">🎯 What-If Premium Optimizer</h1>', unsafe_allow_html=True)
    st.markdown('<span class="feature-badge feature-badge-1">Feature 1: Reverse Prediction Engine</span>', unsafe_allow_html=True)
    st.markdown("Discover the minimum changes needed to drop your risk category and save money.")
    st.divider()

    last = st.session_state.get("last_prediction", {})

    with st.form("optimizer_form"):
        st.markdown("#### Your Current Profile")
        c1, c2, c3 = st.columns(3)
        with c1:
            age    = st.number_input("Age",           min_value=1,    max_value=119, value=last.get("age", 30))
            weight = st.number_input("Weight (kg)",   min_value=10.0, max_value=250.0, value=float(last.get("weight",80.0)), step=0.5)
            height = st.number_input("Height (m)",    min_value=0.5,  max_value=2.49, value=float(last.get("height",1.72)), step=0.01)
        with c2:
            income     = st.number_input("Income (LPA)",  min_value=0.1, value=float(last.get("income_lpa",8.0)), step=0.5)
            smoker_str = st.selectbox("Do you smoke?", ["No","Yes"], index=1 if last.get("smoker") else 0)
            city       = st.text_input("City", value=last.get("city","Mumbai"))
        with c3:
            occupation = st.selectbox("Occupation", OCCUPATIONS,
                                      index=OCCUPATIONS.index(last["occupation"]) if last.get("occupation") in OCCUPATIONS else 0)
            target_cat = st.selectbox("Target Category", ["Low","Medium"])

        run = st.form_submit_button("🎯  Run Optimizer", use_container_width=True)

    if run:
        payload = {
            "age": int(age), "weight": float(weight), "height": float(height),
            "income_lpa": float(income), "smoker": smoker_str == "Yes",
            "city": city, "occupation": occupation,
            "target_category": target_cat,
        }
        try:
            resp = requests.post(f"{API}/optimize", json=payload, timeout=20)
            if resp.status_code == 200:
                data     = resp.json()
                current  = data.get("current_category","—")
                target   = data.get("target_category","Low")
                scenarios = data.get("scenarios",[])

                if data.get("message"):
                    st.success(f"🎉 {data['message']}")
                    return

                # Current vs target banner
                cc = cat_color(current); tc = cat_color(target)
                st.markdown(f"""
                <div class="card" style="text-align:center;padding:1.5rem">
                    <span style="font-size:1.8rem;font-weight:800;color:{cc}">{cat_emoji(current)} {current}</span>
                    <span style="font-size:1.5rem;color:#64748b;margin:0 1rem">→</span>
                    <span style="font-size:1.8rem;font-weight:800;color:{tc}">{cat_emoji(target)} {target}</span>
                    <p style="color:#94a3b8;margin:.5rem 0 0;font-size:.85rem">
                        Showing top {len(scenarios)} pathways to reach your target
                    </p>
                </div>""", unsafe_allow_html=True)

                st.markdown("### Optimization Pathways")

                winners   = [s for s in scenarios if s["reaches_target"]]
                non_winners = [s for s in scenarios if not s["reaches_target"]]

                if winners:
                    st.markdown("#### ✅ Pathways that reach your target")
                    for s in winners:
                        diff_colors = {"Easy":"#22c55e","Medium":"#f59e0b","Hard":"#ef4444"}
                        dc = diff_colors.get(s["difficulty"],"#64748b")
                        res_color = cat_color(s["result_category"])
                        st.markdown(f"""
                        <div class="scenario-card winner">
                            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem">
                                <div>
                                    <strong style="font-family:'Syne',sans-serif;font-size:1rem">{s['action']}</strong>
                                    <p style="margin:.2rem 0 0;font-size:.82rem;color:#94a3b8">{s.get('change_detail','')}</p>
                                </div>
                                <div style="text-align:right">
                                    <span style="color:{res_color};font-weight:700;font-size:1rem">{cat_emoji(s['result_category'])} {s['result_category']}</span><br>
                                    <span style="color:#22c55e;font-size:.9rem;font-weight:600">Save ~₹{s['estimated_annual_savings']:,}/yr</span>
                                </div>
                            </div>
                            <div style="display:flex;gap:.8rem;margin-top:.6rem;flex-wrap:wrap">
                                <span style="font-size:.78rem;color:{dc};background:rgba(0,0,0,.2);padding:2px 10px;border-radius:20px">
                                    {s['difficulty']}
                                </span>
                                <span style="font-size:.78rem;color:#94a3b8">⏱ {s['timeline']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)

                if non_winners:
                    with st.expander("📉 Partial improvements (don't reach target but still help)"):
                        for s in non_winners:
                            res_color = cat_color(s["result_category"])
                            st.markdown(f"""
                            <div class="scenario-card" style="margin-bottom:.5rem">
                                <strong>{s['action']}</strong>
                                <span style="color:{res_color};margin-left:.8rem">{cat_emoji(s['result_category'])} {s['result_category']}</span>
                                <span style="color:#22c55e;margin-left:.8rem;font-size:.88rem">Save ~₹{s['estimated_annual_savings']:,}/yr</span>
                                <p style="margin:.2rem 0 0;font-size:.78rem;color:#64748b">{s.get('change_detail','')}</p>
                            </div>""", unsafe_allow_html=True)
            else:
                st.error(f"API Error: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("❌ FastAPI server not running.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: AI REPORT SCANNER (Feature 2)
# ══════════════════════════════════════════════════════════════════════════════
def page_report():
    st.markdown('<h1 class="gradient-text">🧬 AI Medical Report Scanner</h1>', unsafe_allow_html=True)
    st.markdown('<span class="feature-badge feature-badge-2">Feature 2: Claude Vision + OCR</span>', unsafe_allow_html=True)
    st.markdown("Upload your blood test PDF or image. Claude AI will extract health metrics and auto-fill the predictor form.")
    st.divider()

    col_up, col_info = st.columns([1.2, 1], gap="large")

    with col_info:
        st.markdown("""
        <div class="card">
            <h4 style="margin:0 0 .8rem">What gets extracted?</h4>
            <ul style="padding-left:1.2rem;font-size:.88rem;color:#94a3b8;line-height:2">
                <li>Age, Weight, Height → BMI</li>
                <li>Blood Sugar (Fasting)</li>
                <li>HbA1c (diabetes marker)</li>
                <li>Total Cholesterol, LDL, HDL</li>
                <li>Blood Pressure (Systolic/Diastolic)</li>
                <li>Triglycerides</li>
                <li>Smoker status (if mentioned)</li>
            </ul>
            <p style="font-size:.8rem;color:#64748b;margin:.8rem 0 0">
                Supported: PDF, JPG, PNG<br>
                Powered Aman kashyap
            </p>
        </div>""", unsafe_allow_html=True)

    with col_up:
        uploaded = st.file_uploader("Upload Blood Test Report", type=["pdf","jpg","jpeg","png"],
                                     label_visibility="collapsed")
        if uploaded:
            st.info(f"📄 File: {uploaded.name} ({uploaded.size // 1024} KB)")

            if st.button("🧬  Scan with AI", use_container_width=True):
                with st.spinner("Claude is reading your report..."):
                    try:
                        files  = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                        resp   = requests.post(f"{API}/parse-report", files=files, timeout=60)

                        if resp.status_code == 200:
                            result = resp.json()

                            if "error" in result:
                                st.error(f"Parsing error: {result['error']}")
                                return

                            st.success(f"✅ Extracted {result.get('fields_found',0)} of {result.get('fields_total',0)} fields ({result.get('confidence',0)}% confidence)")

                            # Display extracted metrics
                            metrics = result.get("extracted_metrics", {})
                            m_items = [(k.replace("_"," ").title(), v) for k, v in metrics.items() if v is not None]
                            if m_items:
                                st.markdown("#### Extracted Values")
                                cols = st.columns(3)
                                for i, (k, v) in enumerate(m_items):
                                    cols[i % 3].metric(k, v)

                            # Health flags
                            pred_fields = result.get("predictor_fields", {})
                            flags = pred_fields.get("health_flags", [])
                            if flags:
                                st.markdown("#### ⚠️ Health Risk Flags")
                                for flag in flags:
                                    st.warning(flag)

                            # Pre-fill predictor
                            fill = {k: v for k, v in pred_fields.items() if k != "health_flags" and v is not None}
                            if fill:
                                st.session_state["report_prefill"] = fill
                                st.success("✅ Predictor form pre-filled! Go to Premium Predictor.")
                                if st.button("🔮 Go to Predictor →"):
                                    st.session_state["page"] = "predictor"
                                    st.rerun()
                        else:
                            st.error(f"API Error {resp.status_code}: {resp.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ FastAPI server not running.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # Demo mode
    st.divider()
    with st.expander("🧪 Demo: Simulate report scan (no file needed)"):
        st.markdown("Simulates what a real scan would return for a sample report.")
        if st.button("Run Demo Scan"):
            demo = {
                "extracted_metrics": {"age":35,"weight":82.5,"height":1.75,"bmi":26.9,"blood_sugar_fasting":118,
                                      "hba1c":5.9,"total_cholesterol":215,"hdl":48,"ldl":145,"triglycerides":170,
                                      "systolic_bp":132,"diastolic_bp":84,"smoker": False},
                "predictor_fields": {"age":35,"weight":82.5,"height":1.75,"smoker":False,
                                     "health_flags":["Borderline blood sugar (118 mg/dL) — pre-diabetic range",
                                                     "Elevated BP (132/84 mmHg) — stage 1 hypertension",
                                                     "Borderline LDL (145 mg/dL)"]},
                "confidence": 92, "fields_found": 13, "fields_total": 13,
            }
            metrics = demo["extracted_metrics"]
            cols = st.columns(4)
            for i, (k,v) in enumerate(metrics.items()):
                if v is not None:
                    cols[i%4].metric(k.replace("_"," ").title(), v)
            for flag in demo["predictor_fields"]["health_flags"]:
                st.warning(flag)
            st.session_state["report_prefill"] = {k:v for k,v in demo["predictor_fields"].items() if k!="health_flags"}
            st.success("Demo scan complete! Form pre-filled.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: WEARABLE SYNC (Feature 3)
# ══════════════════════════════════════════════════════════════════════════════
def page_wearable():
    st.markdown('<h1 class="gradient-text">⌚ Digital Twin Wearable Sync</h1>', unsafe_allow_html=True)
    st.markdown('<span class="feature-badge feature-badge-3">Feature 3: Lifestyle Intelligence</span>', unsafe_allow_html=True)
    st.markdown("Sync your fitness data to get a lifestyle discount on your premium prediction.")
    st.divider()

    uid = st.session_state["user_id"]
    wd  = st.session_state.get("wearable_data")

    col_btn, col_info = st.columns([1, 1.5], gap="large")

    with col_btn:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2rem">
            <div style="font-size:3rem">⌚</div>
            <h3>Connect Wearable</h3>
            <p style="color:#94a3b8;font-size:.85rem">Simulates 30 days of Google Fit / Apple Health data.</p>
        </div>""", unsafe_allow_html=True)

        if st.button("🔄  Sync Now (Mock Google Fit)", use_container_width=True):
            with st.spinner("Syncing 30 days of fitness data..."):
                try:
                    resp = requests.get(f"{API}/wearable/{uid}", timeout=10)
                    if resp.status_code == 200:
                        st.session_state["wearable_data"] = resp.json()
                        st.success("✅ Synced successfully!")
                        st.rerun()
                    else:
                        st.error("Sync failed")
                except:
                    # Offline fallback
                    from wearable import get_wearable_summary
                    st.session_state["wearable_data"] = get_wearable_summary(uid)
                    st.rerun()

    with col_info:
        if wd:
            score  = wd.get("lifestyle_score", 0)
            badge  = wd.get("lifestyle_badge","—")
            color  = wd.get("badge_color","#64748b")
            disc   = wd.get("discount_pct", 0)

            # Score ring visual
            st.markdown(f"""
            <div style="text-align:center;padding:1rem">
                <div style="display:inline-block;border:8px solid {color};border-radius:50%;width:130px;height:130px;
                            display:flex;flex-direction:column;align-items:center;justify-content:center;margin:0 auto">
                    <span style="font-size:2.2rem;font-weight:800;color:{color}">{score}</span>
                    <span style="font-size:.72rem;color:{color}">/ 100</span>
                </div>
                <p style="margin:.8rem 0 0;font-size:1rem;font-weight:700;color:{color}">{badge}</p>
                <p style="color:#94a3b8;font-size:.82rem">{wd.get('days_synced',30)} days synced · Last: {wd.get('last_sync','—')}</p>
            </div>""", unsafe_allow_html=True)

        else:
            st.info("Sync your wearable data to see your lifestyle score here.")

    if wd:
        st.divider()
        # Metrics
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Avg Daily Steps", f"{wd.get('avg_steps',0):,}")
        m2.metric("Avg Sleep",       f"{wd.get('avg_sleep_hours',0)} hrs")
        m3.metric("Resting HR",      f"{wd.get('avg_resting_hr',0)} bpm")
        m4.metric("Active Minutes",  f"{wd.get('avg_active_min',0)} min/day")

        # Discount card
        disc = wd.get("discount_pct", 0)
        disc_color = "#22c55e" if disc >= 10 else "#f59e0b" if disc >= 5 else "#ef4444"
        st.markdown(f"""
        <div class="card" style="border-color:{disc_color};text-align:center;padding:1.5rem">
            <p style="color:#94a3b8;margin:0">Your Lifestyle Discount</p>
            <p style="font-size:2.5rem;font-weight:800;color:{disc_color};margin:.3rem 0">{disc}% OFF</p>
            <p style="color:#94a3b8;font-size:.85rem">Applied to your next premium prediction</p>
        </div>""", unsafe_allow_html=True)

        # Insights
        st.markdown("### Insights")
        for insight in wd.get("insights", []):
            st.markdown(f'<div class="card" style="padding:.7rem 1rem"><span style="font-size:.9rem">💡 {insight}</span></div>', unsafe_allow_html=True)

        # 7-day table
        st.markdown("### Last 7 Days Activity")
        daily = wd.get("daily_records", [])
        if daily:
            import pandas as pd
            df = pd.DataFrame(daily)[["date","steps","sleep_hours","resting_hr","active_minutes"]]
            df.columns = ["Date","Steps","Sleep (hrs)","Resting HR","Active Min"]
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Apply to last prediction
        if st.session_state.get("last_prediction"):
            st.divider()
            st.markdown("### Apply Discount to Your Last Prediction")
            last_cat = st.session_state["last_prediction"].get("predicted_category","Medium")
            if st.button(f"Apply {disc}% Lifestyle Discount to '{last_cat}' result"):
                try:
                    r = requests.post(f"{API}/wearable/apply-discount",
                                      json={"predicted_category": last_cat, "discount_pct": disc}, timeout=10)
                    if r.status_code == 200:
                        res = r.json()
                        adj = res["adjusted_category"]
                        save = res["estimated_savings"]
                        if res["category_upgraded"]:
                            st.success(f"🎉 Category upgraded: {last_cat} → {adj}! Estimated savings: ₹{save:,}/year")
                        else:
                            st.info(f"Category stays {adj} with discount. Estimated savings: ₹{save:,}/year on premium.")
                except:
                    st.error("Could not apply discount. Make sure FastAPI is running.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SOCIAL BENCHMARKING (Feature 5)
# ══════════════════════════════════════════════════════════════════════════════
def page_community():
    st.markdown('<h1 class="gradient-text">🌐 Community Health Benchmark</h1>', unsafe_allow_html=True)
    st.markdown('<span class="feature-badge feature-badge-5">Feature 5: Hyper-Local Social Intelligence</span>', unsafe_allow_html=True)
    st.markdown("See how you compare to others in your city and age group — anonymously.")
    st.divider()

    uid  = st.session_state["user_id"]
    last = st.session_state.get("last_prediction", {})

    col_form, col_result = st.columns([1, 1.5], gap="large")

    with col_form:
        city = st.text_input("Your City", value=last.get("city","Mumbai"))
        age  = st.number_input("Your Age", min_value=18, max_value=100, value=last.get("age", 28))
        if st.button("📊  Get My Benchmark", use_container_width=True):
            try:
                resp = requests.get(f"{API}/benchmark/{uid}", params={"city": city, "age": age}, timeout=10)
                if resp.status_code == 200:
                    st.session_state["benchmark_data"] = resp.json()
                    st.rerun()
            except:
                st.error("FastAPI not running. Using local DB fallback.")
                # Local fallback
                all_preds  = db.get_all_predictions_flat()
                user_preds = db.get_user_predictions(uid, limit=1)
                if not user_preds:
                    st.warning("Make a prediction first!")
                    return
                user_cat   = user_preds[0]["predicted_category"]
                cat_score  = {"Low":100,"Medium":50,"High":0}
                user_score = cat_score.get(user_cat, 50)
                city_preds = [p for p in all_preds if p.get("city","").lower()==city.lower()] or all_preds
                age_preds  = [p for p in all_preds if abs((p.get("age") or 0)-age)<=5]

                def pctile(preds):
                    if not preds: return None
                    scores = [cat_score.get(p["predicted_category"],50) for p in preds]
                    return int(sum(1 for s in scores if s<=user_score)/len(scores)*100)

                total = len(all_preds)
                dist  = {cat:{"count":sum(1 for p in all_preds if p["predicted_category"]==cat),
                               "pct":round(sum(1 for p in all_preds if p["predicted_category"]==cat)/total*100) if total else 0}
                         for cat in ["Low","Medium","High"]}
                st.session_state["benchmark_data"] = {
                    "user_category": user_cat,
                    "city_percentile": pctile(city_preds),
                    "age_percentile":  pctile(age_preds),
                    "total_users": total,
                    "city_sample": len(city_preds),
                    "age_sample":  len(age_preds),
                    "category_dist": dist,
                    "trend_message": None,
                    "city": city,
                    "age_cohort": f"users aged {max(18,age-5)}-{age+5}",
                }
                st.rerun()

    with col_result:
        bd = st.session_state.get("benchmark_data")
        if not bd:
            st.markdown("""
            <div class="card" style="text-align:center;padding:2rem;color:#64748b">
                <p style="font-size:2rem">🌐</p>
                <p>Enter your city and age to see how you compare</p>
            </div>""", unsafe_allow_html=True)
            return

        if bd.get("message"):
            st.info(bd["message"])
            return

        user_cat    = bd.get("user_category","—")
        city_pctile = bd.get("city_percentile")
        age_pctile  = bd.get("age_percentile")
        color       = cat_color(user_cat)

        st.markdown(f"""
        <div class="card" style="border-color:{color};text-align:center;padding:1.5rem">
            <p style="color:#94a3b8;margin:0;font-size:.85rem">Your current risk category</p>
            <p style="font-size:2rem;font-weight:800;color:{color};margin:.3rem 0">{cat_emoji(user_cat)} {user_cat}</p>
        </div>""", unsafe_allow_html=True)

        m1, m2 = st.columns(2)
        if city_pctile is not None:
            pctile_color = "#22c55e" if city_pctile >= 70 else "#f59e0b" if city_pctile >= 40 else "#ef4444"
            m1.markdown(f"""
            <div class="card" style="text-align:center">
                <p style="color:#94a3b8;font-size:.8rem;margin:0">Healthier than in {bd.get('city','your city')}</p>
                <p style="font-size:2rem;font-weight:800;color:{pctile_color};margin:.2rem 0">{city_pctile}%</p>
                <p style="color:#64748b;font-size:.78rem;margin:0">of {bd.get('city_sample',0)} users</p>
            </div>""", unsafe_allow_html=True)

        if age_pctile is not None:
            pctile_color = "#22c55e" if age_pctile >= 70 else "#f59e0b" if age_pctile >= 40 else "#ef4444"
            m2.markdown(f"""
            <div class="card" style="text-align:center">
                <p style="color:#94a3b8;font-size:.8rem;margin:0">Healthier than in your age group</p>
                <p style="font-size:2rem;font-weight:800;color:{pctile_color};margin:.2rem 0">{age_pctile}%</p>
                <p style="color:#64748b;font-size:.78rem;margin:0">{bd.get('age_cohort','')}</p>
            </div>""", unsafe_allow_html=True)

        # Category distribution
        dist = bd.get("category_dist",{})
        if dist:
            st.markdown("#### Platform-wide Distribution")
            for cat, info in dist.items():
                dc = cat_color(cat)
                pct = info.get("pct",0)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:.7rem;margin:.3rem 0">
                    <span style="width:70px;color:{dc};font-weight:700">{cat}</span>
                    <div style="flex:1;background:#1a2236;border-radius:6px;height:10px">
                        <div style="width:{pct}%;background:{dc};height:100%;border-radius:6px"></div>
                    </div>
                    <span style="color:#94a3b8;font-size:.82rem">{info.get('count',0)} users ({pct}%)</span>
                </div>""", unsafe_allow_html=True)

        if bd.get("trend_message"):
            st.info(f"📈 {bd['trend_message']}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROFILE
# ══════════════════════════════════════════════════════════════════════════════
def page_profile():
    uid   = st.session_state["user_id"]
    user  = db.get_user_by_id(uid)
    stats = db.get_prediction_stats(uid)
    hist  = db.get_user_predictions(uid, limit=8)

    st.markdown('<h1 class="gradient-text">👤 User Profile</h1>', unsafe_allow_html=True)
    st.divider()

    p1, p2 = st.columns([1,2], gap="large")
    with p1:
        st.markdown(f"""
        <div class="card" style="text-align:center;padding:2rem">
            <div style="font-size:3.5rem">👤</div>
            <h2 style="font-family:'Syne',sans-serif;margin:.5rem 0 .2rem">{user['username']}</h2>
            <p style="color:#94a3b8;margin:0">{user['email']}</p>
            <p style="color:#475569;margin:.5rem 0 0;font-size:.8rem">Member since {user['created_at'][:10]}</p>
        </div>""", unsafe_allow_html=True)

    with p2:
        s1,s2,s3 = st.columns(3)
        s1.metric("Total Predictions",  stats["total"])
        s2.metric("Latest Category",    stats["latest_category"] or "—")
        s3.metric("Last Predicted",     stats["latest_date"] or "—")

        dist = stats.get("distribution",{})
        if dist:
            st.markdown("**Category Breakdown**")
            total = stats["total"] or 1
            for cat, cnt in dist.items():
                dc  = cat_color(cat)
                pct = int(cnt/total*100)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:.7rem;margin:.3rem 0">
                    <span style="width:70px;color:{dc};font-weight:700">{cat}</span>
                    <div style="flex:1;background:#1a2236;border-radius:6px;height:10px">
                        <div style="width:{pct}%;background:{dc};height:100%;border-radius:6px"></div>
                    </div>
                    <span style="color:#94a3b8;font-size:.82rem">{cnt} ({pct}%)</span>
                </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📜 Prediction History")
    if not hist:
        st.info("No predictions yet. Go to the Premium Predictor to get started!")
    else:
        for rec in hist:
            cat   = rec["predicted_category"]
            badge = f"badge-{cat.lower()}"
            color = cat_color(cat)
            ts    = rec["created_at"][:16].replace("T"," ")
            st.markdown(f"""
            <div class="timeline-item" style="border-color:{color}">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h4 style="margin:0">{ts}</h4>
                    <span class="badge {badge}">{cat}</span>
                </div>
                <p style="margin:.2rem 0 0;font-size:.82rem;color:#94a3b8">
                    Age {rec['age']} · BMI {(rec['bmi'] or 0):.1f} · {(rec['occupation'] or '—').replace('_',' ').title()} ·
                    {'Smoker' if rec['smoker'] else 'Non-smoker'} · {rec['city']} · ₹{rec['income_lpa']} LPA
                </p>
            </div>""", unsafe_allow_html=True)

    st.divider()
    with st.expander("🔒 Change Password"):
        with st.form("pw_form"):
            new_pw  = st.text_input("New Password",     type="password")
            conf_pw = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Update Password"):
                if not new_pw:         st.error("Password cannot be empty.")
                elif new_pw != conf_pw: st.error("Passwords do not match.")
                elif len(new_pw) < 6:  st.error("Min 6 characters.")
                else:
                    db.update_password(uid, new_pw)
                    st.success("Password updated!")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADMIN
# ══════════════════════════════════════════════════════════════════════════════
def page_admin():
    if st.session_state.get("username") != "admin":
        st.error("⛔ Access denied.")
        return
    st.markdown('<h1 class="gradient-text">🛠️ Admin Panel</h1>', unsafe_allow_html=True)
    st.divider()
    users = db.get_all_users()
    preds = db.get_all_predictions_admin()
    c1,c2 = st.columns(2)
    c1.metric("Total Users",       len(users))
    c2.metric("Total Predictions", len(preds))
    st.markdown("### All Users")
    st.dataframe(users, use_container_width=True)
    st.markdown("### All Predictions")
    st.dataframe(preds, use_container_width=True)


# ── Auth Pages ────────────────────────────────────────────────────────────────
def page_login():
    st.markdown('<h1 class="gradient-text">🔑 Login</h1>', unsafe_allow_html=True)
    col, _ = st.columns([1.2,1])
    with col:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            sub = st.form_submit_button("Login", use_container_width=True)
        if sub:
            if not username or not password:
                st.error("Fill in all fields.")
            else:
                user = db.authenticate_user(username, password)
                if user:
                    st.session_state.update({"user_id":user["id"],"username":user["username"],"email":user["email"],"page":"home"})
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        st.markdown("---")
        if st.button("Create Account →"):
            st.session_state["page"] = "signup"; st.rerun()


def page_signup():
    st.markdown('<h1 class="gradient-text">📝 Create Account</h1>', unsafe_allow_html=True)
    col, _ = st.columns([1.2,1])
    with col:
        with st.form("signup_form"):
            username = st.text_input("Username")
            email    = st.text_input("Email")
            password = st.text_input("Password (min 6 chars)", type="password")
            confirm  = st.text_input("Confirm Password",       type="password")
            sub = st.form_submit_button("Create Account", use_container_width=True)
        if sub:
            errors = []
            if len(username) < 3:   errors.append("Username must be at least 3 characters.")
            if "@" not in email:    errors.append("Enter a valid email.")
            if len(password) < 6:   errors.append("Password must be at least 6 characters.")
            if password != confirm:  errors.append("Passwords do not match.")
            for e in errors: st.error(e)
            if not errors:
                result = db.create_user(username, email, password)
                if result["success"]:
                    st.success("Account created! Please login.")
                    st.session_state["page"] = "login"; st.rerun()
                else:
                    st.error(result["error"])
        st.markdown("---")
        if st.button("Already have an account? Login →"):
            st.session_state["page"] = "login"; st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────
def main():
    db.init_db()
    if "page" not in st.session_state:
        st.session_state["page"] = "login" if not is_logged_in() else "home"

    render_sidebar()

    page = st.session_state.get("page","home")
    protected = {"predictor","optimizer","report","wearable","community","profile","admin"}

    if page in protected and not is_logged_in():
        st.warning("🔒 Please login to access this page.")
        st.session_state["page"] = "login"
        st.rerun()

    dispatch = {
        "home":      page_home,
        "predictor": page_predictor,
        "optimizer": page_optimizer,
        "report":    page_report,
        "wearable":  page_wearable,
        "community": page_community,
        "profile":   page_profile,
        "admin":     page_admin,
        "login":     page_login,
        "signup":    page_signup,
    }
    dispatch.get(page, page_home)()


if __name__ == "__main__":
    main()
