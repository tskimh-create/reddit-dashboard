# ═══════════════════════════════════════════════════════════════════
# data_loader.py — DB loading, enrichment, sidebar, KPI cards
# Reddit Beauty Market Intelligence Dashboard v7.0
# ═══════════════════════════════════════════════════════════════════

import sqlite3
import os

import gdown
import numpy as np
import pandas as pd
import streamlit as st

from config import (
    DB_PATH, GDRIVE_FILE_ID,
    REGION_GROUP_MAP, REGION_CARDS, REGION_ING_DICT,
)

# ╔══════════════════════════════════════╗
# ║  SECTION: ensure_db  [LOCKED v7]    ║
# ╚══════════════════════════════════════╝
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
# ══ END SECTION: ensure_db ══════════════════════════════════════════

# ╔══════════════════════════════════════╗
# ║  SECTION: load_all_data  [LOCKED v7]║
# ╚══════════════════════════════════════╝
@st.cache_data(ttl=300)
def load_all_data():
    """Load posts, keyword_hits, and subreddits_meta from SQLite DB."""
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

        # ── Remove user profile pages (r/u_ prefix) ──
        posts = posts[
            ~posts["subreddit"].str.contains(r"^r/u_", na=False, regex=True)
        ].copy()

        # ── Parse dates ──
        posts["fetch_date"] = pd.to_datetime(posts["fetch_date"], errors="coerce")
        posts["created_dt"] = pd.to_datetime(posts["created_utc"], unit="s", errors="coerce")

        # ── Enrich: region_group, reddit_url ──
        posts["region_group"] = posts["region"].apply(get_region_group)
        posts["reddit_url"]   = posts.apply(make_reddit_url, axis=1)

        return posts, keywords, meta

    except Exception as e:
        st.error(f"❌ DB connection error: {e}")
        st.info(f"Make sure `{DB_PATH}` is in the same folder as dashboard.py.")
        st.stop()
# ══ END SECTION: load_all_data ══════════════════════════════════════

# ╔══════════════════════════════════════════╗
# ║  SECTION: helper_functions  [LOCKED v7] ║
# ╚══════════════════════════════════════════╝
def get_region_group(val):
    """Map raw region string → one of the 6 REGION_GROUP_MAP keys."""
    if pd.isna(val) or str(val).strip() == "":
        return "Uncategorized"
    v = str(val).lower()
    for grp, kws in REGION_GROUP_MAP.items():
        if any(k.lower() in v for k in kws):
            return grp
    return "Uncategorized"


def make_reddit_url(row):
    """Build a full Reddit URL from permalink or reddit_id + subreddit fallback."""
    pl = str(row.get("permalink", "")).strip()
    if pl and pl not in ("", "nan", "None"):
        if pl.startswith("http"):          # legacy full URL
            return pl
        return f"https://www.reddit.com{pl}"   # relative path → prepend domain
    # Fallback: construct from reddit_id + subreddit
    rid = row.get("reddit_id", "")
    sub = str(row.get("subreddit", "")).strip()
    sub_clean = sub[2:] if sub.startswith("r/") else sub
    return (f"https://www.reddit.com/r/{sub_clean}/comments/{rid}/"
            if rid and sub_clean else "")


def get_display_region(region_val):
    """Simplified 4-bucket region label: Asia / Europe / N.America / Global."""
    if pd.isna(region_val) or str(region_val).strip() == "":
        return "Global"
    v = str(region_val).lower()
    if any(k in v for k in ["korea", "japan", "china", "asia", "india",
                             "singapore", "동남아", "아시아", "pacific"]):
        return "Asia"
    if any(k in v for k in ["europe", "uk", "germany", "france",
                             "유럽", "영국", "네덜", "스웨", "이탈"]):
        return "Europe"
    if any(k in v for k in ["north", "usa", "canada", "america",
                             "북미", "호주", "australia", "newzeal", "뉴질"]):
        return "N.America"
    return "Global"


def calc_region_ingredients(df):
    """Scan post titles/bodies for each REGION_ING_DICT entry → counts per region_group."""
    records = []
    for ing, terms in REGION_ING_DICT.items():
        pat  = "|".join(terms)
        mask = (df["title"].str.contains(pat, case=False, na=False) |
                df["selftext"].str.contains(pat, case=False, na=False))
        grp  = df[mask].groupby("region_group").size().reset_index(name="mentions")
        grp["ingredient"] = ing
        records.append(grp)
    return pd.concat(records, ignore_index=True) if records else pd.DataFrame()
# ══ END SECTION: helper_functions ═══════════════════════════════════

