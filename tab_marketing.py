# ═══════════════════════════════════════════════════════════════════
# tab_marketing.py — Tab 4: Marketing Actions
# Reddit Beauty Market Intelligence Dashboard v7.0
# Phase 7
# ═══════════════════════════════════════════════════════════════════

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    COMPLAINT_DICT, REGION_GROUP_MAP, REGION_ING_DICT,
    KEYWORD_CATEGORY_MAP, KEYWORD_NAME_MAP,
)
from tab_analysis import _normalize_keywords


# ───────────────────────────────────────────────────────────────────
#  Shared post card helper (duplicated to keep tab_marketing standalone)
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
    idx_badge = f"#{index + 1} &nbsp; " if index is not None else ""
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
        f"<div class='ptitle'>{idx_badge}💬 {link_html}</div>"
        f"<div class='pmeta'>"
        f"r/{sub_clean} &nbsp;|&nbsp; {row.get('region_group','')}"
        f" &nbsp;|&nbsp; <span class='pscore'>⭐ {int(row['score']):,}</span>"
        f" &nbsp;|&nbsp; 👍 {ratio_pct}"
        f" &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}"
        f"{src_link}"
        f"</div></div>"
    )


# ═══════════════════════════════════════════════════════════════════
#  TAB 4 — Marketing Actions
# ═══════════════════════════════════════════════════════════════════

