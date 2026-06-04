"""
Reddit Beauty Market Intelligence Dashboard v7.0
Changelog:
  v2.0  - Google Drive DB auto-download
  v3.0  - Tab reorder + Consumer VOC Analysis tab
  v4.0  - Permalink links / Region group filter / Overview tab
  v4.1  - Bugfix: set_page_config ordering / defensive SQL columns
  v5.0  - Full English UI + Regional Ingredient Comparison section
  v5.1  - VOC/Technique post links / Regional tab new sections / LinkColumn
  v6.0  - Tab restructure: background sections → Overview / Data Source Context expander
  v6.1  - Sidebar card-style region group radio / Link bug fix
  v6.2  - Bug fixes: URS scatter / IndexError / r-prefix / data mutation / LinkColumn
  v6.3  - make_reddit_url() format branch: full URL vs relative path permalink handling
  v7.0  - Full modular refactor · 5 tabs · all English UI · new fields activated
          New: Flair analysis · created_utc trend · Positive Signal Tracker
          New: Hybrid Dynamic Segment Matrix (T8) · Subreddit Correlation Heatmap
          Modules: config.py · data_loader.py · tab_overview.py ·
                   tab_analysis.py · tab_marketing.py
"""

# ★ st.set_page_config MUST be the very first Streamlit call ★
import streamlit as st

st.set_page_config(
    page_title="Reddit Beauty Insights",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Module imports (after set_page_config) ──────────────────────
from datetime import datetime

from config import CSS, DB_PATH
from data_loader import ensure_db, load_all_data, build_sidebar, render_kpi_cards
from tab_overview import render_tab_overview
from tab_analysis import render_tab_trend, render_tab_ingredient, render_tab_voc
from tab_marketing import render_tab_marketing

# ─── Apply CSS ───────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

# ─── Load Data ───────────────────────────────────────────────────
ensure_db()
posts_df, keywords_df, meta_df = load_all_data()

# ─── Sidebar + Filter ────────────────────────────────────────────
filtered = build_sidebar(posts_df)

# ─── Header ──────────────────────────────────────────────────────
st.markdown("# 🌿 Reddit Beauty Market Intelligence Dashboard")
st.markdown(
    f"> Global beauty community · "
    f"**{posts_df['subreddit'].nunique()} subreddits** · "
    f"**{len(posts_df):,} posts** collected"
)
st.markdown("---")

# ─── KPI Cards ───────────────────────────────────────────────────
render_kpi_cards(filtered, keywords_df)

# ─── Tabs ────────────────────────────────────────────────────────
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "📌 Overview & Data Hub",
    "📊 Trend Detection",
    "🧬 Ingredients & Positioning",
    "💬 Consumer Intelligence",
    "🎯 Marketing Actions",
])

with tab0:
    render_tab_overview(filtered, posts_df, keywords_df, meta_df)

with tab1:
    render_tab_trend(filtered, posts_df)

with tab2:
    render_tab_ingredient(filtered, posts_df, keywords_df)

with tab3:
    render_tab_voc(filtered, posts_df, keywords_df)

with tab4:
    render_tab_marketing(filtered, posts_df, keywords_df)

# ─── Footer ──────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"🌿 Reddit Beauty Market Intelligence Dashboard v7.0 | "
    f"DB: {DB_PATH} | "
    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)