# ╔══════════════════════════════════════╗
# ║  SECTION: build_sidebar  [LOCKED v7]║
# ╚══════════════════════════════════════╝
def build_sidebar(posts_df):
    """
    Render all sidebar widgets and return the filtered DataFrame.
    Also attaches 'region_display' column to the result.
    """
    st.sidebar.markdown(
        "## 🌿 Reddit Beauty Insights\n**Cosmetics Market Intelligence**"
    )
    st.sidebar.markdown("---")

    # ── Collection Period ──
    st.sidebar.markdown("**📅 Collection Period**")
    period_mode = st.sidebar.radio(
        "", ["All (Cumulative)", "Select Period"],
        horizontal=True, label_visibility="collapsed",
    )
    if period_mode == "Select Period":
        avail_years = sorted(
            posts_df["fetch_date"].dt.year.dropna().unique().astype(int).tolist(),
            reverse=True,
        )
        sel_year  = st.sidebar.selectbox("Year", avail_years)
        avail_mon = ["All"] + [
            f"{m:02d}" for m in sorted(
                posts_df[posts_df["fetch_date"].dt.year == sel_year]["fetch_date"]
                .dt.month.dropna().unique().astype(int).tolist()
            )
        ]
        sel_month = st.sidebar.selectbox("Month", avail_mon)
    else:
        sel_year = sel_month = None

    # ── Region Group (card-style radio) ──
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🌏 Region Group**")

    _rg_cnt     = posts_df["region_group"].value_counts().to_dict()
    _rg_labels  = []
    _rg_key_map = {}
    for lbl, key, icon, desc in REGION_CARDS:
        n     = len(posts_df) if key == "All" else _rg_cnt.get(key, 0)
        # Line 1 (large bold via ::first-line CSS): icon + name
        # Line 2 (small muted): post count · description
        label = f"{icon} {lbl}\n{n:,} posts  ·  {desc}"
        _rg_labels.append(label)
        _rg_key_map[label] = key

    _sel_label = st.sidebar.radio(
        "region_group_radio",
        _rg_labels,
        label_visibility="collapsed",
        key="rg_radio",
    )
    sel_rgroup = _rg_key_map[_sel_label]

    # ── Subreddit & Score ──
    st.sidebar.markdown("---")
    sub_opts  = ["All"] + sorted(posts_df["subreddit"].dropna().unique().tolist())
    sel_sub   = st.sidebar.selectbox("📌 Subreddit", sub_opts)
    min_score = st.sidebar.slider(
        "⭐ Min Score", 0, int(posts_df["score"].max() or 1000), 0, 10
    )

    # ── Footer stats ──
    st.sidebar.markdown("---")
    st.sidebar.caption(f"🗄️ DB: `{DB_PATH}`")
    st.sidebar.caption(
        f"🕐 Last collected: "
        f"{posts_df['fetch_date'].max().strftime('%Y-%m-%d') if not posts_df.empty else '-'}"
    )
    st.sidebar.caption(
        f"📦 {len(posts_df):,} posts · {posts_df['subreddit'].nunique()} subreddits"
    )

    # ── Apply filters ──
    filtered = posts_df.copy()
    if period_mode == "Select Period" and sel_year:
        filtered = filtered[filtered["fetch_date"].dt.year == sel_year]
        if sel_month != "All":
            filtered = filtered[filtered["fetch_date"].dt.month == int(sel_month)]
    if sel_rgroup != "All":
        filtered = filtered[filtered["region_group"] == sel_rgroup]
    if sel_sub != "All":
        filtered = filtered[filtered["subreddit"] == sel_sub]
    filtered = filtered[filtered["score"] >= min_score].copy()

    # Attach simplified region display label
    filtered["region_display"] = filtered["region"].apply(get_display_region)
    return filtered
# ══ END SECTION: build_sidebar ══════════════════════════════════════

# ╔══════════════════════════════════════╗
# ║  SECTION: render_kpi_cards [LOCK v7]║
# ╚══════════════════════════════════════╝
def render_kpi_cards(filtered, keywords_df):
    """Render the 5 top-of-page KPI metric cards."""
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_data = [
        (f"{len(filtered):,}",
         "Total Posts (filtered)"),
        (f"{int(filtered['score'].mean()) if not filtered.empty else 0:,}",
         "Avg Score"),
        (f"{int(filtered['num_comments'].sum()) if not filtered.empty else 0:,}",
         "Total Comments"),
        (f"{len(keywords_df):,}",
         "Keyword Hits"),
        (f"{filtered['subreddit'].nunique()}",
         "Active Subreddits"),
    ]
    for col, (val, lbl) in zip([c1, c2, c3, c4, c5], kpi_data):
        with col:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='val'>{val}</div>"
                f"<div class='lbl'>{lbl}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<br>", unsafe_allow_html=True)
# ══ END SECTION: render_kpi_cards ═══════════════════════════════════
