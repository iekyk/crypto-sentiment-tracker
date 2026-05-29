import streamlit as st
import mysql.connector
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import subprocess
import sys

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crypto Market Health Tracker",
    page_icon="📊",
    layout="wide"
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0A1628; }
    .block-container { padding-top: 1rem; }
    .top-header {
        background: #00C4CC;
        padding: 16px 24px;
        border-radius: 8px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .traffic-light-box {
        border-radius: 12px;
        padding: 24px 28px;
        margin: 12px 0 20px 0;
        border-left: 8px solid;
    }
    .tl-label {
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 3px;
        margin-bottom: 8px;
    }
    .tl-verdict {
        font-size: 28px;
        font-weight: bold;
        margin: 6px 0;
    }
    .tl-explanation {
        font-size: 14px;
        line-height: 1.7;
        margin-top: 10px;
    }
    .tl-stats {
        font-size: 12px;
        margin-top: 12px;
        opacity: 0.7;
    }
    .chapter-box {
        background: #112235;
        border-radius: 8px;
        padding: 14px 20px;
        margin: 20px 0 10px 0;
    }
    .chapter-num {
        color: #00C4CC;
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 3px;
    }
    .chapter-title {
        color: #FFFFFF;
        font-size: 20px;
        font-weight: bold;
        margin: 4px 0 0 0;
    }
    .chapter-desc {
        color: #8BA4BE;
        font-size: 12px;
        margin: 4px 0 0 0;
        line-height: 1.5;
    }
    .metric-card {
        background: #112235;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        border: 1px solid #1E3A5F;
        height: 100%;
    }
    .metric-label {
        color: #8BA4BE;
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        margin: 6px 0 2px 0;
    }
    .metric-sub { font-size: 11px; margin: 0; }
    .insight-box {
        background: #112235;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
        border: 1px solid #1E3A5F;
        line-height: 1.6;
    }
    .stat-row {
        background: #112235;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        border: 1px solid #1E3A5F;
    }
    .stat-label {
        color: #8BA4BE;
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    .stat-value {
        color: #FFFFFF;
        font-size: 16px;
        font-weight: bold;
        margin: 2px 0 0 0;
    }
    .stat-desc {
        color: #4A6580;
        font-size: 10px;
        margin: 2px 0 0 0;
        line-height: 1.4;
    }
    .coin-card {
        background: #112235;
        border-radius: 8px;
        padding: 20px;
        border: 1px solid #1E3A5F;
        height: 100%;
    }
    .source-footer {
        text-align: center;
        padding: 12px 0;
        color: #4A6580;
        font-size: 11px;
    }
    .source-badge {
        background: #0D2137;
        border: 1px solid #1E3A5F;
        border-radius: 20px;
        padding: 4px 12px;
        color: #8BA4BE;
        font-size: 11px;
        display: inline-block;
        margin: 3px;
    }
    .stRadio label { color: #8BA4BE !important; }
    h1, h2, h3 { color: #FFFFFF !important; }
    hr { border-color: #1E3A5F; }
    .stButton button {
        background: #112235;
        color: #00C4CC;
        border: 1px solid #00C4CC;
        border-radius: 6px;
        font-weight: bold;
    }
    .stButton button:hover {
        background: #00C4CC;
        color: #0A1628;
    }
</style>
""", unsafe_allow_html=True)

# ─── DATABASE ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    return create_engine(
        "mysql+mysqlconnector://root:Danish12@localhost/crypto_sentiment"
    )

def run_query(query, params=None):
    engine = get_engine()
    with engine.connect() as conn:
        if params:
            named_query = query
            named_params = {}
            for i, val in enumerate(params):
                key = f"param{i}"
                named_query = named_query.replace("%s", f":{key}", 1)
                named_params[key] = val
            return pd.read_sql(text(named_query), conn, params=named_params)
        return pd.read_sql(text(query), conn)

# ─── CONSTANTS ────────────────────────────────────────────────────────────
COIN_COLORS = {
    "bitcoin":  "#F7931A",
    "ethereum": "#627EEA",
    "solana":   "#9945FF"
}
COIN_LABELS = {
    "bitcoin":  "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana":   "Solana (SOL)"
}

# ─── HELPERS ──────────────────────────────────────────────────────────────
def mood_label(score):
    if score >= 75:   return "Very Confident", "#00FF88"
    elif score >= 55: return "Confident",      "#80FF44"
    elif score >= 45: return "Balanced",       "#FFD700"
    elif score >= 25: return "Nervous",        "#FF8800"
    else:             return "Very Nervous",   "#FF4466"

def hex_to_rgba(hex_color, alpha=0.1):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def get_price_trend(price_df, days=14):
    if len(price_df) < days:
        return 0.0
    recent = price_df["price_usd"].tail(days).values
    return ((recent[-1] - recent[0]) / recent[0]) * 100

def get_traffic_light(mood_score, price_trend_pct):
    mood_is_high   = mood_score >= 55
    mood_is_low    = mood_score < 45
    price_going_up = price_trend_pct > 2
    price_going_dn = price_trend_pct < -2

    if mood_is_high and price_going_up:
        return {
            "verdict":     "🟢  HEALTHY MARKET",
            "color":       "#00FF88",
            "bg":          "#0A2A1A",
            "border":      "#00FF88",
            "short":       "Both public confidence and prices are rising together.",
            "explanation": (
                "Public confidence is HIGH and prices are trending UP. "
                "This is the healthiest market condition — people feel good "
                "and the market reflects that positively. "
                "Like a ripe, fresh banana — good condition, right time to observe."
            ),
            "action": "Market conditions are aligned. Confidence and price move together."
        }
    elif mood_is_high and price_going_dn:
        return {
            "verdict":     "🟠  RECOVERY WATCH",
            "color":       "#FF8800",
            "bg":          "#2A1A00",
            "border":      "#FF8800",
            "short":       "People are confident but prices are still falling.",
            "explanation": (
                "Public confidence is HIGH but prices are trending DOWN. "
                "This is an interesting divergence — people believe in the market "
                "but prices have not caught up yet. "
                "Like a banana that looks good on the outside but needs more time."
            ),
            "action": "Watch for price recovery — confidence may pull prices back up."
        }
    elif mood_is_low and price_going_up:
        return {
            "verdict":     "🟡  WARNING SIGNAL",
            "color":       "#FFD700",
            "bg":          "#2A2200",
            "border":      "#FFD700",
            "short":       "Prices are rising but people feel nervous — a danger sign.",
            "explanation": (
                "Public confidence is LOW but prices are still going UP. "
                "This is the most dangerous condition — prices are high "
                "but people do not trust them. Historically this precedes a correction. "
                "Like a banana that looks yellow but is starting to show brown spots — "
                "it may look fine but the warning signs are there."
            ),
            "action": "High risk condition. Price and mood are disconnected — correction possible."
        }
    elif mood_is_low and price_going_dn:
        return {
            "verdict":     "🔴  DANGER ZONE",
            "color":       "#FF4466",
            "bg":          "#2A0A10",
            "border":      "#FF4466",
            "short":       "Both confidence and prices are falling — full negative signal.",
            "explanation": (
                "Public confidence is LOW and prices are trending DOWN. "
                "Both indicators point in the same negative direction. "
                "This is a full danger signal — the market is under stress. "
                "Like a brown, overripe banana — clearly in bad condition."
            ),
            "action": "Both mood and price are negative. Market is under significant stress."
        }
    else:
        return {
            "verdict":     "⚪  NEUTRAL / MIXED",
            "color":       "#8BA4BE",
            "bg":          "#0D1B2E",
            "border":      "#8BA4BE",
            "short":       "Market signals are mixed — no clear direction yet.",
            "explanation": (
                "Public confidence and price trends are neither clearly positive "
                "nor clearly negative. The market is in a transitional state. "
                "Like a banana that is half-green, half-yellow — "
                "not yet ripe, not yet bad, just in between."
            ),
            "action": "Monitor closely — the next few days will show a clearer direction."
        }

def run_regression(price_df, sentiment_df):
    merged = pd.merge(
        price_df.groupby("date")["price_change_24h"].mean().reset_index(),
        sentiment_df.groupby("date")["score"].mean().reset_index(),
        on="date"
    ).dropna()
    if len(merged) < 10:
        return 0.0, 0.0, 0.0, merged
    X = merged["score"].values.astype(float).reshape(-1, 1)
    y = merged["price_change_24h"].values.astype(float)
    if np.std(X) == 0 or np.std(y) == 0:
        return 0.0, 0.0, 0.0, merged
    model = LinearRegression().fit(X, y)
    r     = float(np.corrcoef(X.flatten(), y)[0][1])
    r2    = r ** 2
    slope = float(model.coef_[0])
    return r, r2, slope, merged

# ─── HEADER ───────────────────────────────────────────────────────────────
st.markdown("""
<div class='top-header'>
    <div>
        <div style='color:#0A1628; font-size:22px; font-weight:bold;'>
            📊 Crypto Market Health Tracker
        </div>
        <div style='color:#0A1628; font-size:13px; margin-top:4px;'>
            Is the market healthy or in danger? — Powered by MySQL & Linear Regression
        </div>
    </div>
    <div style='color:#0A1628; font-size:12px; text-align:right;'>
        JBNU 2026<br>Database Design Term Project
    </div>
</div>
""", unsafe_allow_html=True)

# ─── CONTROLS ─────────────────────────────────────────────────────────────
col_coin, col_days, col_btn = st.columns([3, 3, 2])
with col_coin:
    coin = st.radio("Select Coin:",
                    ["bitcoin", "ethereum", "solana"],
                    format_func=lambda x: COIN_LABELS[x],
                    horizontal=True)
with col_days:
    days = st.radio("Analysis Window:",
                    [90, 180, 270, 365],
                    format_func=lambda x: f"{x} Days",
                    horizontal=True, index=3)
with col_btn:
    st.write("")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("⬇ Fetch New Data"):
            with st.spinner("Fetching from APIs..."):
                subprocess.run([sys.executable, "fetcher.py"])
            st.cache_resource.clear()
            st.rerun()
    with b2:
        if st.button("⚙ Run Regression"):
            with st.spinner("Running regression..."):
                subprocess.run([sys.executable, "regression.py"])
            st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ─── LOAD DATA ────────────────────────────────────────────────────────────
cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

try:
    price_df = run_query("""
        SELECT DATE(recorded_at) as date,
               AVG(price_usd) as price_usd,
               AVG(price_change_24h) as price_change_24h,
               AVG(volume_24h) as volume_24h
        FROM price_data
        WHERE coin_id = %s AND DATE(recorded_at) >= %s
        GROUP BY DATE(recorded_at)
        ORDER BY date
    """, params=(coin, cutoff))

    sentiment_df = run_query("""
        SELECT DATE(recorded_at) as date, AVG(score) as score
        FROM sentiment_data
        WHERE DATE(recorded_at) >= %s
        GROUP BY DATE(recorded_at)
        ORDER BY date
    """, params=(cutoff,))

    latest_price = run_query("""
        SELECT price_usd, price_change_24h FROM price_data
        WHERE coin_id = %s ORDER BY recorded_at DESC LIMIT 1
    """, params=(coin,))

    latest_mood = run_query("""
        SELECT score, sentiment_label FROM sentiment_data
        ORDER BY recorded_at DESC LIMIT 1
    """)

    if price_df.empty or sentiment_df.empty:
        st.warning("No data found. Please click 'Fetch New Data' first.")
        st.stop()

    # ── Core calculations ──────────────────────────────────────────────
    price_val    = float(latest_price["price_usd"].iloc[0]) if not latest_price.empty else 0
    change_val   = float(latest_price["price_change_24h"].iloc[0] or 0) if not latest_price.empty else 0
    mood_score   = int(latest_mood["score"].iloc[0]) if not latest_mood.empty else 50
    mood_lbl, mood_clr = mood_label(mood_score)
    price_trend  = get_price_trend(price_df, days=14)
    traffic      = get_traffic_light(mood_score, price_trend)
    avg_mood     = float(sentiment_df["score"].mean())
    period_change= ((float(price_df["price_usd"].iloc[-1]) /
                     float(price_df["price_usd"].iloc[0])) - 1) * 100
    peak_price   = float(price_df["price_usd"].max())
    low_price    = float(price_df["price_usd"].min())
    swing        = ((peak_price - low_price) / low_price) * 100
    nervous_days = len(sentiment_df[sentiment_df["score"] < 50])
    conf_days    = len(sentiment_df[sentiment_df["score"] >= 50])
    color        = COIN_COLORS[coin]

    r, r2, slope, merged_df = run_regression(price_df, sentiment_df)

    # ════════════════════════════════════════════════════════════════════
    # TRAFFIC LIGHT VERDICT
    # ════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class='traffic-light-box'
         style='background:{traffic["bg"]}; border-left-color:{traffic["border"]};'>
        <div class='tl-label' style='color:{traffic["color"]};'>
            🚦 MARKET HEALTH VERDICT — {COIN_LABELS[coin].upper()} — LAST {days} DAYS
        </div>
        <div class='tl-verdict' style='color:{traffic["color"]};'>
            {traffic["verdict"]}
        </div>
        <div class='tl-explanation' style='color:#FFFFFF;'>
            {traffic["explanation"]}
        </div>
        <div class='tl-stats' style='color:{traffic["color"]};'>
            Today's Mood: {mood_score}/100 ({mood_lbl}) &nbsp;|&nbsp;
            14-Day Price Trend: {"+" if price_trend >= 0 else ""}{price_trend:.1f}% &nbsp;|&nbsp;
            {traffic["action"]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── HOW TO READ THIS ──────────────────────────────────────────────
    with st.expander("📖 How to read this verdict? (Click to expand)"):
        c1, c2, c3, c4 = st.columns(4)
        verdicts = [
            ("🟢 HEALTHY",         "#00FF88", "Mood HIGH + Price UP",
             "Both indicators positive. Market is in good condition."),
            ("🟡 WARNING",         "#FFD700", "Mood LOW + Price UP",
             "Prices rising but people nervous. Risk of correction."),
            ("🟠 RECOVERY WATCH",  "#FF8800", "Mood HIGH + Price DOWN",
             "Confident people, falling price. Watch for bounce."),
            ("🔴 DANGER ZONE",     "#FF4466", "Mood LOW + Price DOWN",
             "Both negative. Market under stress."),
        ]
        for col, (v, c, cond, desc) in zip([c1, c2, c3, c4], verdicts):
            with col:
                st.markdown(f"""
                <div style='background:#112235; border-radius:8px; padding:14px;
                            border-left:4px solid {c};'>
                    <div style='color:{c}; font-weight:bold; font-size:13px;'>
                        {v}
                    </div>
                    <div style='color:#8BA4BE; font-size:11px;
                                margin:4px 0; font-weight:bold;'>
                        {cond}
                    </div>
                    <div style='color:#FFFFFF; font-size:11px; line-height:1.5;'>
                        {desc}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── SNAPSHOT METRICS ──────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    change_clr  = "#00FF88" if change_val >= 0 else "#FF4466"
    change_sign = "+" if change_val >= 0 else ""
    pc_clr      = "#00FF88" if period_change >= 0 else "#FF4466"
    pc_sign     = "+" if period_change >= 0 else ""
    tr_clr      = "#00FF88" if price_trend >= 0 else "#FF4466"
    tr_sign     = "+" if price_trend >= 0 else ""
    am_lbl, am_clr = mood_label(avg_mood)

    for col, (label, val, vc, sub, sc) in zip(
        [m1, m2, m3, m4, m5],
        [
            ("LATEST PRICE",       f"${price_val:,.2f}", color,
             f"{change_sign}{change_val:.2f}% today", change_clr),
            ("TODAY'S MOOD",       f"{mood_score}/100", mood_clr,
             mood_lbl, mood_clr),
            (f"{days}-DAY CHANGE", f"{pc_sign}{period_change:.1f}%", pc_clr,
             "over full period", "#8BA4BE"),
            ("14-DAY TREND",       f"{tr_sign}{price_trend:.1f}%", tr_clr,
             "recent direction", "#8BA4BE"),
            ("AVG MOOD",           f"{avg_mood:.0f}/100", am_clr,
             am_lbl, am_clr),
        ]
    ):
        with col:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value' style='color:{vc};'>{val}</div>
                <div class='metric-sub' style='color:{sc};'>{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # CHAPTER 1 — PRICE HISTORY
    # ════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class='chapter-box'>
        <div class='chapter-num'>CHAPTER 1 OF 3</div>
        <div class='chapter-title'>What happened to prices?</div>
        <div class='chapter-desc'>
            The full price history of {COIN_LABELS[coin]} from our MySQL database.
            Peak and lowest points are marked. The highlighted section
            shows the most recent 14 days used for the traffic light verdict.
        </div>
    </div>
    """, unsafe_allow_html=True)

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=price_df["date"], y=price_df["price_usd"],
        mode="lines", line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=hex_to_rgba(color, 0.06),
        name=COIN_LABELS[coin],
        hovertemplate="<b>%{x}</b><br>Price: $%{y:,.2f}<extra></extra>"
    ))
    if len(price_df) >= 14:
        fig1.add_trace(go.Scatter(
            x=price_df["date"].tail(14).tolist(),
            y=price_df["price_usd"].tail(14).tolist(),
            mode="lines",
            line=dict(color=traffic["color"], width=2.5),
            fill="tozeroy",
            fillcolor=hex_to_rgba(traffic["border"], 0.15),
            name="Recent 14 Days (verdict basis)",
            hovertemplate="<b>%{x}</b><br>Price: $%{y:,.2f}<extra></extra>"
        ))
    max_idx = price_df["price_usd"].idxmax()
    min_idx = price_df["price_usd"].idxmin()
    fig1.add_annotation(
        x=price_df["date"].iloc[max_idx],
        y=float(price_df["price_usd"].iloc[max_idx]),
        text=f"Peak: ${float(price_df['price_usd'].iloc[max_idx]):,.0f}",
        showarrow=True, arrowhead=2,
        arrowcolor="#00FF88", font=dict(color="#00FF88", size=11),
        bgcolor="#0A1628", bordercolor="#00FF88", borderwidth=1
    )
    fig1.add_annotation(
        x=price_df["date"].iloc[min_idx],
        y=float(price_df["price_usd"].iloc[min_idx]),
        text=f"Low: ${float(price_df['price_usd'].iloc[min_idx]):,.0f}",
        showarrow=True, arrowhead=2,
        arrowcolor="#FF4466", font=dict(color="#FF4466", size=11),
        bgcolor="#0A1628", bordercolor="#FF4466", borderwidth=1
    )
    fig1.update_layout(
        paper_bgcolor="#0A1628", plot_bgcolor="#112235",
        font=dict(color="#8BA4BE"), height=320,
        margin=dict(l=70, r=20, t=20, b=40),
        xaxis=dict(gridcolor="#1E3A5F"),
        yaxis=dict(gridcolor="#1E3A5F",
                   tickprefix="$", tickformat=",.0f"),
        legend=dict(bgcolor="#112235", bordercolor="#1E3A5F",
                    font=dict(color="#8BA4BE")),
        hovermode="x unified"
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown(f"""
    <div class='insight-box'>
        <span style='color:#00C4CC; font-weight:bold;'>📊 Price Story: </span>
        <span style='color:#FFFFFF;'>
        Over {days} days, {COIN_LABELS[coin]} moved between a low of
        <b style='color:#FF4466;'>${low_price:,.0f}</b> and a peak of
        <b style='color:#00FF88;'>${peak_price:,.0f}</b>
        — a total swing of <b style='color:#FFD700;'>{swing:.1f}%</b>.
        Overall period change:
        <b style='color:{"#00FF88" if period_change>=0 else "#FF4466"};'>
        {pc_sign}{period_change:.1f}%</b>.
        The highlighted section shows the 14 days driving the current verdict.
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # CHAPTER 2 — PUBLIC MOOD
    # ════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class='chapter-box'>
        <div class='chapter-num'>CHAPTER 2 OF 3</div>
        <div class='chapter-title'>What was the public mood?</div>
        <div class='chapter-desc'>
            Daily public mood score (0–100) stored in our MySQL database.
            Green = confident. Red = nervous. Dotted line at 50 = neutral.
            The price chart below uses the same time axis so you can compare 
            whether mood and price move together.
        </div>
    </div>
    """, unsafe_allow_html=True)

    fig2 = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.45], vertical_spacing=0.06,
        subplot_titles=[
            "Public Mood Score (0=Very Nervous → 100=Very Confident)",
            f"{COIN_LABELS[coin]} Price (same period)"
        ]
    )
    s_scores = sentiment_df["score"].tolist()
    s_dates  = sentiment_df["date"].tolist()
    fig2.add_trace(go.Scatter(
        x=s_dates, y=s_scores, mode="lines",
        line=dict(color="#FFD700", width=2), name="Mood Score",
        hovertemplate="<b>%{x}</b><br>Mood: %{y:.0f}/100<extra></extra>"
    ), row=1, col=1)
    fig2.add_trace(go.Scatter(
        x=s_dates + s_dates[::-1],
        y=[max(s, 50) for s in s_scores] + [50]*len(s_scores),
        fill="toself", fillcolor="rgba(0,255,136,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Confident Zone", hoverinfo="skip"
    ), row=1, col=1)
    fig2.add_trace(go.Scatter(
        x=s_dates + s_dates[::-1],
        y=[min(s, 50) for s in s_scores] + [50]*len(s_scores),
        fill="toself", fillcolor="rgba(255,68,102,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Nervous Zone", hoverinfo="skip"
    ), row=1, col=1)
    fig2.add_hline(y=50, line_dash="dot", line_color="#4A6580",
                   annotation_text="Neutral (50)",
                   annotation_font_color="#4A6580", row=1, col=1)
    fig2.add_trace(go.Scatter(
        x=price_df["date"], y=price_df["price_usd"],
        mode="lines", line=dict(color=color, width=1.5),
        name=f"{COIN_LABELS[coin]} Price",
        hovertemplate="<b>%{x}</b><br>Price: $%{y:,.2f}<extra></extra>"
    ), row=2, col=1)
    fig2.update_layout(
        paper_bgcolor="#0A1628", plot_bgcolor="#112235",
        font=dict(color="#8BA4BE"), height=440,
        margin=dict(l=70, r=20, t=40, b=40),
        hovermode="x unified",
        legend=dict(bgcolor="#112235", bordercolor="#1E3A5F",
                    font=dict(color="#8BA4BE"))
    )
    fig2.update_yaxes(
        gridcolor="#1E3A5F", range=[0, 100],
        tickvals=[0, 25, 50, 75, 100],
        ticktext=["0 Very Nervous", "25 Nervous",
                  "50 Balanced", "75 Confident", "100 Very Confident"],
        row=1, col=1
    )
    fig2.update_yaxes(
        gridcolor="#1E3A5F",
        tickprefix="$", tickformat=",.0f",
        row=2, col=1
    )
    fig2.update_xaxes(gridcolor="#1E3A5F")
    st.plotly_chart(fig2, use_container_width=True)

    dom      = "nervous" if nervous_days > conf_days else "confident"
    dom_clr  = "#FF4466" if dom == "nervous" else "#00FF88"
    st.markdown(f"""
    <div class='insight-box'>
        <span style='color:#00C4CC; font-weight:bold;'>🧠 Mood Story: </span>
        <span style='color:#FFFFFF;'>
        Over {days} days, the public felt
        <b style='color:#FF4466;'>nervous for {nervous_days} days</b> and
        <b style='color:#00FF88;'>confident for {conf_days} days</b>.
        Dominant mood: <b style='color:{dom_clr};'>{dom}</b>
        (average {avg_mood:.0f}/100).
        Compare both charts — do the green and red mood areas 
        match the price rises and falls?
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # CHAPTER 3 — REGRESSION
    # ════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class='chapter-box'>
        <div class='chapter-num'>CHAPTER 3 OF 3</div>
        <div class='chapter-title'>
            What does the Linear Regression algorithm show?
        </div>
        <div class='chapter-desc'>
            Each dot = one day from our MySQL database.
            The dashed line is calculated by Linear Regression (scikit-learn).
            If the line slopes upward → higher confidence tends to mean 
            higher price changes.
            If the line is flat → mood alone does not predict price.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_chart, col_stats = st.columns([3, 2])
    with col_chart:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=merged_df["score"],
            y=merged_df["price_change_24h"],
            mode="markers",
            marker=dict(color=color, size=7, opacity=0.6),
            name="One day of data",
            hovertemplate=(
                "<b>Mood: %{x:.0f}/100</b><br>"
                "Price Change: %{y:.2f}%<extra></extra>"
            )
        ))
        if len(merged_df) > 2:
            x_vals = merged_df["score"].values.astype(float)
            y_vals = merged_df["price_change_24h"].values.astype(float)
            x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
            mdl    = LinearRegression().fit(x_vals.reshape(-1, 1), y_vals)
            y_line = mdl.predict(x_line.reshape(-1, 1))
            fig3.add_trace(go.Scatter(
                x=x_line, y=y_line, mode="lines",
                line=dict(color="#00C4CC", width=2.5, dash="dash"),
                name="Regression Line", hoverinfo="skip"
            ))
        fig3.add_hline(y=0, line_dash="dot", line_color="#4A6580",
                       annotation_text="No change",
                       annotation_font_color="#4A6580")
        fig3.add_vline(x=50, line_dash="dot", line_color="#4A6580",
                       annotation_text="Neutral mood",
                       annotation_font_color="#4A6580")
        fig3.update_layout(
            paper_bgcolor="#0A1628", plot_bgcolor="#112235",
            font=dict(color="#8BA4BE"), height=380,
            margin=dict(l=70, r=20, t=20, b=60),
            xaxis=dict(
                title=dict(
                    text="Public Mood Score (0=Very Nervous → 100=Very Confident)",
                    font=dict(color="#8BA4BE")
                ),
                gridcolor="#1E3A5F"
            ),
            yaxis=dict(
                title=dict(
                    text="Price Change That Day (%)",
                    font=dict(color="#8BA4BE")
                ),
                gridcolor="#1E3A5F", ticksuffix="%"
            ),
            legend=dict(bgcolor="#112235", bordercolor="#1E3A5F",
                        font=dict(color="#8BA4BE")),
            hovermode="closest"
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col_stats:
        r_clr = ("#00FF88" if abs(r) > 0.5
                 else "#FF8800" if abs(r) > 0.3
                 else "#FF4466")
        for label, val, vc, desc in [
            ("Correlation (r)", f"{r:.4f}", r_clr,
             "How strongly mood and price are linked.\n"
             "Close to 1.0 = strong. Close to 0 = no link."),
            ("R² Score", f"{r2:.4f}", "#FFFFFF",
             f"Mood explains {r2*100:.1f}% of daily price change.\n"
             f"Other factors explain the remaining {100-r2*100:.1f}%."),
            ("Slope (β)", f"{slope:.4f}", "#FFFFFF",
             f"Every +1 mood point → price changes by {slope:.4f}% on average."),
            ("Data Points", f"{len(merged_df)} days", "#FFFFFF",
             "Days with both price AND mood data in MySQL."),
        ]:
            st.markdown(f"""
            <div class='stat-row'>
                <div class='stat-label'>{label}</div>
                <div class='stat-value' style='color:{vc};'>{val}</div>
                <div class='stat-desc'>{desc}</div>
            </div>
            """, unsafe_allow_html=True)

        if abs(r) > 0.5:
            reg_msg = "Strong link found. Mood is a meaningful predictor."
            reg_clr = "#00FF88"
        elif abs(r) > 0.3:
            reg_msg = "Moderate link. Mood has some effect on price."
            reg_clr = "#FFD700"
        else:
            reg_msg = ("Weak statistical link detected.\n"
                       "Price is driven by other forces beyond public mood.\n"
                       "This is itself a valid and honest finding.")
            reg_clr = "#FF8800"

        st.markdown(f"""
        <div style='background:#0D2137; border-radius:8px; padding:14px;
                    border:1px solid {reg_clr}; margin-top:8px;'>
            <div style='color:{reg_clr}; font-weight:bold; font-size:13px;'>
                🤖 Regression Finding
            </div>
            <div style='color:#FFFFFF; font-size:12px;
                        margin-top:6px; line-height:1.6;'>
                {reg_msg}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # ALL COINS COMPARISON
    # ════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class='chapter-box'>
        <div class='chapter-num'>BONUS</div>
        <div class='chapter-title'>How do all three coins compare?</div>
        <div class='chapter-desc'>
            Side-by-side market health verdict for Bitcoin, Ethereum, 
            and Solana over the same time window.
        </div>
    </div>
    """, unsafe_allow_html=True)

    comp_cols = st.columns(3)
    for i, c in enumerate(["bitcoin", "ethereum", "solana"]):
        c_price = run_query("""
            SELECT DATE(recorded_at) as date,
                   AVG(price_usd) as price_usd,
                   AVG(price_change_24h) as price_change_24h
            FROM price_data
            WHERE coin_id = %s AND DATE(recorded_at) >= %s
            GROUP BY DATE(recorded_at) ORDER BY date
        """, params=(c, cutoff))
        c_latest = run_query("""
            SELECT price_usd, price_change_24h FROM price_data
            WHERE coin_id = %s ORDER BY recorded_at DESC LIMIT 1
        """, params=(c,))
        c_mood_q = run_query("""
            SELECT score FROM sentiment_data
            ORDER BY recorded_at DESC LIMIT 1
        """)
        c_sent = run_query("""
            SELECT AVG(score) as avg_score FROM sentiment_data
            WHERE DATE(recorded_at) >= %s
        """, params=(cutoff,))

        if c_price.empty:
            continue

        c_price_val  = float(c_latest["price_usd"].iloc[0]) if not c_latest.empty else 0
        c_change     = float(c_latest["price_change_24h"].iloc[0] or 0) if not c_latest.empty else 0
        c_mood_score = int(c_mood_q["score"].iloc[0]) if not c_mood_q.empty else 50
        c_trend      = get_price_trend(c_price, days=14)
        c_traffic    = get_traffic_light(c_mood_score, c_trend)
        c_avg_mood   = float(c_sent["avg_score"].iloc[0]) if not c_sent.empty else 50
        c_pc         = ((float(c_price["price_usd"].iloc[-1]) /
                         float(c_price["price_usd"].iloc[0])) - 1) * 100
        c_chg_clr    = "#00FF88" if c_change >= 0 else "#FF4466"
        c_chg_sign   = "+" if c_change >= 0 else ""
        c_pc_clr     = "#00FF88" if c_pc >= 0 else "#FF4466"
        c_pc_sign    = "+" if c_pc >= 0 else ""
        c_ml, c_mc   = mood_label(c_mood_score)
        c_aml, c_amc = mood_label(c_avg_mood)

        with comp_cols[i]:
            st.markdown(f"""
            <div class='coin-card'>
                <div style='color:{COIN_COLORS[c]}; font-size:16px;
                            font-weight:bold; margin-bottom:12px;'>
                    {COIN_LABELS[c]}
                </div>
                <div style='background:{c_traffic["bg"]}; border-radius:6px;
                            padding:10px 12px;
                            border-left:4px solid {c_traffic["border"]};
                            margin-bottom:12px;'>
                    <div style='color:{c_traffic["color"]}; font-weight:bold;
                                font-size:13px;'>
                        {c_traffic["verdict"]}
                    </div>
                    <div style='color:#8BA4BE; font-size:11px; margin-top:4px;'>
                        {c_traffic["short"]}
                    </div>
                </div>
                <div style='color:#8BA4BE; font-size:10px;
                            letter-spacing:1px;'>LATEST PRICE</div>
                <div style='color:{COIN_COLORS[c]}; font-size:18px;
                            font-weight:bold; margin-bottom:8px;'>
                    ${c_price_val:,.2f}
                    <span style='color:{c_chg_clr}; font-size:12px;'>
                        ({c_chg_sign}{c_change:.2f}% today)
                    </span>
                </div>
                <div style='color:#8BA4BE; font-size:10px;
                            letter-spacing:1px;'>{days}-DAY CHANGE</div>
                <div style='color:{c_pc_clr}; font-size:15px;
                            font-weight:bold; margin-bottom:8px;'>
                    {c_pc_sign}{c_pc:.1f}%
                </div>
                <div style='color:#8BA4BE; font-size:10px;
                            letter-spacing:1px;'>TODAY'S MOOD</div>
                <div style='color:{c_mc}; font-size:14px;
                            font-weight:bold; margin-bottom:4px;'>
                    {c_mood_score}/100 — {c_ml}
                </div>
                <div style='color:#8BA4BE; font-size:10px;
                            letter-spacing:1px;'>AVG MOOD THIS PERIOD</div>
                <div style='color:{c_amc}; font-size:13px; font-weight:bold;'>
                    {c_avg_mood:.0f}/100 — {c_aml}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='source-footer'>
        <div style='letter-spacing:2px; margin-bottom:8px;'>DATA SOURCES</div>
        <span class='source-badge'>
            📈 Price Data: CoinGecko API — coingecko.com/en/api
        </span>
        <span class='source-badge'>
            🧠 Mood Score: Alternative.me — alternative.me/crypto/fear-and-greed-index
        </span>
        <span class='source-badge'>
            🗄️ Database: MySQL (crypto_sentiment) — 3 Tables
        </span>
        <span class='source-badge'>
            🤖 AI: Linear Regression — scikit-learn
        </span>
        <div style='margin-top:10px;'>
            JBNU 2026 · Database Design Term Project ·
            {len(price_df)} price records · {len(sentiment_df)} mood records loaded
        </div>
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please click 'Fetch New Data' to populate the database first.")