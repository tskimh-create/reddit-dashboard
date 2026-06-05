# ═══════════════════════════════════════════════════════════════════
# tab_overview.py — Tab 0: Overview & Data Hub
# Reddit Beauty Market Intelligence Dashboard v7.0
# Phase 3 — full implementation
# ═══════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from config import DB_PATH


# ╔══════════════════════════════════════════════════╗
# ║  SECTION: render_tab_overview  [Phase 3 v7]     ║
# ╚══════════════════════════════════════════════════╝
def render_tab_overview(filtered, posts_df, keywords_df, meta_df):
    """
    Tab 0 — Overview & Data Hub
    Sections:
      A. DB Summary (KPI metrics)
      B. 30-Subreddit Profile Table
      C. Subreddit Correlation Heatmap (ingredient co-mention)
      D. Collection Trend (monthly)
      E. Region Group Distribution
      F. Raw Data Table + CSV Download
    """

    # ── A. DB Summary ────────────────────────────────────────────
    st.markdown(
        "<div class='section-header'>🗄️ Database Summary</div>",
        unsafe_allow_html=True,
    )

    def _stat_card(value, label, color, icon=""):
        return (
            f"<div style='"
            f"background:linear-gradient(135deg,{color},color-mix(in srgb,{color} 70%,#000));"
            f"border-radius:12px;padding:18px 16px;text-align:center;color:white;"
            f"box-shadow:0 4px 12px {color}55;margin:2px;'>"
            f"<div style='font-size:1.7rem;font-weight:700;line-height:1.1;'>"
            f"{icon}{value}</div>"
            f"<div style='font-size:0.78rem;opacity:0.9;margin-top:6px;'>{label}</div>"
            f"</div>"
        )

    db_size = "-"
    if os.path.exists(DB_PATH):
        b = os.path.getsize(DB_PATH)
        db_size = f"{b/1024:.1f} KB" if b < 1024 * 1024 else f"{b/1024/1024:.2f} MB"

    fd = posts_df["fetch_date"].min()
    ld = posts_df["fetch_date"].max()
    fc = posts_df["fetch_type"].value_counts()

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.markdown(_stat_card(f"{len(posts_df):,}",         "Total Posts",      "#185FA5", "📦 "), unsafe_allow_html=True)
    with m2: st.markdown(_stat_card(f"{posts_df['subreddit'].nunique()}", "Subreddits", "#1D9E75", "📌 "), unsafe_allow_html=True)
    with m3: st.markdown(_stat_card(fd.strftime("%Y-%m-%d") if pd.notna(fd) else "-", "First Collected", "#533483", "📅 "), unsafe_allow_html=True)
    with m4: st.markdown(_stat_card(ld.strftime("%Y-%m-%d") if pd.notna(ld) else "-", "Last Collected",  "#0f3460", "🕐 "), unsafe_allow_html=True)
    with m5: st.markdown(_stat_card(db_size,                       "DB File Size",     "#6B7280", "🗄️ "), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    ma1, ma2, ma3, ma4 = st.columns(4)
    with ma1: st.markdown(_stat_card(f"{fc.get('weekly', 0):,}",  "Weekly Posts",     "#2563EB", "📊 "), unsafe_allow_html=True)
    with ma2: st.markdown(_stat_card(f"{fc.get('monthly', 0):,}", "Monthly Posts",    "#059669", "📈 "), unsafe_allow_html=True)
    with ma3: st.markdown(_stat_card(f"{len(keywords_df):,}",     "Keyword Hits",     "#e94560", "🔑 "), unsafe_allow_html=True)
    with ma4: st.markdown(_stat_card(f"{(posts_df['region_group'] == 'Uncategorized').sum():,}", "Uncategorized Region", "#D97706", "📂 "), unsafe_allow_html=True)

    # ── B. 30-Subreddit Profile Table ────────────────────────────
    st.markdown(
        "<div class='section-header'>📋 Subreddit Profiles — All 30 Communities</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Each row = one subreddit. "
        "Top Flair = most common post flair tag. "
        "Engagement = avg comments per post."
    )

    sub_profile = (
        posts_df.groupby("subreddit")
        .agg(
            posts          = ("id",             "count"),
            avg_score      = ("score",          "mean"),
            avg_comments   = ("num_comments",   "mean"),
            avg_upvote     = ("upvote_ratio",   "mean"),
            total_score    = ("score",          "sum"),
            last_fetched   = ("fetch_date",     "max"),
            region_group   = ("region_group",   lambda x:
                              x.value_counts().index[0] if len(x.value_counts()) > 0 else ""),
        )
        .reset_index()
        .sort_values("posts", ascending=False)
    )

    # Top flair per subreddit (from link_flair_text if available)
    if "link_flair_text" in posts_df.columns:
        flair_top = (
            posts_df[posts_df["link_flair_text"].notna() & (posts_df["link_flair_text"] != "")]
            .groupby("subreddit")["link_flair_text"]
            .agg(lambda x: x.value_counts().index[0] if len(x) > 0 else "")
            .reset_index()
            .rename(columns={"link_flair_text": "top_flair"})
        )
        sub_profile = sub_profile.merge(flair_top, on="subreddit", how="left")
        sub_profile["top_flair"] = sub_profile["top_flair"].fillna("—")
    else:
        sub_profile["top_flair"] = "—"

    sub_profile["avg_score"]    = sub_profile["avg_score"].round(1)
    sub_profile["avg_comments"] = sub_profile["avg_comments"].round(1)
    sub_profile["avg_upvote"]   = (sub_profile["avg_upvote"] * 100).round(1).astype(str) + "%"
    sub_profile["last_fetched"] = sub_profile["last_fetched"].dt.strftime("%Y-%m-%d")

    st.dataframe(
        sub_profile[[
            "subreddit", "posts", "avg_score", "avg_comments",
            "avg_upvote", "top_flair", "region_group", "last_fetched",
        ]],
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "subreddit":    st.column_config.TextColumn("Subreddit"),
            "posts":        st.column_config.NumberColumn("Posts",       format="%d"),
            "avg_score":    st.column_config.NumberColumn("Avg Score",   format="%.1f"),
            "avg_comments": st.column_config.NumberColumn("Avg Comments",format="%.1f"),
            "avg_upvote":   st.column_config.TextColumn("Upvote Rate"),
            "top_flair":    st.column_config.TextColumn("Top Flair"),
            "region_group": st.column_config.TextColumn("Region Group"),
            "last_fetched": st.column_config.TextColumn("Last Fetched"),
        },
    )

    # ── C. Subreddit Correlation Heatmap ─────────────────────────
    st.markdown(
        "<div class='section-header'>"
        "🔗 Subreddit Similarity — Shared Ingredient Mentions"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Cell value = number of ingredient keywords mentioned in BOTH subreddits. "
        "Higher = more topically similar communities."
    )

    if keywords_df.empty:
        st.info("⚠️ No keyword_hits data. Run `keyword_matcher.py` to enable this chart.")
    else:
        # Build subreddit × keyword pivot
        kw_pivot_raw = (
            keywords_df.groupby(["subreddit", "keyword"])
            .size()
            .reset_index(name="cnt")
        )
        top_subs = (
            posts_df.groupby("subreddit")["id"]
            .count()
            .nlargest(20)
            .index.tolist()
        )
        kw_pivot_raw = kw_pivot_raw[kw_pivot_raw["subreddit"].isin(top_subs)]
        kw_matrix = kw_pivot_raw.pivot_table(
            index="subreddit", columns="keyword", values="cnt", fill_value=0
        )
        if kw_matrix.shape[0] > 1:
            import numpy as np
            mat = kw_matrix.values.astype(float)
            # Cosine similarity
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            norms[norms == 0] = 1
            sim   = mat / norms
            sim   = sim @ sim.T
            sim_df = pd.DataFrame(sim, index=kw_matrix.index, columns=kw_matrix.index)
            fig_corr = px.imshow(
                sim_df,
                color_continuous_scale="Blues",
                title="Subreddit Ingredient Similarity (cosine, Top 20 subreddits)",
                labels={"color": "Similarity"},
                aspect="auto",
                zmin=0, zmax=1,
            )
            fig_corr.update_layout(height=500)
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Not enough subreddits with keyword data for correlation.")

    # ── D. Collection Trend ──────────────────────────────────────
    st.markdown(
        "<div class='section-header'>📈 Collection Trend (Monthly)</div>",
        unsafe_allow_html=True,
    )
    _ov = posts_df.copy()
    _ov["ym"] = _ov["fetch_date"].dt.to_period("M").astype(str)
    monthly = (
        _ov.groupby(["ym", "fetch_type"])
        .size()
        .reset_index(name="count")
        .sort_values("ym")
    )
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if not monthly.empty:
            fig_trend = px.bar(
                monthly, x="ym", y="count", color="fetch_type", barmode="stack",
                color_discrete_map={"weekly": "#185FA5", "monthly": "#1D9E75"},
                title="Monthly Collection Count (stacked by fetch type)",
                labels={"ym": "Month", "count": "Posts", "fetch_type": "Fetch Type"},
            )
            fig_trend.update_layout(height=320, xaxis_tickangle=-30)
            st.plotly_chart(fig_trend, use_container_width=True)
    with col_d2:
        # Posts per subreddit activity bar
        sub_act = (
            posts_df.groupby("subreddit")["score"]
            .agg(post_count="count", avg_score="mean")
            .reset_index()
            .sort_values("post_count", ascending=False)
            .head(20)
        )
        fig_act = px.bar(
            sub_act, x="post_count", y="subreddit", orientation="h",
            color="avg_score", color_continuous_scale="RdYlGn",
            title="Posts per Subreddit (color = Avg Score, Top 20)",
            labels={"subreddit": "", "post_count": "Post Count", "avg_score": "Avg Score"},
        )
        fig_act.update_layout(height=320, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_act, use_container_width=True)

    # ── E. Region Group Distribution ─────────────────────────────
    st.markdown(
        "<div class='section-header'>🌏 Region Group Distribution</div>",
        unsafe_allow_html=True,
    )
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        rg_cnt = posts_df["region_group"].value_counts().reset_index()
        rg_cnt.columns = ["Region Group", "Posts"]
        fig_rg = px.pie(
            rg_cnt, values="Posts", names="Region Group",
            title="Post Share by Region Group", hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_rg.update_layout(height=350)
        st.plotly_chart(fig_rg, use_container_width=True)
    with col_e2:
        rg_det = (
            posts_df.groupby("region_group")
            .agg(posts=("id", "count"), subreddits=("subreddit", "nunique"),
                 avg_score=("score", "mean"))
            .reset_index()
            .sort_values("posts", ascending=False)
        )
        rg_det["avg_score"] = rg_det["avg_score"].round(1)
        st.dataframe(rg_det, use_container_width=True, hide_index=True, height=320)

    # ── F. Raw Data Table + CSV Download ─────────────────────────
    st.markdown(
        "<div class='section-header'>📋 Raw Data — Filtered Posts</div>",
        unsafe_allow_html=True,
    )
    base_cols = [
        "subreddit", "title", "score", "num_comments", "upvote_ratio",
        "link_flair_text", "region_group", "fetch_type", "fetch_date", "author",
    ]
    cols_show = [c for c in base_cols if c in filtered.columns]
    df_show   = filtered[cols_show].sort_values("score", ascending=False).copy()
    col_cfg   = {}
    if "reddit_url" in filtered.columns:
        df_show["link"] = filtered["reddit_url"]
        col_cfg["link"] = st.column_config.LinkColumn("🔗 Link")

    st.dataframe(
        df_show, use_container_width=True, height=500,
        hide_index=True, column_config=col_cfg,
    )

    csv = filtered[cols_show].to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ Download filtered data as CSV",
        data=csv,
        file_name=f"reddit_beauty_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

# ══ END SECTION: render_tab_overview ════════════════════════════════
