"""
Reddit Beauty Market Intelligence Dashboard v6.0
Changelog:
  v2.0 - Google Drive DB auto-download
  v3.0 - Tab reorder + Consumer VOC Analysis tab
  v4.0 - Permalink links / Region group filter / Overview tab
  v4.1 - Bugfix: set_page_config ordering / defensive SQL columns
  v5.0 - Full English UI + Regional Ingredient Comparison section
  v5.1 - VOC/Technique post links / Regional tab new sections / LinkColumn
  v6.0 - Tab restructure: background sections → Overview / Data Source Context expander on all analysis tabs
"""

import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime
import os
import gdown
import numpy as np

# ─────────────────────────────────────────
# 0. Page config ★ Must be the first Streamlit command ★
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Reddit Beauty Insights",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# Google Drive DB auto-download
# ─────────────────────────────────────────
DB_PATH        = "reddit_data.db"
GDRIVE_FILE_ID = "1-nuBg81wfomyeCoqvF6JMURzSCBWM9Fz"   # ← Replace with your file ID

@st.cache_resource(show_spinner="📥 Loading database...")
def ensure_db():
    if not os.path.exists(DB_PATH):
        try:
            url = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}&export=download"
            gdown.download(url, DB_PATH, quiet=False)
        except Exception:
            try:
                url2 = f"https://drive.google.com/file/d/{GDRIVE_FILE_ID}/view"
                gdown.download(url2, DB_PATH, quiet=False, fuzzy=True)
            except Exception as e2:
                st.error(f"""
                ❌ DB download failed.

                **Check:**
                1. Google Drive sharing → 'Anyone with the link' (Viewer)
                2. File ID is correct: `{GDRIVE_FILE_ID}`
                3. Error detail: {e2}
                """)
                st.stop()
    return DB_PATH

ensure_db()

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=DM+Serif+Display&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }

