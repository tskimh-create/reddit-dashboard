# ═══════════════════════════════════════════════════════════════════
# tab_analysis.py — Tab 1 / 2 / 3: Trend · Ingredients · VOC
# Reddit Beauty Market Intelligence Dashboard v7.0
# Phases 4 / 5 / 6
# ═══════════════════════════════════════════════════════════════════

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    COMPLAINT_DICT, IMPROVEMENT_DICT,
    PAIN_DICT, POSITIVE_DICT, REGION_GROUP_MAP, REGION_ING_DICT,
    KEYWORD_CATEGORY_MAP, KEYWORD_NAME_MAP,
)
from data_loader import calc_region_ingredients, get_region_group


def _normalize_keywords(keywords_df):
    """
    Map Korean keyword names and categories to English.
    Strips whitespace first to handle DB values with leading/trailing spaces.
    Uses a fallback loop for any remaining unmapped Korean-only strings.
    """
    if keywords_df.empty:
        return keywords_df
    kw = keywords_df.copy()

    # Strip + exact replace
    kw["keyword"]          = kw["keyword"].str.strip().replace(KEYWORD_NAME_MAP)
    kw["keyword_category"] = kw["keyword_category"].str.strip().replace(KEYWORD_CATEGORY_MAP)

    # Fallback: any remaining value that is ALL non-ASCII (pure Korean) → keep as-is
    # but attempt a normalised match (lower, no spaces) against the map keys
    _cat_map_norm = {k.replace(" ", "").lower(): v for k, v in KEYWORD_CATEGORY_MAP.items()}
    _kw_map_norm  = {k.replace(" ", "").lower(): v for k, v in KEYWORD_NAME_MAP.items()}

    def _safe_map(val, norm_map):
        norm_key = str(val).replace(" ", "").lower()
        return norm_map.get(norm_key, val)

    kw["keyword"]          = kw["keyword"].apply(lambda v: _safe_map(v, _kw_map_norm))
    kw["keyword_category"] = kw["keyword_category"].apply(lambda v: _safe_map(v, _cat_map_norm))
    return kw


# ───────────────────────────────────────────────────────────────────
#  SHARED HELPER — post card HTML
# ───────────────────────────────────────────────────────────────────
def _post_card(row, index=None, border_color="#e94560"):
    url       = row.get("reddit_url", "")
    title_str = str(row["title"])
    trunc     = title_str[:100] + ("…" if len(title_str) > 100 else "")
    link_html = (
        f'<a href="{url}" target="_blank" style="color:#1a1a2e;text-decoration:none;">'
        f"{trunc}</a>"
        if url else trunc
    )
    idx_badge = f"#{index + 1} &nbsp; " if index is not None else "📌 "
    ratio_pct = (
        f"{row['upvote_ratio']*100:.0f}%"
        if pd.notna(row.get("upvote_ratio")) else "-"
    )
    src_link = (
        f'&nbsp;|&nbsp;<a href="{url}" target="_blank" '
        f'style="font-size:.75rem;color:#718096;">source ↗</a>'
        if url else ""
    )
    sub_clean = str(row.get("subreddit", "")).removeprefix("r/")
    return (
        f"<div class='post-card' style='border-left-color:{border_color};'>"
        f"<div class='ptitle'>{idx_badge}{link_html}</div>"
        f"<div class='pmeta'>"
        f"r/{sub_clean} &nbsp;|&nbsp; "
        f"<span class='pscore'>⭐ {int(row['score']):,}</span> &nbsp;|&nbsp; "
        f"💬 {int(row['num_comments']):,} &nbsp;|&nbsp; 👍 {ratio_pct}"
        f"{src_link}"
        f"</div></div>"
    )


# ═══════════════════════════════════════════════════════════════════
#  TAB 1 — Trend Detection
# ═══════════════════════════════════════════════════════════════════