# ╔══════════════════════════════════════════════════════╗
# ║  SECTION: render_tab_marketing  [Phase 7 v7]        ║
# ╚══════════════════════════════════════════════════════╝
def render_tab_marketing(filtered, posts_df, keywords_df):
    """
    Tab 4 — Marketing Actions  (4 Domains × 11 Techniques)
    Domain A — Content Marketing     : T1 VOC Copywriting · T2 Trend Calendar · T3 Unmet Needs*
    Domain B — Positioning           : T4 Traffic Light* · T5 Competitor Signal · T6 Climate*
    Domain C — Target Marketing      : T7 KOL Discovery · T8 Hybrid Dynamic Segments (NEW)
    Domain D — Risk / Viral          : T9 Gallery Proof · T10 Crisis* · T11 Crosspost Viral
    (* Moved to Tab 2/3 — reference links provided here)
    """

    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f3460,#533483);color:white;
                padding:18px 24px;border-radius:12px;margin-bottom:20px'>
        <h3 style='margin:0;font-family:DM Serif Display,serif'>
            🎯 Reddit Data-Driven Marketing Playbook — 11 Techniques
        </h3>
        <p style='margin:6px 0 0 0;opacity:.85;font-size:.9rem'>
            4 domains · 11 techniques · all driven by real collected data
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📊 All 11 Techniques — Quick Reference Table", expanded=False):
        overview = {
            "Domain":    (["A. Content"] * 2 +       # T1, T2
                          ["B. Positioning"] * 4 +    # T5, T8, T4(→Tab2), T6(→Tab2)
                          ["C. Targeting"] * 2 +      # T7, T9
                          ["D. Risk / Viral"] * 3),   # T10, T11, T12
            "Technique": [
                "T1. VOC Mirror Copywriting",
                "T2. Trend Pre-emption Calendar",
                "T5. Competitor Red Signal",
                "T8. Hybrid Dynamic Segments",
                "T7. Community KOL Discovery",
                "T9. Gallery Before & After",
                "T10. Crisis Early Detection ▶ Tab 3",
                "T11. Controversy Education",
                "T12. Crosspost Viral Amplification",
                "T4. Traffic Light ▶ Tab 2",
                "T6. Climate Formula ▶ Tab 2",
            ],
            "Key Data Fields": [
                "title · selftext · score · upvote_ratio",
                "keyword weighted index weekly delta",
                "upvote_ratio < 0.65 + score ≥ 50",
                "region_group × top_ingredient × top_complaint",
                "total_awards_received · author",
                "is_gallery · score",
                "upvote_ratio + negative sentiment + time",
                "upvote_ratio 0.5~0.7 band",
                "num_crossposts",
                "avg_upvote threshold",
                "region × keyword_category heatmap",
            ],
            "Time to Effect": [
                "Immediate", "4–8 weeks",
                "1–2 months", "Immediate",
                "1–3 months", "Immediate",
                "Immediate", "2–4 months", "Immediate",
                "3–6 months", "3–6 months",
            ],
        }
        st.dataframe(pd.DataFrame(overview), use_container_width=True,
                     hide_index=True, height=420)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # DOMAIN A — Content Marketing
    # ════════════════════════════════════════════════════════
    st.markdown(
        "<div class='section-header'>"
        "🅐 Domain A — Content Marketing · Speak the Consumer's Language"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── T1. VOC Mirror Copywriting ───────────────────────────────
    with st.expander(
        "📝 T1 — VOC Mirror Copywriting | Ad CTR +20–40%", expanded=True
    ):
        st.markdown("""
        > **Concept:** Posts with high score + high upvote ratio = community-validated language.
        > Use these exact phrases in ad copy for 20–40% CTR improvement.
        """)
        voc_score = st.slider("Min Score", 100, 2000, 300, 50, key="voc_score_t1")
        voc_ratio = st.slider("Min Upvote Ratio", 0.70, 1.00, 0.85, 0.01, key="voc_ratio_t1")
        voc_df = filtered[
            (filtered["score"] >= voc_score) &
            (filtered["upvote_ratio"] >= voc_ratio)
        ].nlargest(15, "score")

        if voc_df.empty:
            st.info("No posts match criteria. Lower the score or ratio threshold.")
        else:
            st.markdown(f"**✅ {len(voc_df)} posts — use these titles as copywriting source**")
            for _, row in voc_df.iterrows():
                st.markdown(_post_card(row), unsafe_allow_html=True)

    # ── T2. Trend Pre-emption Calendar ───────────────────────────
    with st.expander(
        "📅 T2 — Trend Pre-emption Calendar | SEO traffic +30%", expanded=False
    ):
        st.markdown("""
        > **Concept:** Weighted Trend Index = Score × upvote_ratio × log(comments+1).
        > Publish content on rising ingredients 2–4 weeks ahead of competitors.
        """)
        if keywords_df.empty:
            st.warning("keyword_hits data required. Run `keyword_matcher.py` first.")
        else:
            # Apply Korean→English normalization via shared helper
            kw_trend = _normalize_keywords(keywords_df)
            kw_trend["weighted_index"] = (
                kw_trend["score"] *
                kw_trend["upvote_ratio"].fillna(0.75) *
                np.log1p(kw_trend["num_comments"])
            )
            kw_sum = (
                kw_trend.groupby(["keyword", "keyword_category"])
                .agg(
                    mentions      = ("keyword",       "count"),
                    weighted_index= ("weighted_index","sum"),
                    avg_score     = ("score",         "mean"),
                    avg_upvote    = ("upvote_ratio",  "mean"),
                )
                .reset_index()
                .sort_values("weighted_index", ascending=False)
                .head(20)
            )
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                fig_tr = px.bar(
                    kw_sum, x="weighted_index", y="keyword",
                    orientation="h", color="keyword_category",
                    title="Weighted Trend Index by Ingredient (Top 20)",
                    labels={"keyword": "Ingredient", "keyword_category": "Category"},
                )
                fig_tr.update_layout(height=550, yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig_tr, use_container_width=True)
            with col_t2:
                fig_tr2 = px.scatter(
                    kw_sum, x="mentions", y="weighted_index",
                    size="avg_score", color="keyword_category",
                    hover_name="keyword",
                    title="Mentions vs Weighted Trend Index",
                )
                fig_tr2.update_layout(height=550)
                st.plotly_chart(fig_tr2, use_container_width=True)

    # ════════════════════════════════════════════════════════
    # DOMAIN B — Positioning
    # ════════════════════════════════════════════════════════
    st.markdown(
        "<div class='section-header'>"
        "🅑 Domain B — Product Positioning · Data-Proven Differentiation"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── T5. Competitor Red Signal ────────────────────────────────
    with st.expander(
        "⚔️ T5 — Competitor Red Signal Counter-positioning", expanded=True
    ):
        st.markdown("""
        > **Concept:** High-score posts with low upvote consensus reveal divisive competitor
        > ingredients or products. Use as counter-positioning signals in your own messaging.
        """)
        controversy = filtered[
            (filtered["upvote_ratio"] < 0.65) &
            (filtered["score"] >= 50)
        ].sort_values("score", ascending=False).head(10).copy()

        st.markdown(
            f"**📊 Low-consensus posts** (Score ≥ 50, Upvote < 65%): "
            f"{len(controversy)} posts"
        )
        if not controversy.empty:
            controversy["link"] = controversy["reddit_url"]
            st.dataframe(
                controversy[["subreddit", "title", "score", "upvote_ratio",
                              "num_comments", "region_group", "link"]],
                column_config={"link": st.column_config.LinkColumn("🔗 Link")},
                use_container_width=True, hide_index=True, height=300,
            )

    # ── T8. Hybrid Dynamic Segment Matrix ────────────────────────
    with st.expander(
        "🎯 T8 — Hybrid Dynamic Segments | ROAS +25–50%", expanded=True
    ):
        st.markdown("""
        > **Concept:** Auto-generates target segments from real DB data using 3 axes:
        > **Region Group** × **Top Ingredient** × **Top Complaint**.
        > Each segment shows evidence-backed posts. No hardcoded data.
        """)

        # Build segments: for each region_group × top ingredient × top complaint
        _seg_rows = []
        for grp in REGION_GROUP_MAP.keys():
            grp_df = filtered[filtered["region_group"] == grp]
            if len(grp_df) < 5:
                continue

            # Top ingredient (scan titles/bodies for REGION_ING_DICT terms)
            ing_counts = {}
            for ing, terms in REGION_ING_DICT.items():
                pat = "|".join(terms)
                cnt = (
                    grp_df["title"].str.contains(pat, case=False, na=False) |
                    grp_df["selftext"].str.contains(pat, case=False, na=False)
                ).sum()
                ing_counts[ing] = cnt
            top_ing = max(ing_counts, key=ing_counts.get) if ing_counts else "—"
            top_ing_cnt = ing_counts.get(top_ing, 0)

            # Top complaint
            complaint_counts = {}
            for cat, terms in COMPLAINT_DICT.items():
                pat = "|".join(terms)
                cnt = (
                    grp_df["title"].str.contains(pat, case=False, na=False) |
                    grp_df["selftext"].str.contains(pat, case=False, na=False)
                ).sum()
                complaint_counts[cat] = cnt
            top_complaint     = max(complaint_counts, key=complaint_counts.get) if complaint_counts else "—"
            top_complaint_cnt = complaint_counts.get(top_complaint, 0)

            _seg_rows.append({
                "Region Group":   grp,
                "Posts":          len(grp_df),
                "Top Ingredient": f"{top_ing} ({top_ing_cnt})",
                "Top Complaint":  f"{top_complaint} ({top_complaint_cnt})",
                "Avg Score":      round(grp_df["score"].mean(), 1),
                "Avg Upvote":     f"{grp_df['upvote_ratio'].mean()*100:.0f}%",
            })

        if _seg_rows:
            seg_df = pd.DataFrame(_seg_rows).sort_values("Posts", ascending=False)
            st.markdown("**Auto-Generated Segment Matrix (from live DB data)**")
            st.dataframe(seg_df, use_container_width=True, hide_index=True, height=280)

            # Drill-down: show top posts for selected segment
            st.markdown("**🔍 Segment Drill-down — Top Posts**")
            sel_seg = st.selectbox(
                "Select a Region Group to explore",
                seg_df["Region Group"].tolist(),
                key="seg_drilldown",
            )
            seg_posts = (
                filtered[filtered["region_group"] == sel_seg]
                .nlargest(5, "score")
            )
            for _, row in seg_posts.iterrows():
                st.markdown(_post_card(row), unsafe_allow_html=True)
        else:
            st.info("Not enough data per region group in current filter. Select 'All'.")

    # ════════════════════════════════════════════════════════
    # DOMAIN C — Target Marketing
    # ════════════════════════════════════════════════════════
    st.markdown(
        "<div class='section-header'>"
        "🅒 Domain C — Target Marketing · Precision Segment Targeting"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── T7. Community KOL Discovery ──────────────────────────────
    with st.expander(
        "⭐ T7 — Community-Verified KOL Discovery | Influence over follower count",
        expanded=True,
    ):
        st.markdown("""
        > **Concept:** Reddit awards = community-verified quality signal.
        > Authors with multiple awarded posts are organic KOL candidates — zero paid media.
        """)
        award_df = filtered[filtered["total_awards_received"] >= 1].copy()
        if award_df.empty:
            st.info("No awarded posts found in current filter.")
        else:
            kol_df = (
                award_df.groupby("author")
                .agg(
                    award_posts  = ("total_awards_received", "count"),
                    total_awards = ("total_awards_received", "sum"),
                    total_score  = ("score",                 "sum"),
                    avg_score    = ("score",                 "mean"),
                    top_subreddit= ("subreddit",
                                    lambda x: x.value_counts().index[0]
                                    if len(x.value_counts()) > 0 else ""),
                )
                .reset_index()
                .sort_values("total_awards", ascending=False)
            )
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                fig_kol = px.bar(
                    kol_df.head(15), x="total_awards", y="author",
                    orientation="h", color="total_score",
                    color_continuous_scale="Oranges",
                    title="Community-Verified KOL Top 15 (by Awards)",
                    labels={"author": "Author", "total_awards": "Total Awards"},
                )
                fig_kol.update_layout(
                    height=450, yaxis={"categoryorder": "total ascending"}
                )
                st.plotly_chart(fig_kol, use_container_width=True)
            with col_k2:
                st.dataframe(
                    kol_df.head(10)[[
                        "author", "award_posts", "total_awards",
                        "avg_score", "top_subreddit",
                    ]],
                    use_container_width=True, hide_index=True, height=380,
                )

    # ── T9. Gallery Before & After Social Proof ──────────────────
    with st.expander(
        "📸 T9 — Gallery Before & After Social Proof | PDP conversion +15–35%",
        expanded=False,
    ):
        st.markdown("""
        > **Concept:** Gallery posts (multiple images) score higher on average —
        > before/after content drives product page conversion.
        """)
        gallery_df  = filtered[filtered["is_gallery"] == 1].copy()
        non_gallery = filtered[filtered["is_gallery"] != 1].copy()

        col_g1, col_g2, col_g3 = st.columns(3)
        avg_g  = gallery_df["score"].mean()  if len(gallery_df)  > 0 else 0
        avg_ng = non_gallery["score"].mean() if len(non_gallery) > 0 else 0
        with col_g1: st.metric("Gallery Posts",       f"{len(gallery_df)}")
        with col_g2: st.metric("Gallery Avg Score",   f"{avg_g:.0f}",
                               delta=f"{avg_g - avg_ng:+.0f} vs regular posts")
        with col_g3: st.metric("Score ≥ 200 Gallery", f"{len(gallery_df[gallery_df['score'] >= 200])}")

        if not gallery_df.empty:
            st.markdown("**Top Gallery Posts**")
            for _, row in gallery_df.nlargest(5, "score").iterrows():
                st.markdown(_post_card(row), unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # DOMAIN D — Risk / Viral
    # ════════════════════════════════════════════════════════
    st.markdown(
        "<div class='section-header'>"
        "🅓 Domain D — Risk & Viral Marketing · Turn Crisis into Opportunity"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── T11. Controversy Education Marketing ─────────────────────
    with st.expander(
        "📚 T11 — Controversy Education Marketing | SEO evergreen traffic",
        expanded=False,
    ):
        st.markdown("""
        > **Concept:** Posts with moderate upvote ratio (50–70%) indicate
        > controversial topics with two sides — ideal for educational content
        > that captures both audiences and drives SEO long-tail traffic.
        """)
        edu_posts = filtered[
            (filtered["upvote_ratio"] >= 0.50) &
            (filtered["upvote_ratio"] <  0.70) &
            (filtered["score"] >= 30)
        ].copy()

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.metric("Controversial Posts", f"{len(edu_posts)}")
        with col_e2:
            st.metric(
                "Avg Score",
                f"{edu_posts['score'].mean():.0f}" if len(edu_posts) > 0 else "0",
            )

        if not edu_posts.empty:
            st.markdown("**Top Controversial Posts (education content opportunities)**")
            for _, row in edu_posts.nlargest(5, "score").iterrows():
                st.markdown(
                    _post_card(row, border_color="#f59e0b"),
                    unsafe_allow_html=True,
                )

    # ── T12. Crosspost Viral Amplification ───────────────────────
    with st.expander(
        "🔥 T12 — Crosspost Viral Amplification | Trend timing capture",
        expanded=True,
    ):
        st.markdown("""
        > **Concept:** Posts with multiple crossposts = community-validated viral content.
        > Amplify these immediately across brand channels.
        """)
        cp_thresh = st.slider("Min crossposts", 1, 10, 2, 1, key="cp_threshold_t12")
        viral_posts = filtered[filtered["num_crossposts"] >= cp_thresh].copy()

        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1: st.metric("🔥 Viral Posts", f"{len(viral_posts)}")
        with col_v2: st.metric(
            "Avg Crossposts",
            f"{viral_posts['num_crossposts'].mean():.1f}" if len(viral_posts) > 0 else "0",
        )
        with col_v3: st.metric(
            "Max Crossposts",
            f"{int(viral_posts['num_crossposts'].max())}" if len(viral_posts) > 0 else "0",
        )

        if not viral_posts.empty:
            st.markdown("**⚡ Immediate action — highest crossposts first**")
            for _, row in viral_posts.nlargest(7, "num_crossposts").iterrows():
                url        = row.get("reddit_url", "")
                title_str  = str(row["title"])[:85]
                link_html  = (
                    f'<a href="{url}" target="_blank" style="color:#1a1a2e;'
                    f'text-decoration:none;">{title_str}</a>'
                    if url else title_str
                )
                src_link = (
                    f'&nbsp;|&nbsp;<a href="{url}" target="_blank" '
                    f'style="font-size:.75rem;color:#718096;">source ↗</a>'
                    if url else ""
                )
                sub_clean = str(row.get("subreddit", "")).removeprefix("r/")
                st.markdown(
                    f"<div class='post-card' style='border-left-color:#f59e0b;'>"
                    f"<div class='ptitle'>🔥 {link_html}</div>"
                    f"<div class='pmeta'>r/{sub_clean} &nbsp;|&nbsp; "
                    f"<span style='color:#f59e0b;font-weight:700;'>"
                    f"🔁 {int(row['num_crossposts'])} crossposts"
                    f"</span>"
                    f" &nbsp;|&nbsp; ⭐ {int(row['score']):,}"
                    f"{src_link}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
# ══ END SECTION: render_tab_marketing ═══════════════════════════════