.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460; border-radius: 12px;
    padding: 20px 24px; text-align: center; color: white;
}
.metric-card .val { font-size: 2.4rem; font-weight: 700; color: #e94560; line-height: 1; }
.metric-card .lbl { font-size: 0.85rem; color: #a0aec0; margin-top: 6px; }

.section-header {
    background: linear-gradient(90deg, #0f3460, #533483);
    color: white; padding: 10px 20px; border-radius: 8px;
    margin: 24px 0 16px 0; font-size: 1.05rem; font-weight: 600;
}

.post-card {
    background: #f8f9fa; border-left: 4px solid #e94560;
    border-radius: 0 8px 8px 0; padding: 12px 16px; margin: 8px 0;
}
.post-card .ptitle { font-weight: 600; font-size: 0.95rem; color: #1a1a2e; }
.post-card .pmeta  { font-size: 0.8rem; color: #718096; margin-top: 4px; }
.post-card .pscore { font-weight: 700; color: #e94560; }

.voc-header {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    color: white; padding: 14px 20px; border-radius: 10px; margin-bottom: 16px;
}
.voc-header h3 { margin: 0; font-size: 1rem; font-family: 'DM Serif Display', serif; }
.voc-header p  { margin: 4px 0 0 0; opacity: .8; font-size: .85rem; }

.urs-card {
    background: #fff8f0; border-left: 4px solid #e94560;
    border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 6px 0;
}
.urs-card .uc-title { font-weight: 600; font-size: 0.9rem; color: #1a1a2e; }
.urs-card .uc-meta  { font-size: 0.78rem; color: #718096; margin-top: 3px; }
.urs-card .uc-score { font-weight: 700; color: #e94560; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 1. DB load
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("PRAGMA table_info(reddit_posts)")
        existing = {row[1] for row in cur.fetchall()}

        base = """id, reddit_id, subreddit, title, selftext,
                  score, upvote_ratio, num_comments,
                  link_flair_text, author, author_flair_text,
                  total_awards_received, num_crossposts,
                  is_gallery, is_self,
                  created_utc, fetch_date, fetch_type,
                  region, priority_rank"""
        extra = ", ".join(
            f"COALESCE({c}, '') as {c}"
            for c in ["permalink", "url"] if c in existing
        )
        sql = f"SELECT {base}{', ' + extra if extra else ''} FROM reddit_posts"
        posts    = pd.read_sql_query(sql, conn)
        keywords = pd.read_sql_query("""
            SELECT kh.post_id, kh.keyword, kh.keyword_category,
                   kh.match_field, kh.matched_date, kh.matched_term,
                   rp.score, rp.num_comments, rp.upvote_ratio,
                   rp.subreddit, rp.region, rp.title,
                   rp.total_awards_received, rp.num_crossposts
            FROM keyword_hits kh
            JOIN reddit_posts rp ON kh.post_id = rp.id
        """, conn)
        meta = pd.read_sql_query("SELECT * FROM subreddits_meta", conn)
        conn.close()
        return posts, keywords, meta
    except Exception as e:
        st.error(f"❌ DB connection error: {e}")
        st.info(f"Make sure `{DB_PATH}` is in the same folder as dashboard.py.")
        st.stop()

posts_df, keywords_df, meta_df = load_data()

# 유저 프로필 페이지(r/u_ 형식) 제거 — 실제 서브레딧이 아님
posts_df = posts_df[~posts_df["subreddit"].str.contains(r"^r/u_", na=False, regex=True)].copy()

posts_df["fetch_date"] = pd.to_datetime(posts_df["fetch_date"], errors="coerce")
posts_df["created_dt"] = pd.to_datetime(posts_df["created_utc"], unit="s", errors="coerce")

# ─────────────────────────────────────────
# Region Group Mapping  (English display names, Korean + English matching)
# ─────────────────────────────────────────
REGION_GROUP_MAP = {
    "Global · General":          ["범용", "mass", "general", "다인종", "원료 데이터", "표준", "global_general"],
    "Global · Expert Consumer":  ["전문", "expert", "diy", "연구", "고관여", "가성비", "enthusiast"],
    "Global · Specific Target":  ["타깃", "target", "시니어", "senior", "고소득", "k-beauty", "미세연지"],
    "Global · Skin Concerns":    ["피부고민", "skin_concern", "acne", "호르몬", "지성", "트러블"],
    "Western Markets (NA/EU)":   ["north", "europe", "usa", "uk", "australia", "canada", "western",
                                   "서구", "북미", "유럽", "호주", "뉴질", "영국"],
    "Asia-Pacific":              ["asia", "pacific", "korea", "japan", "china", "india",
                                   "southeast", "singapore", "아시아", "태평양", "동남아", "인도", "싱가"],
}

def get_region_group(val):
    if pd.isna(val) or str(val).strip() == "":
        return "Uncategorized"
    v = str(val).lower()
    for grp, kws in REGION_GROUP_MAP.items():
        if any(k.lower() in v for k in kws):
            return grp
    return "Uncategorized"

posts_df["region_group"] = posts_df["region"].apply(get_region_group)

def make_reddit_url(row):
    pl = row.get("permalink", "")
    if pl and str(pl) not in ("", "nan", "None"):
        return f"https://www.reddit.com{pl}"
    rid, sub = row.get("reddit_id", ""), row.get("subreddit", "")
    return f"https://www.reddit.com/r/{sub}/comments/{rid}/" if rid and sub else ""

posts_df["reddit_url"] = posts_df.apply(make_reddit_url, axis=1)

# ─────────────────────────────────────────
# Ingredient keyword set (for direct scanning in Regional tab)
# ─────────────────────────────────────────
REGION_ING_DICT = {
    "Retinol":         ["retinol", "retinoid", "retin-a", "tretinoin"],
    "Niacinamide":     ["niacinamide", "nicotinamide"],
    "Hyaluronic Acid": ["hyaluronic acid", "sodium hyaluronate"],
    "Vitamin C":       ["vitamin c", "ascorbic acid"],
    "SPF/Sunscreen":   ["sunscreen", "spf", "sun protection"],
    "Ceramide":        ["ceramide"],
    "AHA/BHA":         ["glycolic acid", "salicylic acid", " aha ", " bha "],
    "Peptide":         ["peptide", "matrixyl"],
    "Centella":        ["centella", "cica"],
    "Squalane":        ["squalane"],
}

def calc_region_ingredients(df):
    records = []
    for ing, terms in REGION_ING_DICT.items():
        pat = "|".join(terms)
        mask = (df["title"].str.contains(pat, case=False, na=False) |
                df["selftext"].str.contains(pat, case=False, na=False))
        grp = df[mask].groupby("region_group").size().reset_index(name="mentions")
        grp["ingredient"] = ing
        records.append(grp)
    return pd.concat(records, ignore_index=True) if records else pd.DataFrame()

# ─────────────────────────────────────────
# 2. Sidebar
# ─────────────────────────────────────────
st.sidebar.markdown("## 🌿 Reddit Beauty Insights\n**Cosmetics Market Intelligence**")
st.sidebar.markdown("---")

st.sidebar.markdown("**📅 Collection Period**")
period_mode = st.sidebar.radio("", ["All (Cumulative)", "Select Period"],
                               horizontal=True, label_visibility="collapsed")
if period_mode == "Select Period":
    avail_years = sorted(
        posts_df["fetch_date"].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
    sel_year  = st.sidebar.selectbox("Year", avail_years)
    avail_mon = ["All"] + [f"{m:02d}" for m in sorted(
        posts_df[posts_df["fetch_date"].dt.year == sel_year]["fetch_date"]
        .dt.month.dropna().unique().astype(int).tolist())]
    sel_month = st.sidebar.selectbox("Month", avail_mon)
else:
    sel_year = sel_month = None

st.sidebar.markdown("---")
st.sidebar.markdown("**🌏 Region Group**")
rg_opts   = ["All"] + list(REGION_GROUP_MAP.keys()) + ["Uncategorized"]
sel_rgroup = st.sidebar.selectbox("Select region group", rg_opts, label_visibility="collapsed")

if sel_rgroup != "All":
    reg_in_grp = sorted(
        posts_df[posts_df["region_group"] == sel_rgroup]["region"].dropna().unique().tolist())
    reg_opts = ["All"] + reg_in_grp
else:
    reg_opts = ["All"] + sorted(posts_df["region"].dropna().unique().tolist())
sel_region = st.sidebar.selectbox("└ Sub-region", reg_opts)

st.sidebar.markdown("---")
sub_opts  = ["All"] + sorted(posts_df["subreddit"].dropna().unique().tolist())
sel_sub   = st.sidebar.selectbox("📌 Subreddit", sub_opts)
min_score = st.sidebar.slider("⭐ Min Score", 0, int(posts_df["score"].max() or 1000), 0, 10)

st.sidebar.markdown("---")
st.sidebar.caption(f"🗄️ DB: `{DB_PATH}`")
st.sidebar.caption(f"🕐 Last collected: {posts_df['fetch_date'].max().strftime('%Y-%m-%d') if not posts_df.empty else '-'}")
st.sidebar.caption(f"📦 {len(posts_df):,} posts · {posts_df['subreddit'].nunique()} subreddits")

# Apply filters
filtered = posts_df.copy()
if period_mode == "Select Period" and sel_year:
    filtered = filtered[filtered["fetch_date"].dt.year == sel_year]
    if sel_month != "All":
        filtered = filtered[filtered["fetch_date"].dt.month == int(sel_month)]
if sel_rgroup != "All":
    filtered = filtered[filtered["region_group"] == sel_rgroup]
if sel_region != "All":
    filtered = filtered[filtered["region"] == sel_region]
if sel_sub != "All":
    filtered = filtered[filtered["subreddit"] == sel_sub]
filtered = filtered[filtered["score"] >= min_score]

# ── Helper: simplified 4-region label (global — used by Tab3 & Overview) ──
def get_display_region(region_val):
    if pd.isna(region_val) or str(region_val).strip() == "":
        return "Global"
    v = str(region_val).lower()
    if any(k in v for k in ["korea","japan","china","asia","india","singapore","동남아","아시아","pacific"]):
        return "Asia"
    if any(k in v for k in ["europe","uk","germany","france","유럽","영국","네덜","스웨","이탈"]):
        return "Europe"
    if any(k in v for k in ["north","usa","canada","america","북미","호주","australia","newzeal","뉴질"]):
        return "N.America"
    return "Global"

filtered["region_display"] = filtered["region"].apply(get_display_region)

# ─────────────────────────────────────────
# 3. Header
# ─────────────────────────────────────────
st.markdown("# 🌿 Reddit Beauty Market Intelligence Dashboard")
st.markdown(
    f"> Global beauty community · **{len(posts_df['subreddit'].unique())} subreddits** · "
    f"**{len(posts_df):,} posts** collected"
)

# ─────────────────────────────────────────
# 4. KPI cards
# ─────────────────────────────────────────
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)
kpi_data = [
    (f"{len(filtered):,}",                                  "Total Posts"),
    (f"{int(filtered['score'].mean()) if not filtered.empty else 0:,}", "Avg Score"),
    (f"{int(filtered['num_comments'].sum()) if not filtered.empty else 0:,}", "Total Comments"),
    (f"{len(keywords_df):,}",                               "Keyword Hits"),
    (f"{filtered['subreddit'].nunique()}",                  "Active Subreddits"),
]
for col, (val, lbl) in zip([c1,c2,c3,c4,c5], kpi_data):
    with col:
        st.markdown(
            f"<div class='metric-card'><div class='val'>{val}</div>"
            f"<div class='lbl'>{lbl}</div></div>",
            unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 5. Tabs
# ─────────────────────────────────────────
# 탭 변수 할당 순서 (레이블 순서와 동일):
# tab1=Trend, tab2=Ingredient, tab_voc=VOC, tab3=Regional,
# tab5=MarketingPlaybook, tab4=RawData, tab6=Overview
tab1, tab2, tab_voc, tab3, tab5, tab4, tab6 = st.tabs([
    "📊 Trend Dashboard",
    "🧪 Ingredient Keywords",
    "💬 Consumer VOC",
    "🌏 Regional Comparison",
    "🎯 Marketing Playbook 12",
    "📋 Raw Data",
    "📌 Overview",
])

# ═══════════════════════════════════════════
# TAB 1: Trend Dashboard
# ═══════════════════════════════════════════
with tab1:
    with st.expander("📊 Data Source Context — Subreddit Weight (Post Count & Avg Score)", expanded=False):
        src_ctx = (posts_df.groupby("subreddit")["score"]
                   .agg(post_count="count", avg_score="mean")
                   .reset_index().sort_values("post_count", ascending=False))
        src_ctx["avg_score"] = src_ctx["avg_score"].round(1)
        st.caption(f"Total: {len(posts_df):,} posts · {posts_df['subreddit'].nunique()} subreddits | Filtered: {len(filtered):,} posts")
        st.dataframe(src_ctx, use_container_width=True, hide_index=True, height=250)

    st.markdown("<div class='section-header'>📊 Trending Posts — Top 10</div>",
                unsafe_allow_html=True)
    top10 = filtered.nlargest(10, "score")[
        ["subreddit","title","score","num_comments","upvote_ratio","region","reddit_url"]
    ].reset_index(drop=True)

    for i, row in top10.iterrows():
        ratio_pct  = f"{row['upvote_ratio']*100:.0f}%" if pd.notna(row["upvote_ratio"]) else "-"
        url        = row.get("reddit_url", "")
        title_str  = str(row["title"])[:100] + ("..." if len(str(row["title"])) > 100 else "")
        title_html = (f'<a href="{url}" target="_blank" style="color:#1a1a2e;text-decoration:none;">'
                      f'{title_str}</a>') if url else title_str
        st.markdown(f"""
        <div class='post-card'>
            <div class='ptitle'>#{i+1} &nbsp; {title_html}</div>
            <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                Region: {row['region']} &nbsp;|&nbsp;
                <span class='pscore'>⭐ {int(row['score']):,}</span> &nbsp;|&nbsp;
                💬 {int(row['num_comments']):,} &nbsp;|&nbsp; 👍 {ratio_pct}
                {f'&nbsp;|&nbsp;<a href="{url}" target="_blank" style="font-size:.75rem;color:#718096;">source ↗</a>' if url else ''}
            </div>
        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB 2: Ingredient Keywords
# ═══════════════════════════════════════════
with tab2:
    with st.expander("📊 Data Source Context — Subreddit Weight (Post Count & Avg Score)", expanded=False):
        src_ctx2 = (posts_df.groupby("subreddit")["score"]
                    .agg(post_count="count", avg_score="mean")
                    .reset_index().sort_values("post_count", ascending=False))
        src_ctx2["avg_score"] = src_ctx2["avg_score"].round(1)
        st.caption(f"Total: {len(posts_df):,} posts · {posts_df['subreddit'].nunique()} subreddits | Filtered: {len(filtered):,} posts")
        st.dataframe(src_ctx2, use_container_width=True, hide_index=True, height=250)

    if keywords_df.empty:
        st.warning("⚠️ No data in keyword_hits table.  Run `keyword_matcher.py` to populate it.")
        st.markdown("""
        ### 💡 How keyword matching works
        Run `keyword_matcher.py` in the same folder as `reddit_data.db`.
        It scans every post title and body for ingredient keywords and writes
        results to the `keyword_hits` table — this tab will activate automatically.
        """)
    else:
        st.markdown("<div class='section-header'>🧪 Ingredient Rankings (Score-weighted)</div>",
                    unsafe_allow_html=True)
        kw_agg = (keywords_df.groupby("keyword")
                  .agg(mentions=("keyword","count"), total_score=("score","sum"),
                       avg_score=("score","mean"), total_comments=("num_comments","sum"))
                  .reset_index().sort_values("total_score", ascending=False).head(30))
        col_a, col_b = st.columns(2)
        with col_a:
            fig_kw1 = px.bar(kw_agg.head(20), x="total_score", y="keyword",
                             orientation="h", color="mentions",
                             color_continuous_scale="Blues",
                             title="Total Score by Ingredient (Top 20)",
                             labels={"keyword":"Ingredient","total_score":"Total Score","mentions":"Mentions"})
            fig_kw1.update_layout(height=500, yaxis={"categoryorder":"total ascending"})
            st.plotly_chart(fig_kw1, use_container_width=True)
        with col_b:
            fig_kw2 = px.scatter(kw_agg, x="mentions", y="avg_score",
                                 size="total_comments", hover_name="keyword",
                                 color="total_score", color_continuous_scale="RdYlGn",
                                 title="Ingredient Bubble Chart: Mentions × Avg Score × Comments",
                                 labels={"mentions":"Mentions","avg_score":"Avg Score"})
            fig_kw2.update_layout(height=500)
            st.plotly_chart(fig_kw2, use_container_width=True)

        if "keyword_category" in keywords_df.columns:
            st.markdown("<div class='section-header'>📂 Category Trends</div>", unsafe_allow_html=True)
            cat_agg = (keywords_df.groupby("keyword_category")
                       .agg(mentions=("keyword","count"), total_score=("score","sum"))
                       .reset_index().sort_values("total_score", ascending=False))
            fig_cat = px.treemap(cat_agg, path=["keyword_category"],
                                 values="total_score", color="mentions",
                                 color_continuous_scale="Teal",
                                 title="Category Treemap (size = Total Score, color = Mentions)")
            fig_cat.update_layout(height=400)
            st.plotly_chart(fig_cat, use_container_width=True)

# ═══════════════════════════════════════════
# TAB VOC: Consumer VOC Analysis
# ═══════════════════════════════════════════
with tab_voc:
    with st.expander("📊 Data Source Context — Subreddit Weight (Post Count & Avg Score)", expanded=False):
        src_ctx_voc = (posts_df.groupby("subreddit")["score"]
                       .agg(post_count="count", avg_score="mean")
                       .reset_index().sort_values("post_count", ascending=False))
        src_ctx_voc["avg_score"] = src_ctx_voc["avg_score"].round(1)
        st.caption(f"Total: {len(posts_df):,} posts · {posts_df['subreddit'].nunique()} subreddits | Filtered: {len(filtered):,} posts")
        st.dataframe(src_ctx_voc, use_container_width=True, hide_index=True, height=250)

    st.markdown("""
    <div class='voc-header'>
        <h3>💬 Consumer VOC Analysis — Complaints & Improvement Requests</h3>
        <p>Automatically detects consumer complaints and improvement requests
        from Reddit post titles and body text (selftext).<br>
        <b>URS (User Requirement Specification):</b> The priority matrix at the bottom
        ranks product improvement priorities by complaint frequency × engagement.</p>
    </div>
    """, unsafe_allow_html=True)

    COMPLAINT_DICT = {
        "Pilling / Balling Up":          ["pilling","pills","rub off","ball up","peeling off","flakes off"],
        "Irritation / Breakouts":        ["irritation","irritated","stings","burning","breakout",
                                          "purge","purging","flare","redness","rash","reaction","allergic"],
        "Dryness / Tightness":           ["dry","tight","flaky","dehydrated","peeling","dryness","flaking"],
        "Oiliness / Excess Sebum":       ["oily","greasy","shiny","sebum","excess oil","slippery"],
        "Clogged Pores / Blackheads":    ["clogged","clogs","pores","blackhead","blackheads",
                                          "congested","congestion","comedone"],
        "Hyperpigmentation / Dark Spots":["hyperpigmentation","dark spots","melasma","uneven",
                                          "discoloration","pigmentation"],
        "Unpleasant Scent / Texture":    ["smell","smells","sticky","tacky","heavy texture",
                                          "thick","goopy","fragrance"],
        "No Visible Effect":             ["doesn't work","no effect","useless","waste",
                                          "disappointed","overhyped","overrated"],
    }
    IMPROVEMENT_DICT = {
        "Formula Improvement":      ["wish it had","needs more","should add","would be better with",
                                     "improve formula","better formula","reformulate"],
        "Packaging Improvement":    ["packaging","pump","dispenser","tube","jar","too small",
                                     "bigger size","refill","travel size"],
        "Pricing Concerns":         ["too expensive","price drop","overpriced","cheaper",
                                     "affordable","dupe","budget friendly"],
        "Scent / Shade Options":    ["fragrance free","no scent","unscented","color","tint","shade"],
        "Texture / Absorption":     ["takes too long","absorb faster","lighter texture",
                                     "more lightweight","less sticky","lighter formula"],
        "Sensitive Skin Friendly":  ["sensitive skin","gentle","non-irritating",
                                     "hypoallergenic","fragrance free version"],
    }

    def count_voc(df, kw_dict, label_col):
        results = []
        for cat, terms in kw_dict.items():
            pattern = "|".join(terms)
            mt = df[df["title"].str.contains(pattern, case=False, na=False)]
            mb = df[df["selftext"].str.contains(pattern, case=False, na=False)]
            matched = pd.concat([mt, mb]).drop_duplicates(subset="id")
            results.append({
                label_col:     cat,
                "Mentions":    len(matched),
                "Avg Score":   round(matched["score"].mean(), 1) if len(matched) > 0 else 0,
                "Total Comments": int(matched["num_comments"].sum()) if len(matched) > 0 else 0,
                "Search terms (sample)": ", ".join(terms[:3]) + ("…" if len(terms) > 3 else ""),
            })
        return pd.DataFrame(results).sort_values("Mentions", ascending=False)

    complaint_df = count_voc(filtered, COMPLAINT_DICT, "Complaint Type")
    improve_df   = count_voc(filtered, IMPROVEMENT_DICT, "Request Type")

    st.markdown("<div class='section-header'>😤 Complaint Analysis</div>", unsafe_allow_html=True)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        fig_comp = px.bar(complaint_df, x="Mentions", y="Complaint Type",
                          orientation="h", color="Avg Score",
                          color_continuous_scale="RdYlGn_r",
                          title="Complaints by Type (color = Avg Score)",
                          labels={"Complaint Type":"Complaint Type","Mentions":"Post Mentions"})
        fig_comp.update_layout(height=380, yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig_comp, use_container_width=True)
    with col_c2:
        st.dataframe(complaint_df[["Complaint Type","Mentions","Avg Score","Total Comments"]],
                     use_container_width=True, hide_index=True, height=350)

    if not complaint_df.empty and complaint_df["Mentions"].max() > 0:
        top_cat   = complaint_df.iloc[0]["Complaint Type"]
        top_terms = COMPLAINT_DICT[top_cat]
        pat       = "|".join(top_terms)
        samples   = filtered[
            filtered["title"].str.contains(pat, case=False, na=False) |
            filtered["selftext"].str.contains(pat, case=False, na=False)
        ].nlargest(5, "score")[["subreddit","title","score","num_comments","upvote_ratio","reddit_url"]]
        st.markdown(f"**💡 Top posts for '{top_cat}' — copywriting & product improvement source**")
        for _, row in samples.iterrows():
            ratio_pct  = f"{row['upvote_ratio']*100:.0f}%" if pd.notna(row["upvote_ratio"]) else "-"
            url        = row.get("reddit_url", "")
            title_str  = str(row["title"])
            title_html = (f'<a href="{url}" target="_blank" style="color:#1a1a2e;text-decoration:none;">'
                          f'{title_str}</a>') if url else title_str
            st.markdown(f"""
            <div class='post-card'>
                <div class='ptitle'>📌 {title_html}</div>
                <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                    <span class='pscore'>⭐ {int(row['score']):,}</span>
                    &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}
                    &nbsp;|&nbsp; 👍 {ratio_pct}
                    {f'&nbsp;|&nbsp;<a href="{url}" target="_blank" style="font-size:.75rem;color:#718096;">source ↗</a>' if url else ''}
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>✅ Improvement Request Analysis</div>",
                unsafe_allow_html=True)
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        fig_imp = px.bar(improve_df, x="Mentions", y="Request Type",
                         orientation="h", color="Avg Score",
                         color_continuous_scale="Blues",
                         title="Improvement Requests by Type",
                         labels={"Request Type":"Request Type","Mentions":"Post Mentions"})
        fig_imp.update_layout(height=340, yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig_imp, use_container_width=True)
    with col_i2:
        st.dataframe(improve_df[["Request Type","Mentions","Avg Score","Total Comments"]],
                     use_container_width=True, hide_index=True, height=310)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>📋 URS Priority Matrix — Product Improvement Roadmap</div>",
                unsafe_allow_html=True)
    st.markdown("""
    > **Calculation:** `Priority Score = Mentions × Avg Score`
    > Higher frequency + higher engagement = stronger consumer pain signal.
    """)
    complaint_df["Priority Score"] = (complaint_df["Mentions"] * complaint_df["Avg Score"]).round(0)
    col_u1, col_u2 = st.columns([3, 2])
    with col_u1:
        fig_urs = px.scatter(complaint_df, x="Mentions", y="Avg Score",
                             size="Priority Score", text="Complaint Type",
                             color="Priority Score", color_continuous_scale="RdYlGn_r",
                             title="URS Priority Matrix (bubble size = Priority Score)",
                             labels={"Mentions":"Frequency (posts)","Avg Score":"Engagement (Avg Score)"})
        fig_urs.update_traces(textposition="top center", textfont_size=9)
        fig_urs.update_layout(height=420)
        st.plotly_chart(fig_urs, use_container_width=True)
    with col_u2:
        top_urs = (complaint_df.nlargest(5, "Priority Score")
                   [["Complaint Type","Mentions","Avg Score","Priority Score"]]
                   .reset_index(drop=True))
        top_urs.index += 1
        st.markdown("**🔴 Immediate Improvement — Top 5**")
        for i, row in top_urs.iterrows():
            label = "🔴" if i == 1 else ("🟠" if i == 2 else "🟡")
            st.markdown(f"""
            <div class='urs-card'>
                <div class='uc-title'>{label} #{i} {row['Complaint Type']}</div>
                <div class='uc-meta'>Mentions: {int(row['Mentions'])} &nbsp;|&nbsp;
                    Avg Score: <span class='uc-score'>{row['Avg Score']:,.0f}</span></div>
                <div class='uc-meta'>Priority Score: <b>{row['Priority Score']:,.0f}</b></div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Complaint Posts Detected", f"{int(complaint_df['Mentions'].sum()):,}")
    with m2: st.metric("Complaint Types",           f"{len(complaint_df)}")
    with m3: st.metric("Improvement Request Posts", f"{int(improve_df['Mentions'].sum()):,}")
    with m4: st.metric("Improvement Request Types", f"{len(improve_df)}")

# ═══════════════════════════════════════════
# TAB 3: Regional Comparison
# ═══════════════════════════════════════════
with tab3:
    with st.expander("📊 Data Source Context — Subreddit Weight (Post Count & Avg Score)", expanded=False):
        src_ctx3 = (posts_df.groupby("subreddit")["score"]
                    .agg(post_count="count", avg_score="mean")
                    .reset_index().sort_values("post_count", ascending=False))
        src_ctx3["avg_score"] = src_ctx3["avg_score"].round(1)
        st.caption(f"Total: {len(posts_df):,} posts · {posts_df['subreddit'].nunique()} subreddits | Filtered: {len(filtered):,} posts")
        st.dataframe(src_ctx3, use_container_width=True, hide_index=True, height=250)

    # ── Monthly trend by region group ─────────────────────────
    st.markdown("<div class='section-header'>📈 Monthly Trend by Region Group</div>",
                unsafe_allow_html=True)

    filtered["ym"] = filtered["fetch_date"].dt.to_period("M").astype(str)
    monthly_rg = (filtered.groupby(["ym","region_group"])
                  .size().reset_index(name="posts").sort_values("ym"))

    if not monthly_rg.empty:
        fig_mt = px.line(monthly_rg, x="ym", y="posts", color="region_group",
                         markers=True,
                         title="Monthly Post Count — by Region Group",
                         labels={"ym":"Month","posts":"Post Count","region_group":"Region Group"})
        fig_mt.update_layout(height=320, xaxis_tickangle=-20)
        st.plotly_chart(fig_mt, use_container_width=True)

    # ════════════════════════════════════════
    # Regional Ingredient Comparison
    # ════════════════════════════════════════
    st.markdown("<div class='section-header'>🧴 Regional Ingredient Comparison</div>",
                unsafe_allow_html=True)
    st.caption("Ingredients detected by scanning post titles and body text directly from collected posts.")

    ing_df = calc_region_ingredients(filtered)

    if ing_df.empty:
        st.info("No ingredient data found in current filter. Try 'All' filters.")
    else:
        # Grouped bar chart: region × ingredient
        focus_groups = ["Global · General", "Asia-Pacific", "Western Markets (NA/EU)"]
        ing_focus    = ing_df[ing_df["region_group"].isin(focus_groups)]

        if not ing_focus.empty:
            fig_ing = px.bar(ing_focus, x="ingredient", y="mentions", color="region_group",
                             barmode="group",
                             color_discrete_map={
                                 "Global · General":        "#185FA5",
                                 "Asia-Pacific":            "#1D9E75",
                                 "Western Markets (NA/EU)": "#D85A30",
                             },
                             title="Region Group × Ingredient Mention Comparison"
                                   " — darker = higher interest",
                             labels={"ingredient":"Ingredient","mentions":"Mentions",
                                     "region_group":"Region Group"})
            fig_ing.update_layout(height=380, xaxis_tickangle=-20)
            st.plotly_chart(fig_ing, use_container_width=True)

        # Global vs Asia comparison table
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**🔬 Global vs Asia-Pacific — Ingredient Interest Gap**")
            gb_ing  = ing_df[ing_df["region_group"] == "Global · General"].set_index("ingredient")["mentions"]
            ap_ing  = ing_df[ing_df["region_group"] == "Asia-Pacific"].set_index("ingredient")["mentions"]
            all_ing = set(gb_ing.index) | set(ap_ing.index)
            cmp_rows = []
            for ing in sorted(all_ing):
                g = int(gb_ing.get(ing, 0))
                a = int(ap_ing.get(ing, 0))
                diff = g - a
                cmp_rows.append({
                    "Ingredient": ing,
                    "Global": g,
                    "Asia-Pacific": a,
                    "Gap": f"+{diff}" if diff > 0 else str(diff)
                })
            cmp_df = pd.DataFrame(cmp_rows).sort_values("Global", ascending=False)
            st.dataframe(cmp_df, use_container_width=True, hide_index=True, height=320)

        with col_t2:
            st.markdown("**🏆 Top 3 Ingredients by Region Group**")
            for grp in REGION_GROUP_MAP.keys():
                grp_data = ing_df[ing_df["region_group"] == grp].nlargest(3, "mentions")
                if grp_data.empty:
                    continue
                top3 = " · ".join(
                    [f"{i+1}. {row['ingredient']}" for i, (_, row) in enumerate(grp_data.iterrows())]
                )
                st.markdown(f"""
                <div style='margin-bottom:8px;padding:6px 10px;
                            background:var(--background-color,#f8f9fa);
                            border-left:3px solid #185FA5;border-radius:0 6px 6px 0;'>
                    <div style='font-size:.85rem;font-weight:600;'>{grp}</div>
                    <div style='font-size:.8rem;color:#718096;'>{top3}</div>
                </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB 5: Marketing Playbook 12
# ═══════════════════════════════════════════
with tab5:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f3460,#533483);color:white;
                padding:18px 24px;border-radius:12px;margin-bottom:20px'>
        <h3 style='margin:0;font-family:DM Serif Display,serif'>
            🎯 Reddit Data-Driven Marketing Playbook — 12 Techniques
        </h3>
        <p style='margin:6px 0 0 0;opacity:.85;font-size:.9rem'>
            4 domains × 12 techniques — actionable insights from real collected data
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📊 All 12 Techniques Overview (click to expand)", expanded=False):
        overview = {
            "Domain": ["A.Content"]*3 + ["B.Positioning"]*3 + ["C.Targeting"]*3 + ["D.Risk"]*3,
            "Technique": [
                "1. VOC Mirror Copywriting","2. Trend Pre-emption Calendar","3. Unmet Needs Storytelling",
                "4. Ingredient Traffic Light","5. Competitor Red Signal","6. Climate Formula Marketing",
                "7. Community KOL Discovery","8. 3-Axis Targeted Ads","9. Gallery Before & After",
                "10. Real-time Crisis Detection","11. Controversy Education","12. Crosspost Viral Amplification"
            ],
            "Key Data Fields": [
                "title·selftext·score·upvote_ratio","keyword weighted index weekly delta",
                "selftext negative sentiment","score·upvote_ratio 3-month trend",
                "competitor keywords + negative sentiment","local subreddit + author_flair",
                "total_awards_received·author","author_flair·created_utc·subreddit",
                "is_gallery·score","upvote_ratio·negative sentiment·time=day",
                "upvote_ratio 0.5~0.7 band","num_crossposts"
            ],
            "Difficulty": ["⭐⭐"]*3+["⭐⭐⭐"]*3+["⭐⭐","⭐⭐⭐⭐","⭐⭐"]+["⭐⭐⭐","⭐⭐","⭐⭐"],
            "Time to Effect": ["Immediate","4~8 weeks","1~3 months","3~6 months","1~2 months",
                               "3~6 months","1~3 months","Immediate","Immediate",
                               "Immediate","2~4 months","Immediate"],
            "Core KPI": [
                "Ad CTR +20~40%","SEO traffic +30%","Brand resonance↑",
                "Brand trust↑","Market share shift","Export conversion↑",
                "CPE reduction","ROAS +25~50%","PDP conversion +15~35%",
                "Crisis response time↓","SEO evergreen traffic","Trend timing capture"
            ]
        }
        st.dataframe(pd.DataFrame(overview), use_container_width=True, hide_index=True, height=460)

    st.markdown("<br>", unsafe_allow_html=True)

    # Domain A
    st.markdown("<div class='section-header'>🅐 Domain A. Content Marketing — \"Speak the consumer's language\"</div>",
                unsafe_allow_html=True)

    with st.expander("📝 Technique 1 — VOC Mirror Copywriting | Ad CTR +20~40%", expanded=True):
        st.markdown("""
        > **Concept:** Posts with score ≥ threshold + upvote_ratio ≥ threshold = community-validated language.
        > Use these exact phrases as ad copy for 20~40% CTR improvement.
        """)
        voc_score = st.slider("Min Score", 100, 2000, 300, 50, key="voc_score")
        voc_ratio = st.slider("Min Upvote Ratio", 0.70, 1.00, 0.85, 0.01, key="voc_ratio")
        voc_df = filtered[
            (filtered["score"] >= voc_score) & (filtered["upvote_ratio"] >= voc_ratio)
        ].nlargest(15, "score")[["subreddit","title","score","upvote_ratio","num_comments","region_group","reddit_url"]]
        if voc_df.empty:
            st.info("No posts match criteria. Lower the score or ratio threshold.")
        else:
            st.markdown(f"**✅ {len(voc_df)} posts found — use these titles as copywriting source**")
            for _, row in voc_df.iterrows():
                url        = row.get("reddit_url", "")
                title_str  = str(row["title"])
                title_html = (f'<a href="{url}" target="_blank" style="color:#1a1a2e;text-decoration:none;">'
                              f'{title_str}</a>') if url else title_str
                st.markdown(f"""
                <div class='post-card'>
                    <div class='ptitle'>💬 {title_html}</div>
                    <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp; {row['region_group']}
                        &nbsp;|&nbsp; <span class='pscore'>⭐ {int(row['score']):,}</span>
                        &nbsp;|&nbsp; 👍 {row['upvote_ratio']*100:.0f}%
                        &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}
                        {f'&nbsp;|&nbsp;<a href="{url}" target="_blank" style="font-size:.75rem;color:#718096;">source ↗</a>' if url else ''}
                    </div>
                </div>""", unsafe_allow_html=True)

    with st.expander("📅 Technique 2 — Trend Pre-emption Calendar | SEO +30%", expanded=False):
        st.markdown("""
        > **Concept:** Calculate weighted trend index (Score × upvote_ratio × log(comments))
        > per ingredient to publish content 2~4 weeks ahead of competitors.
        """)
        if keywords_df.empty:
            st.warning("keyword_hits data required. Run keyword_matcher.py first.")
        else:
            kw_trend = keywords_df.copy()
            kw_trend["weighted_index"] = (
                kw_trend["score"] * kw_trend["upvote_ratio"].fillna(0.75) *
                np.log1p(kw_trend["num_comments"])
            )
            kw_sum = (kw_trend.groupby(["keyword","keyword_category"])
                      .agg(mentions=("keyword","count"), weighted_index=("weighted_index","sum"),
                           avg_score=("score","mean"), avg_upvote=("upvote_ratio","mean"))
                      .reset_index().sort_values("weighted_index", ascending=False).head(20))
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                fig_tr = px.bar(kw_sum, x="weighted_index", y="keyword",
                                orientation="h", color="keyword_category",
                                title="Weighted Trend Index by Ingredient (Top 20)",
                                labels={"keyword":"Ingredient","keyword_category":"Category"})
                fig_tr.update_layout(height=550, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_tr, use_container_width=True)
            with col_t2:
                fig_tr2 = px.scatter(kw_sum, x="mentions", y="weighted_index",
                                     size="avg_score", color="keyword_category",
                                     hover_name="keyword",
                                     title="Mentions vs Weighted Trend Index Bubble Chart")
                fig_tr2.update_layout(height=550)
                st.plotly_chart(fig_tr2, use_container_width=True)

    with st.expander("💔 Technique 3 — Unmet Needs Storytelling | Brand resonance maximization",
                     expanded=False):
        st.markdown("""
        > **Concept:** Find unresolved consumer frustrations in post bodies
        > and turn them into product origin stories.
        > 💡 **Tip:** Use alongside the Consumer VOC tab.
        """)
        PAIN = {
            "Pilling":         ["pilling","pills","rub off","ball up"],
            "Irritation":      ["irritation","stings","burning","breakout","purge","flare"],
            "Dryness":         ["dry","tight","flaky","dehydrated","peeling"],
            "Oiliness":        ["oily","greasy","shiny","sebum"],
            "Clogged Pores":   ["clogged","pores","blackhead","congested"],
            "Hyperpigmentation":["hyperpigmentation","dark spots","melasma","uneven"],
        }
        pain_rows = []
        for lbl, terms in PAIN.items():
            pat     = "|".join(terms)
            matched = posts_df[posts_df["selftext"].str.contains(pat, case=False, na=False)]
            pain_rows.append({
                "Skin Concern":      lbl,
                "Mentions":          len(matched),
                "Avg Score":         round(matched["score"].mean(), 1) if len(matched) > 0 else 0,
                "Total Comments":    int(matched["num_comments"].sum()),
                "Keywords (sample)": ", ".join(terms[:3]),
            })
        pain_df = pd.DataFrame(pain_rows).sort_values("Mentions", ascending=False)
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig_pain = px.bar(pain_df, x="Mentions", y="Skin Concern", orientation="h",
                              color="Avg Score", color_continuous_scale="RdYlGn_r",
                              title="Skin Concern Mentions (Unmet Needs)")
            fig_pain.update_layout(height=350, yaxis={"categoryorder":"total ascending"})
            st.plotly_chart(fig_pain, use_container_width=True)
        with col_p2:
            st.dataframe(pain_df, use_container_width=True, hide_index=True, height=280)

    # Domain B
    st.markdown("<div class='section-header'>🅑 Domain B. Product Positioning — \"Data-proven differentiation\"</div>",
                unsafe_allow_html=True)

    with st.expander("🚦 Technique 4 — Ingredient Traffic Light Positioning | Brand trust innovation",
                     expanded=True):
        if keywords_df.empty:
            st.warning("keyword_hits data required. Run keyword_matcher.py first.")
        else:
            sig = (keywords_df.groupby("keyword")
                   .agg(mentions=("keyword","count"), avg_score=("score","mean"),
                        avg_upvote=("upvote_ratio","mean"), total_score=("score","sum"))
                   .reset_index())
            sig = sig[sig["mentions"] >= 2]
            def signal(r):
                if r >= 0.88: return "🟢 Green (Adopt Now)"
                elif r >= 0.75: return "🟡 Yellow (Monitor)"
                else: return "🔴 Red (Hold)"
            sig["Signal"] = sig["avg_upvote"].apply(signal)
            col_s1, col_s2 = st.columns([3,2])
            with col_s1:
                fig_sig = px.scatter(sig, x="avg_upvote", y="avg_score",
                                     size="total_score", color="Signal", hover_name="keyword",
                                     color_discrete_map={
                                         "🟢 Green (Adopt Now)": "#22c55e",
                                         "🟡 Yellow (Monitor)":  "#f59e0b",
                                         "🔴 Red (Hold)":        "#ef4444"
                                     },
                                     title="Ingredient Safety Traffic Light Chart",
                                     labels={"avg_upvote":"Avg Upvote Ratio","avg_score":"Avg Score"})
                fig_sig.add_vline(x=0.88, line_dash="dash", line_color="green", annotation_text="Green threshold")
                fig_sig.add_vline(x=0.75, line_dash="dash", line_color="orange", annotation_text="Yellow threshold")
                fig_sig.update_layout(height=450)
                st.plotly_chart(fig_sig, use_container_width=True)
            with col_s2:
                for sl in ["🟢 Green (Adopt Now)","🟡 Yellow (Monitor)","🔴 Red (Hold)"]:
                    sub = sig[sig["Signal"] == sl].sort_values("total_score", ascending=False)
                    st.markdown(f"**{sl}** — {len(sub)} ingredients")
                    if not sub.empty:
                        st.caption(", ".join(sub.head(6)["keyword"].tolist()))
                    st.markdown("---")

    with st.expander("⚔️ Technique 5 — Competitor Red Signal Counter-positioning", expanded=False):
        NEG = ["pilling","breakout","irritation","stings","burning","bad","worst",
               "avoid","terrible","hate","doesn't work","useless","rash","reaction"]
        controversy = filtered[
            (filtered["upvote_ratio"] < 0.65) & (filtered["score"] >= 50)
        ].copy()
        st.markdown(f"**📊 Low-support posts** (Score≥50, Upvote<65%): {len(controversy)} posts")
        if not controversy.empty:
            controversy_show = (controversy[["subreddit","title","score","upvote_ratio",
                                             "num_comments","region_group","reddit_url"]]
                                .sort_values("score", ascending=False).head(10).copy())
            controversy_show["link"] = controversy_show["reddit_url"]
            st.dataframe(
                controversy_show[["subreddit","title","score","upvote_ratio","num_comments",
                                  "region_group","link"]],
                column_config={"link": st.column_config.LinkColumn("🔗 Link", display_text="↗ Open")},
                use_container_width=True, hide_index=True, height=280)

    with st.expander("🌍 Technique 6 — Climate Formula Marketing | Export conversion maximization",
                     expanded=False):
        if keywords_df.empty:
            st.warning("keyword_hits data required.")
        else:
            cl_agg = (keywords_df.groupby(["region","keyword_category"])
                      .agg(mentions=("keyword","count"), total_score=("score","sum"))
                      .reset_index())
            pv = cl_agg.pivot_table(index="region", columns="keyword_category",
                                    values="total_score", aggfunc="sum", fill_value=0)
            fig_cl = px.imshow(pv, color_continuous_scale="YlOrRd",
                               title="Region × Ingredient Category Score Heatmap (Export Formula Map)",
                               aspect="auto")
            fig_cl.update_layout(height=400)
            st.plotly_chart(fig_cl, use_container_width=True)

    # Domain C
    st.markdown("<div class='section-header'>🅒 Domain C. Target Marketing — \"Precision segment targeting\"</div>",
                unsafe_allow_html=True)

    with st.expander("⭐ Technique 7 — Community-Verified KOL Discovery | Influence over follower count",
                     expanded=True):
        award_df = filtered[filtered["total_awards_received"] >= 1].copy()
        if award_df.empty:
            st.info("No awarded posts found in current filter.")
        else:
            kol_df = (award_df.groupby("author")
                      .agg(award_posts=("total_awards_received","count"),
                           total_awards=("total_awards_received","sum"),
                           total_score=("score","sum"), avg_score=("score","mean"),
                           top_subreddit=("subreddit", lambda x: x.value_counts().index[0]))
                      .reset_index().sort_values("total_awards", ascending=False))
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                fig_kol = px.bar(kol_df.head(15), x="total_awards", y="author",
                                 orientation="h", color="total_score",
                                 color_continuous_scale="Oranges",
                                 title="Community-Verified KOL Top 15 (by Awards)",
                                 labels={"author":"Author","total_awards":"Total Awards"})
                fig_kol.update_layout(height=450, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_kol, use_container_width=True)
            with col_k2:
                st.dataframe(
                    kol_df.head(10)[["author","award_posts","total_awards","avg_score","top_subreddit"]],
                    use_container_width=True, hide_index=True, height=380)

    with st.expander("🎯 Technique 8 — 3-Axis Targeted Advertising | ROAS +25~50%", expanded=False):
        matrix = {
            "Segment":       ["Dry + Korea + Winter","Oily + SEA + Year-round",
                              "Sensitive + All regions","Combo + NA + Spring"],
            "Ad Message":    ["Your skin feels tight the moment you turn on the heat?",
                              "Moisture that stays fresh even when you sweat",
                              "Tired of reading ingredient labels? We filtered it all for you.",
                              "T-zone shiny, rest of face dry — you know this feeling"],
            "Key Ingredient":["Ceramide NP + Squalane","Niacinamide + PHA",
                              "Centella + Allantoin","Low-conc AHA + HA"],
            "Season":        ["Nov~Feb","Year-round","Year-round","Mar~May"],
        }
        st.dataframe(pd.DataFrame(matrix), use_container_width=True, hide_index=True)

    with st.expander("📸 Technique 9 — Gallery Before & After Social Proof | PDP conversion +15~35%",
                     expanded=False):
        gallery_df  = filtered[filtered["is_gallery"] == 1].copy()
        non_gallery = filtered[filtered["is_gallery"] != 1].copy()
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1: st.metric("Gallery Posts",   f"{len(gallery_df)}")
        with col_g2:
            avg_g  = gallery_df["score"].mean()  if len(gallery_df)  > 0 else 0
            avg_ng = non_gallery["score"].mean() if len(non_gallery) > 0 else 0
            st.metric("Gallery Avg Score", f"{avg_g:.0f}", delta=f"{avg_g-avg_ng:+.0f} vs regular")
        with col_g3: st.metric("Score≥200 Gallery", f"{len(gallery_df[gallery_df['score']>=200])}")

    # Domain D
    st.markdown("<div class='section-header'>🅓 Domain D. Risk Marketing — \"Turn crisis into opportunity\"</div>",
                unsafe_allow_html=True)

    with st.expander("🚨 Technique 10 — Real-time Ingredient Crisis Early Detection | 24~48h faster response",
                     expanded=True):
        risk_thresh = st.slider("Crisis threshold (upvote ratio)", 0.40, 0.70, 0.60, 0.01, key="risk_ratio")
        risk_min_sc = st.slider("Min Score (noise filter)", 10, 200, 30, 10, key="risk_score")
        risk_posts  = filtered[
            (filtered["upvote_ratio"] < risk_thresh) & (filtered["score"] >= risk_min_sc)
        ].sort_values("score", ascending=False)
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("🔴 Crisis Posts Detected", f"{len(risk_posts)}",
                      delta=f"{len(risk_posts)/max(len(filtered),1)*100:.1f}% of total")
        with col_r2:
            st.metric("Avg Score", f"{risk_posts['score'].mean():.0f}" if len(risk_posts) > 0 else "0")
        with col_r3:
            st.metric("Max Comments", f"{int(risk_posts['num_comments'].max()):,}" if len(risk_posts) > 0 else "0")
        if not risk_posts.empty:
            col_ra, col_rb = st.columns(2)
            with col_ra:
                fig_risk = px.scatter(risk_posts, x="upvote_ratio", y="score",
                                      size="num_comments", color="subreddit", hover_data=["title"],
                                      title=f"⚠️ Crisis Posts (upvote ratio < {risk_thresh:.0%})",
                                      labels={"upvote_ratio":"Upvote Ratio","score":"Score"})
                fig_risk.add_vline(x=risk_thresh, line_dash="dash", line_color="red")
                fig_risk.update_layout(height=380)
                st.plotly_chart(fig_risk, use_container_width=True)
            with col_rb:
                st.markdown("**🚨 Immediate action required (highest Score first)**")
                for _, row in risk_posts.head(7).iterrows():
                    ratio_pct  = f"{row['upvote_ratio']*100:.0f}%"
                    url        = row.get("reddit_url", "")
                    title_str  = str(row["title"])[:90]
                    title_html = (f'<a href="{url}" target="_blank" style="color:#1a1a2e;text-decoration:none;">'
                                  f'{title_str}</a>') if url else title_str
                    st.markdown(f"""
                    <div class='post-card' style='border-left-color:#ef4444'>
                        <div class='ptitle'>⚠️ {title_html}</div>
                        <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                            <span style='color:#ef4444;font-weight:700'>
                            ⭐ {int(row['score']):,} | 👍 {ratio_pct}</span>
                            {f'&nbsp;|&nbsp;<a href="{url}" target="_blank" style="font-size:.75rem;color:#718096;">source ↗</a>' if url else ''}
                        </div>
                    </div>""", unsafe_allow_html=True)

    with st.expander("📚 Technique 11 — Controversy Education Marketing | SEO evergreen traffic",
                     expanded=False):
        edu_posts = filtered[
            (filtered["upvote_ratio"] >= 0.50) & (filtered["upvote_ratio"] < 0.70) &
            (filtered["score"] >= 30)
        ].copy()
        col_e1, col_e2 = st.columns(2)
        with col_e1: st.metric("Controversy Posts", f"{len(edu_posts)}")
        with col_e2: st.metric("Avg Score", f"{edu_posts['score'].mean():.0f}" if len(edu_posts) > 0 else "0")

    with st.expander("🔥 Technique 12 — Crosspost Viral Amplification | Trend timing capture",
                     expanded=True):
        cp_thresh  = st.slider("Min crossposts", 1, 10, 2, 1, key="cp_threshold")
        viral_posts = filtered[filtered["num_crossposts"] >= cp_thresh].copy()
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1: st.metric("🔥 Viral Posts", f"{len(viral_posts)}")
        with col_v2: st.metric("Avg Crossposts", f"{viral_posts['num_crossposts'].mean():.1f}" if len(viral_posts)>0 else "0")
        with col_v3: st.metric("Max Crossposts", f"{int(viral_posts['num_crossposts'].max())}" if len(viral_posts)>0 else "0")
        if not viral_posts.empty:
            st.markdown("**⚡ Immediate content action needed (highest crossposts first)**")
            for _, row in viral_posts.nlargest(7, "num_crossposts").iterrows():
                url        = row.get("reddit_url", "")
                title_str  = str(row["title"])[:85]
                title_html = (f'<a href="{url}" target="_blank" style="color:#1a1a2e;text-decoration:none;">'
                              f'{title_str}</a>') if url else title_str
                st.markdown(f"""
                <div class='post-card' style='border-left-color:#f59e0b'>
                    <div class='ptitle'>🔥 {title_html}</div>
                    <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                        <span style='color:#f59e0b;font-weight:700'>
                        🔁 {int(row['num_crossposts'])} crossposts</span>
                        &nbsp;|&nbsp; ⭐ {int(row['score']):,}
                        {f'&nbsp;|&nbsp;<a href="{url}" target="_blank" style="font-size:.75rem;color:#718096;">source ↗</a>' if url else ''}
                    </div>
                </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB 4: Raw Data
# ═══════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>📋 Raw Data Table</div>", unsafe_allow_html=True)
    base_cols = ["subreddit","title","score","num_comments","upvote_ratio",
                 "region","region_group","fetch_type","fetch_date","author"]
    cols_show = [c for c in base_cols if c in filtered.columns]
    df_show   = filtered[cols_show].sort_values("score", ascending=False).copy()
    col_cfg = {}
    if "reddit_url" in filtered.columns:
        df_show["link"] = filtered["reddit_url"]
        col_cfg["link"] = st.column_config.LinkColumn("🔗 Link", display_text="↗ Open")
    st.dataframe(df_show, use_container_width=True, height=500, column_config=col_cfg)
    csv = filtered[cols_show].to_csv(index=False, encoding="utf-8-sig")
    st.download_button("⬇️ Download CSV", data=csv,
                       file_name=f"reddit_beauty_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                       mime="text/csv")
    if not meta_df.empty:
        st.markdown("<div class='section-header'>📌 Subreddit Metadata</div>", unsafe_allow_html=True)
        st.dataframe(meta_df, use_container_width=True, height=300)

# ═══════════════════════════════════════════
# TAB 6: Overview
# ═══════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-header'>🗄️ Database Summary</div>", unsafe_allow_html=True)
    db_size = "-"
    if os.path.exists(DB_PATH):
        b = os.path.getsize(DB_PATH)
        db_size = f"{b/1024:.1f} KB" if b < 1024*1024 else f"{b/1024/1024:.2f} MB"
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Total Posts",    f"{len(posts_df):,}")
    with m2: st.metric("Subreddits",     f"{posts_df['subreddit'].nunique()}")
    with m3:
        fd = posts_df["fetch_date"].min()
        st.metric("First Collected", fd.strftime("%Y-%m-%d") if pd.notna(fd) else "-")
    with m4:
        ld = posts_df["fetch_date"].max()
        st.metric("Last Collected",  ld.strftime("%Y-%m-%d") if pd.notna(ld) else "-")
    with m5: st.metric("DB File Size",   db_size)

    fc = posts_df["fetch_type"].value_counts()
    ma1, ma2, ma3 = st.columns(3)
    with ma1: st.metric("Weekly Posts",       f"{fc.get('weekly',0):,}")
    with ma2: st.metric("Monthly Posts",      f"{fc.get('monthly',0):,}")
    with ma3: st.metric("Uncategorized Region",f"{(posts_df['region_group']=='Uncategorized').sum():,}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>📋 Collection Status by Subreddit</div>",
                unsafe_allow_html=True)
    sub_stat = (posts_df.groupby("subreddit")
                .agg(posts=("id","count"), last_fetched=("fetch_date","max"),
                     avg_score=("score","mean"),
                     region_group=("region_group", lambda x: x.value_counts().index[0]))
                .reset_index().sort_values("posts", ascending=False))
    sub_stat["last_fetched"] = sub_stat["last_fetched"].dt.strftime("%Y-%m-%d")
    sub_stat["avg_score"]    = sub_stat["avg_score"].round(1)
    st.dataframe(sub_stat, use_container_width=True, hide_index=True, height=400)

    st.markdown("<div class='section-header'>📈 Collection Trend (Monthly)</div>",
                unsafe_allow_html=True)
    posts_df["ym"] = posts_df["fetch_date"].dt.to_period("M").astype(str)
    monthly = (posts_df.groupby(["ym","fetch_type"]).size()
               .reset_index(name="count").sort_values("ym"))
    if not monthly.empty:
        fig_tr = px.bar(monthly, x="ym", y="count", color="fetch_type", barmode="stack",
                        color_discrete_map={"weekly":"#185FA5","monthly":"#1D9E75"},
                        title="Monthly Collection Count (stacked by type)",
                        labels={"ym":"Month","count":"Posts","fetch_type":"Type"})
        fig_tr.update_layout(height=300, xaxis_tickangle=-30)
        st.plotly_chart(fig_tr, use_container_width=True)

    col_rg1, col_rg2 = st.columns(2)
    with col_rg1:
        st.markdown("<div class='section-header'>🌏 Region Group Distribution</div>",
                    unsafe_allow_html=True)
        rg_cnt = posts_df["region_group"].value_counts().reset_index()
        rg_cnt.columns = ["Region Group","Posts"]
        fig_rg = px.pie(rg_cnt, values="Posts", names="Region Group",
                        title="Post Share by Region Group", hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set2)
        fig_rg.update_layout(height=350)
        st.plotly_chart(fig_rg, use_container_width=True)
    with col_rg2:
        st.markdown("<div class='section-header'>📊 Region Group Details</div>",
                    unsafe_allow_html=True)
        rg_det = (posts_df.groupby("region_group")
                  .agg(posts=("id","count"), subreddits=("subreddit","nunique"),
                       avg_score=("score","mean"))
                  .reset_index().sort_values("posts", ascending=False))
        rg_det["avg_score"] = rg_det["avg_score"].round(1)
        st.dataframe(rg_det, use_container_width=True, hide_index=True, height=320)

    # ── Subreddit Activity (from Tab1) ─────────────────────────
    st.markdown("<div class='section-header'>📌 Subreddit Activity</div>", unsafe_allow_html=True)
    ov_col_a, ov_col_b = st.columns(2)
    with ov_col_a:
        ov_sub_cnt = (filtered.groupby("subreddit")["score"]
                     .agg(post_count="count", avg_score="mean")
                     .reset_index().sort_values("post_count", ascending=False).head(20))
        fig_ov1 = px.bar(ov_sub_cnt, x="post_count", y="subreddit", orientation="h",
                         color="avg_score", color_continuous_scale="RdYlGn",
                         title="Posts per Subreddit (color = Avg Score)",
                         labels={"subreddit":"Subreddit","post_count":"Post Count","avg_score":"Avg Score"})
        fig_ov1.update_layout(height=500, yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig_ov1, use_container_width=True)
    with ov_col_b:
        ov_sub_sc = (filtered.groupby("subreddit")["score"].sum().reset_index()
                     .rename(columns={"score":"total_score"})
                     .sort_values("total_score", ascending=False).head(15))
        fig_ov2 = px.pie(ov_sub_sc, values="total_score", names="subreddit",
                         title="Score Share by Subreddit (Top 15)",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_ov2.update_layout(height=500)
        st.plotly_chart(fig_ov2, use_container_width=True)

    # ── Upvote Ratio Distribution (from Tab1) ──────────────────
    st.markdown("<div class='section-header'>👍 Upvote Ratio Distribution</div>", unsafe_allow_html=True)
    if not filtered["upvote_ratio"].dropna().empty:
        fig_ov3 = px.histogram(filtered, x="upvote_ratio", nbins=20,
                               color="region_group", barmode="overlay",
                               title="Upvote Ratio Distribution (by Region Group)",
                               labels={"upvote_ratio":"Upvote Ratio","region_group":"Region Group"})
        fig_ov3.update_layout(height=350)
        st.plotly_chart(fig_ov3, use_container_width=True)

    # ── Post Distribution by Region (from Tab3) ────────────────
    st.markdown("<div class='section-header'>🌏 Post Distribution by Region</div>",
                unsafe_allow_html=True)
    ov_region4_agg = (filtered.groupby("region_display")
                      .agg(post_count=("id","count"), avg_score=("score","mean"),
                           total_score=("score","sum"), avg_comments=("num_comments","mean"))
                      .reset_index())
    region4_order = ["Global","Asia","N.America","Europe"]
    ov_region4_agg = ov_region4_agg.copy()
    ov_region4_agg["region_display"] = pd.Categorical(
        ov_region4_agg["region_display"], categories=region4_order, ordered=True)
    ov_region4_agg = ov_region4_agg.sort_values("region_display")

    ov_col_r4a, ov_col_r4b = st.columns(2)
    with ov_col_r4a:
        fig_ov_r4bar = px.bar(ov_region4_agg, x="region_display", y="post_count",
                              color="avg_score", color_continuous_scale="Blues",
                              title="Post Count & Avg Score by Region",
                              labels={"region_display":"Region","post_count":"Post Count","avg_score":"Avg Score"},
                              text="post_count")
        fig_ov_r4bar.update_traces(textposition="outside")
        fig_ov_r4bar.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_ov_r4bar, use_container_width=True)
    with ov_col_r4b:
        ov_color_map4 = {"Global":"#185FA5","Asia":"#1D9E75","N.America":"#D85A30","Europe":"#9B59B6"}
        fig_ov_r4bub = px.scatter(ov_region4_agg, x="avg_score", y="avg_comments",
                                  size="total_score", color="region_display",
                                  color_discrete_map=ov_color_map4,
                                  hover_name="region_display",
                                  title="Engagement by Region (Score vs Comments)",
                                  labels={"avg_score":"Avg Score","avg_comments":"Avg Comments",
                                          "region_display":"Region","total_score":"Total Score"})
        fig_ov_r4bub.update_layout(height=350)
        st.plotly_chart(fig_ov_r4bub, use_container_width=True)

    # ── Asia vs N.America Top 5 (from Tab3) ────────────────────
    st.markdown("<div class='section-header'>🔍 Asia vs N.America — Detailed Comparison (Top 5 Subreddits)</div>",
                unsafe_allow_html=True)
    ov_asia4_df = filtered[filtered["region_display"] == "Asia"]
    ov_na4_df   = filtered[filtered["region_display"] == "N.America"]
    ov_col_r4c, ov_col_r4d = st.columns(2)

    def top5_bar(df, title, color):
        if df.empty:
            st.info(f"No data: {title}")
            return
        ts = df.groupby("subreddit")["score"].sum().nlargest(5).reset_index()
        fig = px.bar(ts, x="score", y="subreddit", orientation="h",
                     title=title, color_discrete_sequence=[color],
                     labels={"score":"Total Score","subreddit":""})
        fig.update_layout(height=280, yaxis={"categoryorder":"total ascending"}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with ov_col_r4c:
        top5_bar(ov_asia4_df, "Asia — Top 5 Subreddits",      "#1D9E75")
    with ov_col_r4d:
        top5_bar(ov_na4_df,   "N.America — Top 5 Subreddits", "#D85A30")

    # ── Region Group Volume & Engagement (from Tab3) ────────────
    st.markdown("<div class='section-header'>🌏 Region Group Post Volume & Engagement</div>",
                unsafe_allow_html=True)
    ov_region_agg = (filtered.groupby("region_group")
                     .agg(post_count=("id","count"), avg_score=("score","mean"),
                          total_score=("score","sum"), avg_comments=("num_comments","mean"))
                     .reset_index())
    ov_col_ra, ov_col_rb = st.columns(2)
    with ov_col_ra:
        fig_ov_r1 = px.bar(ov_region_agg.sort_values("post_count", ascending=False),
                           x="region_group", y="post_count",
                           color="avg_score", color_continuous_scale="Viridis",
                           title="Post Count & Avg Score by Region Group",
                           labels={"region_group":"Region Group","post_count":"Post Count","avg_score":"Avg Score"})
        fig_ov_r1.update_layout(height=350, xaxis_tickangle=-15)
        st.plotly_chart(fig_ov_r1, use_container_width=True)
    with ov_col_rb:
        fig_ov_r2 = px.scatter(ov_region_agg, x="avg_score", y="avg_comments",
                               size="total_score", color="region_group",
                               hover_name="region_group",
                               title="Engagement by Region Group (Score vs Comments)",
                               labels={"avg_score":"Avg Score","avg_comments":"Avg Comments",
                                       "region_group":"Region Group"})
        fig_ov_r2.update_layout(height=350)
        st.plotly_chart(fig_ov_r2, use_container_width=True)

    # ── Asia vs North America Top 10 (from Tab3) ───────────────
    st.markdown("<div class='section-header'>🔍 Asia vs North America — Detailed Comparison (Top 10)</div>",
                unsafe_allow_html=True)
    ov_asia_df = filtered[filtered["region_group"] == "Asia-Pacific"]
    ov_na_df   = filtered[filtered["region_group"] == "Western Markets (NA/EU)"]
    ov_col_rc, ov_col_rd = st.columns(2)

    def top_subs_chart(df, title):
        if df.empty:
            st.info(f"No data for this region group: {title}")
            return
        ts = df.groupby("subreddit")["score"].sum().nlargest(10).reset_index()
        fig = px.bar(ts, x="score", y="subreddit", orientation="h",
                     title=title, color="score", color_continuous_scale="Reds",
                     labels={"score":"Total Score","subreddit":"Subreddit"})
        fig.update_layout(height=350, yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    with ov_col_rc: top_subs_chart(ov_asia_df, "🌏 Asia-Pacific — Top 10 Subreddits")
    with ov_col_rd: top_subs_chart(ov_na_df,   "🇺🇸 Western Markets — Top 10 Subreddits")

    # ── Region × Subreddit Heatmap (from Tab3) ─────────────────
    st.markdown("<div class='section-header'>🗺️ Region × Subreddit Activity Heatmap</div>",
                unsafe_allow_html=True)
    try:
        ov_pivot = filtered.pivot_table(index="region_group", columns="subreddit",
                                        values="score", aggfunc="sum", fill_value=0)
        ov_top_cols = ov_pivot.sum().nlargest(20).index
        ov_pivot    = ov_pivot[ov_top_cols]
        fig_ov_heat = px.imshow(ov_pivot, color_continuous_scale="YlOrRd",
                                title="Region × Subreddit Score Heatmap (Top 20 subreddits)",
                                labels={"color":"Total Score"}, aspect="auto")
        fig_ov_heat.update_layout(height=400)
        st.plotly_chart(fig_ov_heat, use_container_width=True)
    except Exception as e:
        st.warning(f"Heatmap error: {e}")

# ─────────────────────────────────────────
st.markdown("---")
st.caption(
    f"🌿 Reddit Beauty Market Intelligence Dashboard v6.0 | "
    f"DB: {DB_PATH} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)