# ╔══════════════════════════════════════════════════════╗
# ║  SECTION: render_tab_trend  [Phase 4 v7]            ║
# ╚══════════════════════════════════════════════════════╝
def render_tab_trend(filtered, posts_df):
    """
    Tab 1 — Trend Detection
    Sections:
      1. Trending Posts Top 10 (by score)
      2. Post Flair Intent Distribution (link_flair_text — NEW)
      3. Actual Post Date Trend (created_dt — NEW, replaces fetch_date trend)
      4. Monthly Trend by Region Group
    """

    # ── 1. Trending Posts Top 10 ─────────────────────────────────
    st.markdown(
        "<div class='section-header'>📊 Trending Posts — Top 10</div>",
        unsafe_allow_html=True,
    )
    top10 = (
        filtered.nlargest(10, "score")[
            ["subreddit", "title", "score", "num_comments",
             "upvote_ratio", "region_group", "reddit_url"]
        ].reset_index(drop=True)
    )
    for i, row in top10.iterrows():
        st.markdown(_post_card(row, index=i), unsafe_allow_html=True)

    # ── 2. Post Flair Intent Distribution ────────────────────────
    st.markdown(
        "<div class='section-header'>"
        "🏷️ Post Flair — Community Intent Distribution"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Flair tags assigned by users / mods when posting. "
        "Shows what type of content dominates each subreddit."
    )

    if "link_flair_text" not in filtered.columns:
        st.info("link_flair_text column not found in DB.")
    else:
        flair_data = filtered[
            filtered["link_flair_text"].notna() &
            (filtered["link_flair_text"].str.strip() != "")
        ].copy()

        if flair_data.empty:
            st.info("No flair data in current filter — try selecting 'All' filters.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                flair_cnt = (
                    flair_data["link_flair_text"]
                    .value_counts()
                    .head(20)
                    .reset_index()
                )
                flair_cnt.columns = ["Flair", "Posts"]
                fig_flair = px.bar(
                    flair_cnt, x="Posts", y="Flair", orientation="h",
                    color="Posts", color_continuous_scale="Purples",
                    title="Top 20 Flair Tags by Post Count",
                    labels={"Flair": "", "Posts": "Post Count"},
                )
                fig_flair.update_layout(
                    height=480, yaxis={"categoryorder": "total ascending"}
                )
                st.plotly_chart(fig_flair, use_container_width=True)
            with col_f2:
                # Flair × avg score — which intent drives most engagement
                flair_eng = (
                    flair_data.groupby("link_flair_text")["score"]
                    .agg(posts="count", avg_score="mean", total_score="sum")
                    .reset_index()
                    .rename(columns={"link_flair_text": "Flair"})
                    .query("posts >= 3")
                    .sort_values("avg_score", ascending=False)
                    .head(20)
                )
                fig_flair2 = px.scatter(
                    flair_eng, x="posts", y="avg_score",
                    size="total_score", hover_name="Flair",
                    color="avg_score", color_continuous_scale="RdYlGn",
                    title="Flair Intent: Post Count vs Avg Score",
                    labels={"posts": "Post Count", "avg_score": "Avg Score"},
                )
                fig_flair2.update_layout(height=480)
                st.plotly_chart(fig_flair2, use_container_width=True)

            # Top flair per subreddit table
            with st.expander("📋 Top Flair per Subreddit", expanded=False):
                top_flair_sub = (
                    flair_data.groupby(["subreddit", "link_flair_text"])
                    .size()
                    .reset_index(name="count")
                    .sort_values(["subreddit", "count"], ascending=[True, False])
                    .groupby("subreddit")
                    .head(3)
                    .rename(columns={"link_flair_text": "Top Flair", "count": "Posts"})
                )
                st.dataframe(
                    top_flair_sub, use_container_width=True,
                    hide_index=True, height=400,
                )

    # ── 3. Actual Post Date Trend (created_dt) ───────────────────
    st.markdown(
        "<div class='section-header'>"
        "📅 Actual Post Date Trend (created_utc — when posts were published)"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "This uses the original Reddit post creation timestamp, not the fetch date. "
        "Shows when topics actually peaked on Reddit."
    )

    if "created_dt" in filtered.columns and filtered["created_dt"].notna().sum() > 0:
        _trend = filtered.copy()
        _trend["pub_month"] = _trend["created_dt"].dt.to_period("M").astype(str)
        pub_trend = (
            _trend.groupby(["pub_month", "region_group"])
            .size()
            .reset_index(name="posts")
            .sort_values("pub_month")
        )
        pub_trend = pub_trend[pub_trend["pub_month"] >= "2024-01"]   # focus last 2 yrs
        if not pub_trend.empty:
            fig_pub = px.line(
                pub_trend, x="pub_month", y="posts", color="region_group",
                markers=True,
                title="Monthly Post Volume by Region Group (post creation date)",
                labels={"pub_month": "Month", "posts": "Post Count",
                        "region_group": "Region Group"},
            )
            fig_pub.update_layout(height=340, xaxis_tickangle=-20)
            st.plotly_chart(fig_pub, use_container_width=True)
        else:
            st.info("No post creation date data found after 2024-01.")
    else:
        st.info("created_utc not available in DB.")

    # ── 4. Monthly Trend by Region Group (fetch_date) ────────────
    st.markdown(
        "<div class='section-header'>"
        "📈 Monthly Collection Trend by Region Group (fetch date)"
        "</div>",
        unsafe_allow_html=True,
    )
    _tab = filtered.copy()
    _tab["ym"] = _tab["fetch_date"].dt.to_period("M").astype(str)
    monthly_rg = (
        _tab.groupby(["ym", "region_group"])
        .size()
        .reset_index(name="posts")
        .sort_values("ym")
    )
    if not monthly_rg.empty:
        fig_mt = px.line(
            monthly_rg, x="ym", y="posts", color="region_group",
            markers=True,
            title="Monthly Post Count — by Region Group (collected)",
            labels={"ym": "Month", "posts": "Post Count", "region_group": "Region Group"},
        )
        fig_mt.update_layout(height=320, xaxis_tickangle=-20)
        st.plotly_chart(fig_mt, use_container_width=True)
# ══ END SECTION: render_tab_trend ═══════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
#  TAB 2 — Ingredients & Positioning
# ═══════════════════════════════════════════════════════════════════

# ╔══════════════════════════════════════════════════════╗
# ║  SECTION: render_tab_ingredient  [Phase 5 v7]       ║
# ╚══════════════════════════════════════════════════════╝
def render_tab_ingredient(filtered, posts_df, keywords_df):
    """
    Tab 2 — Ingredients & Positioning
    Sections:
      1. Ingredient Rankings (keyword_hits — score-weighted)
      2. Ingredient Bubble Chart (mentions × avg score × comments)
      3. Category Treemap
      4. Ingredient Traffic Light Positioning
      5. Regional Ingredient Comparison
      6. Climate Formula Map (region × category heatmap)
    """

    # ── Apply Korean→English normalization (name + category) ─────
    keywords_df = _normalize_keywords(keywords_df)

    # ── 1 & 2 & 3. Ingredient Rankings (keyword_hits) ────────────
    st.markdown(
        "<div class='section-header'>🧪 Ingredient Rankings (score-weighted)</div>",
        unsafe_allow_html=True,
    )

    if keywords_df.empty:
        st.warning(
            "⚠️ No data in keyword_hits table. "
            "Run `keyword_matcher.py` to populate it."
        )
        st.markdown("""
        **How keyword matching works:**
        Run `keyword_matcher.py` in the same folder as `reddit_data.db`.
        It scans every post title and body for ingredient keywords and writes
        results to the `keyword_hits` table — this tab will activate automatically.
        """)
    else:
        kw_agg = (
            keywords_df.groupby("keyword")
            .agg(
                mentions      = ("keyword",      "count"),
                total_score   = ("score",        "sum"),
                avg_score     = ("score",        "mean"),
                total_comments= ("num_comments", "sum"),
            )
            .reset_index()
            .sort_values("total_score", ascending=False)
            .head(30)
        )
        col_a, col_b = st.columns(2)
        with col_a:
            fig_kw1 = px.bar(
                kw_agg.head(20), x="total_score", y="keyword",
                orientation="h", color="mentions",
                color_continuous_scale="Blues",
                title="Total Score by Ingredient (Top 20)",
                labels={"keyword": "Ingredient", "total_score": "Total Score",
                        "mentions": "Mentions"},
            )
            fig_kw1.update_layout(height=500, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_kw1, use_container_width=True)
        with col_b:
            fig_kw2 = px.scatter(
                kw_agg, x="mentions", y="avg_score",
                size="total_comments", hover_name="keyword",
                color="total_score", color_continuous_scale="RdYlGn",
                title="Ingredient Bubble: Mentions × Avg Score × Comments",
                labels={"mentions": "Mentions", "avg_score": "Avg Score"},
            )
            fig_kw2.update_layout(height=500)
            st.plotly_chart(fig_kw2, use_container_width=True)

        if "keyword_category" in keywords_df.columns:
            st.markdown(
                "<div class='section-header'>📂 Category Treemap</div>",
                unsafe_allow_html=True,
            )
            cat_agg = (
                keywords_df.groupby("keyword_category")
                .agg(mentions=("keyword", "count"), total_score=("score", "sum"))
                .reset_index()
                .sort_values("total_score", ascending=False)
            )
            fig_cat = px.treemap(
                cat_agg, path=["keyword_category"],
                values="total_score", color="mentions",
                color_continuous_scale="Teal",
                title="Category Treemap (size = Total Score, color = Mentions)",
            )
            fig_cat.update_layout(height=400)
            st.plotly_chart(fig_cat, use_container_width=True)

    # ── 4. Ingredient Traffic Light Positioning ───────────────────
    st.markdown(
        "<div class='section-header'>"
        "🚦 Ingredient Traffic Light — Consumer Acceptance Signal"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "**Green** = high upvote ratio → community-approved ingredient.  "
        "**Red** = divisive / negative reaction. "
        "Bubble size = total engagement score."
    )

    if keywords_df.empty:
        st.warning("keyword_hits data required. Run `keyword_matcher.py` first.")
    else:
        sig = (
            keywords_df.groupby("keyword")
            .agg(
                mentions   = ("keyword",      "count"),
                avg_score  = ("score",        "mean"),
                avg_upvote = ("upvote_ratio", "mean"),
                total_score= ("score",        "sum"),
            )
            .reset_index()
        )
        sig = sig[sig["mentions"] >= 2]

        def _signal(r):
            if r >= 0.88:  return "🟢 Green — Adopt Now"
            elif r >= 0.75: return "🟡 Yellow — Monitor"
            else:           return "🔴 Red — Hold"

        sig["Signal"] = sig["avg_upvote"].apply(_signal)
        col_s1, col_s2 = st.columns([3, 2])
        with col_s1:
            fig_sig = px.scatter(
                sig, x="avg_upvote", y="avg_score",
                size="total_score", color="Signal", hover_name="keyword",
                color_discrete_map={
                    "🟢 Green — Adopt Now": "#22c55e",
                    "🟡 Yellow — Monitor":  "#f59e0b",
                    "🔴 Red — Hold":        "#ef4444",
                },
                title="Ingredient Acceptance Traffic Light",
                labels={"avg_upvote": "Avg Upvote Ratio", "avg_score": "Avg Score"},
            )
            fig_sig.add_vline(x=0.88, line_dash="dash", line_color="green",
                              annotation_text="Green threshold")
            fig_sig.add_vline(x=0.75, line_dash="dash", line_color="orange",
                              annotation_text="Yellow threshold")
            fig_sig.update_layout(height=450)
            st.plotly_chart(fig_sig, use_container_width=True)
        with col_s2:
            for sl in ["🟢 Green — Adopt Now", "🟡 Yellow — Monitor", "🔴 Red — Hold"]:
                sub = sig[sig["Signal"] == sl].sort_values("total_score", ascending=False)
                st.markdown(f"**{sl}** — {len(sub)} ingredients")
                if not sub.empty:
                    st.caption(", ".join(sub.head(6)["keyword"].tolist()))
                st.markdown("---")

    # ── 5. Regional Ingredient Comparison ────────────────────────
    st.markdown(
        "<div class='section-header'>🧴 Regional Ingredient Comparison</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Detected by scanning post titles and body text. "
        "Compares ingredient interest across region groups."
    )

    ing_df = calc_region_ingredients(filtered)

    if ing_df.empty:
        st.info("No ingredient data in current filter. Try 'All' filters.")
    else:
        focus_groups = ["Global · General", "Asia-Pacific", "Western Markets (NA/EU)"]
        ing_focus    = ing_df[ing_df["region_group"].isin(focus_groups)]

        if not ing_focus.empty:
            fig_ing = px.bar(
                ing_focus, x="ingredient", y="mentions", color="region_group",
                barmode="group",
                color_discrete_map={
                    "Global · General":        "#185FA5",
                    "Asia-Pacific":            "#1D9E75",
                    "Western Markets (NA/EU)": "#D85A30",
                },
                title="Region Group × Ingredient Mention Comparison",
                labels={"ingredient": "Ingredient", "mentions": "Mentions",
                        "region_group": "Region Group"},
            )
            fig_ing.update_layout(height=380, xaxis_tickangle=-20)
            st.plotly_chart(fig_ing, use_container_width=True)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**🔬 Global vs Asia-Pacific — Ingredient Interest Gap**")
            gb_ing  = (ing_df[ing_df["region_group"] == "Global · General"]
                       .set_index("ingredient")["mentions"])
            ap_ing  = (ing_df[ing_df["region_group"] == "Asia-Pacific"]
                       .set_index("ingredient")["mentions"])
            all_ing = set(gb_ing.index) | set(ap_ing.index)
            cmp_rows = []
            for ing in sorted(all_ing):
                g    = int(gb_ing.get(ing, 0))
                a    = int(ap_ing.get(ing, 0))
                diff = g - a
                cmp_rows.append({
                    "Ingredient":   ing,
                    "Global":       g,
                    "Asia-Pacific": a,
                    "Gap (G-A)":    f"+{diff}" if diff > 0 else str(diff),
                })
            if cmp_rows:
                cmp_df = pd.DataFrame(cmp_rows).sort_values("Global", ascending=False)
                st.dataframe(cmp_df, use_container_width=True, hide_index=True, height=320)
            else:
                st.info("No comparison data for current filter.")
        with col_t2:
            st.markdown("**🏆 Top 3 Ingredients by Region Group**")
            for grp in REGION_GROUP_MAP.keys():
                grp_data = ing_df[ing_df["region_group"] == grp].nlargest(3, "mentions")
                if grp_data.empty:
                    continue
                top3 = " · ".join(
                    [f"{i+1}. {row['ingredient']}"
                     for i, (_, row) in enumerate(grp_data.iterrows())]
                )
                st.markdown(
                    f"<div style='margin-bottom:8px;padding:6px 10px;"
                    f"background:var(--background-color,#f8f9fa);"
                    f"border-left:3px solid #185FA5;border-radius:0 6px 6px 0;'>"
                    f"<div style='font-size:.85rem;font-weight:600;'>{grp}</div>"
                    f"<div style='font-size:.8rem;color:#718096;'>{top3}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── 6. Climate Formula Map ────────────────────────────────────
    st.markdown(
        "<div class='section-header'>"
        "🌍 Climate Formula Map — Region × Ingredient Category Heatmap"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Total engagement score per region × ingredient category combination. "
        "Use to identify which formulas resonate in which markets."
    )

    if keywords_df.empty:
        st.warning("keyword_hits data required.")
    else:
        # Use region_group (English) instead of raw region (Korean DB values)
        _cl = keywords_df.copy()
        _cl["region_group_en"] = _cl["region"].apply(get_region_group)
        cl_agg = (
            _cl.groupby(["region_group_en", "keyword_category"])
            .agg(mentions=("keyword", "count"), total_score=("score", "sum"))
            .reset_index()
        )
        pv = cl_agg.pivot_table(
            index="region_group_en", columns="keyword_category",
            values="total_score", aggfunc="sum", fill_value=0,
        )
        fig_cl = px.imshow(
            pv, color_continuous_scale="YlOrRd",
            title="Region Group × Ingredient Category Score Heatmap",
            labels={"color": "Total Score", "x": "Ingredient Category",
                    "y": "Region Group"},
            aspect="auto",
        )
        fig_cl.update_layout(height=420)
        st.plotly_chart(fig_cl, use_container_width=True)
# ══ END SECTION: render_tab_ingredient ══════════════════════════════


# ═══════════════════════════════════════════════════════════════════
#  TAB 3 — Consumer Intelligence
# ═══════════════════════════════════════════════════════════════════

# ╔══════════════════════════════════════════════════════╗
# ║  SECTION: render_tab_voc  [Phase 6 v7]              ║
# ╚══════════════════════════════════════════════════════╝
def render_tab_voc(filtered, posts_df, keywords_df):
    """
    Tab 3 — Consumer Intelligence
    Sections:
      1. Complaint Analysis + URS Priority Matrix
      2. Improvement Requests
      3. Positive Signal Tracker (NEW)
      4. Unmet Needs Storytelling
      5. Real-time Crisis Detection
    """

    st.markdown("""
    <div class='voc-header'>
        <h3>💬 Consumer Intelligence — VOC, Unmet Needs & Crisis Signals</h3>
        <p>Automatically detects complaints, improvement requests, positive signals,
        and crisis patterns from Reddit post titles and body text (selftext).<br>
        <b>URS Priority Score</b> = Mentions × Avg Score — higher = stronger consumer pain signal.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Shared VOC scanner ───────────────────────────────────────
    def _count_voc(df, kw_dict, label_col):
        results = []
        for cat, terms in kw_dict.items():
            pattern = "|".join(terms)
            mt = df[df["title"].str.contains(pattern, case=False, na=False)]
            mb = df[df["selftext"].str.contains(pattern, case=False, na=False)]
            matched = pd.concat([mt, mb]).drop_duplicates(subset="id")
            results.append({
                label_col:                     cat,
                "Mentions":                    len(matched),
                "Avg Score":                   round(matched["score"].mean(), 1) if len(matched) > 0 else 0,
                "Total Comments":              int(matched["num_comments"].sum()) if len(matched) > 0 else 0,
                "Search terms (sample)":       ", ".join(terms[:3]) + ("…" if len(terms) > 3 else ""),
            })
        return pd.DataFrame(results).sort_values("Mentions", ascending=False)

    complaint_df = _count_voc(filtered, COMPLAINT_DICT, "Complaint Type")
    improve_df   = _count_voc(filtered, IMPROVEMENT_DICT, "Request Type")
    positive_df  = _count_voc(filtered, POSITIVE_DICT,    "Positive Signal")

    # ── 1a. Complaint Analysis ────────────────────────────────────
    st.markdown(
        "<div class='section-header'>😤 Complaint Analysis</div>",
        unsafe_allow_html=True,
    )
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        fig_comp = px.bar(
            complaint_df, x="Mentions", y="Complaint Type", orientation="h",
            color="Avg Score", color_continuous_scale="RdYlGn_r",
            title="Complaints by Type (color = Avg Score)",
            labels={"Complaint Type": "Complaint Type", "Mentions": "Post Mentions"},
        )
        fig_comp.update_layout(height=380, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_comp, use_container_width=True)
    with col_c2:
        st.dataframe(
            complaint_df[["Complaint Type", "Mentions", "Avg Score", "Total Comments"]],
            use_container_width=True, hide_index=True, height=350,
        )

    # Top complaint sample posts
    if not complaint_df.empty and complaint_df["Mentions"].max() > 0:
        top_cat   = complaint_df.iloc[0]["Complaint Type"]
        top_terms = COMPLAINT_DICT[top_cat]
        pat       = "|".join(top_terms)
        samples   = (
            filtered[
                filtered["title"].str.contains(pat, case=False, na=False) |
                filtered["selftext"].str.contains(pat, case=False, na=False)
            ]
            .nlargest(5, "score")
        )
        st.markdown(f"**💡 Top posts for '{top_cat}' — copywriting & product source**")
        for _, row in samples.iterrows():
            st.markdown(_post_card(row), unsafe_allow_html=True)

    # ── 1b. URS Priority Matrix ───────────────────────────────────
    st.markdown(
        "<div class='section-header'>📋 URS Priority Matrix — Product Improvement Roadmap</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "**Priority Score = Mentions × Avg Score**  "
        "Higher frequency + higher engagement = stronger consumer pain signal."
    )
    complaint_df["Priority Score"] = (
        complaint_df["Mentions"] * complaint_df["Avg Score"]
    ).round(0)

    col_u1, col_u2 = st.columns([3, 2])
    with col_u1:
        if complaint_df["Priority Score"].sum() == 0:
            st.info("No complaint data in current filter.")
        else:
            urs_plot = complaint_df.copy()
            urs_plot["bubble_size"] = urs_plot["Priority Score"].clip(lower=1)
            fig_urs = px.scatter(
                urs_plot, x="Mentions", y="Avg Score",
                size="bubble_size", text="Complaint Type",
                color="Priority Score", color_continuous_scale="RdYlGn_r",
                title="URS Priority Matrix (bubble size = Priority Score)",
                labels={"Mentions": "Frequency (posts)", "Avg Score": "Engagement"},
            )
            fig_urs.update_traces(textposition="top center", textfont_size=9)
            fig_urs.update_layout(height=420)
            st.plotly_chart(fig_urs, use_container_width=True)
    with col_u2:
        top_urs = (
            complaint_df.nlargest(5, "Priority Score")
            [["Complaint Type", "Mentions", "Avg Score", "Priority Score"]]
            .reset_index(drop=True)
        )
        top_urs.index += 1
        st.markdown("**🔴 Immediate Improvement — Top 5**")
        for i, row in top_urs.iterrows():
            label = "🔴" if i == 1 else ("🟠" if i == 2 else "🟡")
            st.markdown(
                f"<div class='urs-card'>"
                f"<div class='uc-title'>{label} #{i} {row['Complaint Type']}</div>"
                f"<div class='uc-meta'>Mentions: {int(row['Mentions'])} &nbsp;|&nbsp; "
                f"Avg Score: <span class='uc-score'>{row['Avg Score']:,.0f}</span></div>"
                f"<div class='uc-meta'>Priority Score: <b>{row['Priority Score']:,.0f}</b></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Bottom KPI row
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Complaint Posts",          f"{int(complaint_df['Mentions'].sum()):,}")
    with m2: st.metric("Complaint Types",           f"{len(complaint_df)}")
    with m3: st.metric("Improvement Request Posts", f"{int(improve_df['Mentions'].sum()):,}")
    with m4: st.metric("Improvement Types",         f"{len(improve_df)}")

    # ── 2. Improvement Requests ───────────────────────────────────
    st.markdown(
        "<div class='section-header'>✅ Improvement Request Analysis</div>",
        unsafe_allow_html=True,
    )
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        fig_imp = px.bar(
            improve_df, x="Mentions", y="Request Type", orientation="h",
            color="Avg Score", color_continuous_scale="Blues",
            title="Improvement Requests by Type",
            labels={"Request Type": "Request Type", "Mentions": "Post Mentions"},
        )
        fig_imp.update_layout(height=340, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_imp, use_container_width=True)
    with col_i2:
        st.dataframe(
            improve_df[["Request Type", "Mentions", "Avg Score", "Total Comments"]],
            use_container_width=True, hide_index=True, height=310,
        )

    # ── 3. Positive Signal Tracker (NEW) ─────────────────────────
    st.markdown(
        "<div class='section-header'>"
        "💚 Positive Signal Tracker — What Consumers Love"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Tracks positive language signals: holy grail mentions, repurchase intent, "
        "skin transformation stories, brand love. Counter-balance to complaint analysis."
    )

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig_pos = px.bar(
            positive_df, x="Mentions", y="Positive Signal", orientation="h",
            color="Avg Score", color_continuous_scale="Greens",
            title="Positive Signals by Type (color = Avg Score)",
            labels={"Positive Signal": "", "Mentions": "Post Mentions"},
        )
        fig_pos.update_layout(height=320, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_pos, use_container_width=True)
    with col_p2:
        st.dataframe(
            positive_df[["Positive Signal", "Mentions", "Avg Score", "Total Comments"]],
            use_container_width=True, hide_index=True, height=290,
        )

    # Positive vs Negative ratio
    total_pos = int(positive_df["Mentions"].sum())
    total_neg = int(complaint_df["Mentions"].sum())
    if total_pos + total_neg > 0:
        ratio = total_pos / (total_pos + total_neg) * 100
        st.metric(
            "Positive Signal Ratio",
            f"{ratio:.1f}%",
            delta=f"{total_pos:,} positive vs {total_neg:,} negative posts",
        )

    # ── 4. Unmet Needs Storytelling ───────────────────────────────
    st.markdown(
        "<div class='section-header'>"
        "💔 Unmet Needs — Product Origin Story Signals"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Find unresolved consumer frustrations in post bodies. "
        "Use these as product development briefs or brand storytelling angles."
    )

    pain_rows = []
    for lbl, terms in PAIN_DICT.items():
        pat     = "|".join(terms)
        matched = posts_df[posts_df["selftext"].str.contains(pat, case=False, na=False)]
        pain_rows.append({
            "Skin Concern":       lbl,
            "Mentions":           len(matched),
            "Avg Score":          round(matched["score"].mean(), 1) if len(matched) > 0 else 0,
            "Total Comments":     int(matched["num_comments"].sum()),
            "Keywords (sample)":  ", ".join(terms[:3]),
        })
    pain_df = pd.DataFrame(pain_rows).sort_values("Mentions", ascending=False)

    col_pn1, col_pn2 = st.columns(2)
    with col_pn1:
        fig_pain = px.bar(
            pain_df, x="Mentions", y="Skin Concern", orientation="h",
            color="Avg Score", color_continuous_scale="RdYlGn_r",
            title="Skin Concern Mentions in Post Bodies (Unmet Needs)",
        )
        fig_pain.update_layout(height=350, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_pain, use_container_width=True)
    with col_pn2:
        st.dataframe(pain_df, use_container_width=True, hide_index=True, height=280)

    # ── 5. Real-time Crisis Detection ────────────────────────────
    st.markdown(
        "<div class='section-header'>"
        "🚨 Crisis Detection — Low-Consensus High-Visibility Posts"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Posts with high score but low upvote ratio signal divisive topics — "
        "potential PR / ingredient safety concerns."
    )

    risk_thresh = st.slider(
        "Crisis threshold (upvote ratio below)", 0.40, 0.70, 0.60, 0.01,
        key="risk_ratio_voc",
    )
    risk_min_sc = st.slider(
        "Min Score (noise filter)", 10, 200, 30, 10,
        key="risk_score_voc",
    )
    risk_posts = filtered[
        (filtered["upvote_ratio"] < risk_thresh) &
        (filtered["score"] >= risk_min_sc)
    ].sort_values("score", ascending=False)

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric(
            "🔴 Crisis Posts Detected", f"{len(risk_posts)}",
            delta=f"{len(risk_posts)/max(len(filtered), 1)*100:.1f}% of filtered",
        )
    with col_r2:
        st.metric("Avg Score",    f"{risk_posts['score'].mean():.0f}"          if len(risk_posts) > 0 else "0")
    with col_r3:
        st.metric("Max Comments", f"{int(risk_posts['num_comments'].max()):,}" if len(risk_posts) > 0 else "0")

    if not risk_posts.empty:
        col_ra, col_rb = st.columns(2)
        with col_ra:
            fig_risk = px.scatter(
                risk_posts, x="upvote_ratio", y="score",
                size="num_comments", color="subreddit", hover_data=["title"],
                title=f"⚠️ Crisis Posts (upvote ratio < {risk_thresh:.0%})",
                labels={"upvote_ratio": "Upvote Ratio", "score": "Score"},
            )
            fig_risk.add_vline(x=risk_thresh, line_dash="dash", line_color="red")
            fig_risk.update_layout(height=380)
            st.plotly_chart(fig_risk, use_container_width=True)
        with col_rb:
            st.markdown("**🚨 Immediate attention (highest Score first)**")
            for _, row in risk_posts.head(7).iterrows():
                st.markdown(
                    _post_card(row, border_color="#ef4444"),
                    unsafe_allow_html=True,
                )
# ══ END SECTION: render_tab_voc ═════════════════════════════════════
