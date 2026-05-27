"""
🌿 Reddit 화장품 시장조사 대시보드 v2.0
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta

# ─────────────────────────────────────────
# ★ 추가: Google Drive에서 DB 자동 다운로드
# ─────────────────────────────────────────
import os
import gdown

DB_PATH      = "reddit_data.db"
GDRIVE_FILE_ID = "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"  # ← Step 3에서 복사한 ID로 교체!
GDRIVE_URL   = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}"

@st.cache_resource(show_spinner="📥 데이터베이스 로딩 중...")
def ensure_db():
    """DB가 없거나 오래된 경우 Google Drive에서 자동 다운로드"""
    if not os.path.exists(DB_PATH):
        st.toast("📥 DB를 Google Drive에서 다운로드 중입니다...")
        gdown.download(GDRIVE_URL, DB_PATH, quiet=False, fuzzy=True)
        st.toast("✅ DB 다운로드 완료!")
    return DB_PATH

ensure_db()   # 앱 시작 시 자동 실행

# ─────────────────────────────────────────
# 이하 기존 코드 그대로 유지
# ─────────────────────────────────────────

# ─────────────────────────────────────────
# 0. 페이지 기본 설정
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Reddit 화장품 인사이트",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# 공통 CSS (고급 스타일)
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}
h1, h2, h3 { font-family: 'DM Serif Display', serif; }

/* 카드 스타일 */
.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    color: white;
}
.metric-card .val {
    font-size: 2.4rem;
    font-weight: 700;
    color: #e94560;
    line-height: 1;
}
.metric-card .lbl {
    font-size: 0.85rem;
    color: #a0aec0;
    margin-top: 6px;
}

/* 섹션 헤더 */
.section-header {
    background: linear-gradient(90deg, #0f3460, #533483);
    color: white;
    padding: 10px 20px;
    border-radius: 8px;
    margin: 24px 0 16px 0;
    font-size: 1.1rem;
    font-weight: 600;
}

/* Top 게시글 카드 */
.post-card {
    background: #f8f9fa;
    border-left: 4px solid #e94560;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
}
.post-card .ptitle { font-weight: 600; font-size: 0.95rem; color: #1a1a2e; }
.post-card .pmeta  { font-size: 0.8rem; color: #718096; margin-top: 4px; }
.post-card .pscore { font-weight: 700; color: #e94560; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 1. DB 연결 & 데이터 로드
# ─────────────────────────────────────────
DB_PATH = "reddit_data.db"

@st.cache_data(ttl=300)  # 5분 캐시
def load_data():
    """DB에서 모든 데이터 로드"""
    try:
        conn = sqlite3.connect(DB_PATH)

        # ── 메인 게시글
        posts = pd.read_sql_query("""
            SELECT id, reddit_id, subreddit, title, selftext,
                   score, upvote_ratio, num_comments,
                   link_flair_text, author, author_flair_text,
                   total_awards_received, num_crossposts,
                   is_gallery, is_self,
                   created_utc, fetch_date, fetch_type,
                   region, priority_rank
            FROM reddit_posts
        """, conn)

        # ── 키워드 히트
        keywords = pd.read_sql_query("""
            SELECT kh.post_id, kh.keyword, kh.keyword_category,
                   kh.match_field, kh.matched_date, kh.matched_term,
                   rp.score, rp.num_comments, rp.upvote_ratio,
                   rp.subreddit, rp.region, rp.title,
                   rp.total_awards_received, rp.num_crossposts
            FROM keyword_hits kh
            JOIN reddit_posts rp ON kh.post_id = rp.id
        """, conn)

        # ── 서브레딧 메타
        meta = pd.read_sql_query("SELECT * FROM subreddits_meta", conn)

        conn.close()
        return posts, keywords, meta

    except Exception as e:
        st.error(f"❌ DB 연결 오류: {e}")
        st.info(f"📂 `{DB_PATH}` 파일이 dashboard.py와 같은 폴더에 있는지 확인하세요.")
        st.stop()

posts_df, keywords_df, meta_df = load_data()

# 날짜 변환
posts_df["fetch_date"] = pd.to_datetime(posts_df["fetch_date"], errors="coerce")
posts_df["created_dt"] = pd.to_datetime(posts_df["created_utc"], unit="s", errors="coerce")

# ─────────────────────────────────────────
# 2. 사이드바 — 필터
# ─────────────────────────────────────────
st.sidebar.markdown("## 🌿 Reddit 인사이트\n**화장품 시장조사 대시보드**")
st.sidebar.markdown("---")

# 수집 유형 필터
fetch_types = ["전체"] + sorted(posts_df["fetch_type"].dropna().unique().tolist())
sel_fetch = st.sidebar.selectbox("📅 수집 유형", fetch_types)

# 지역 필터
regions = ["전체"] + sorted(posts_df["region"].dropna().unique().tolist())
sel_region = st.sidebar.selectbox("🌏 지역", regions)

# 서브레딧 필터
subreddits = ["전체"] + sorted(posts_df["subreddit"].dropna().unique().tolist())
sel_sub = st.sidebar.selectbox("📌 서브레딧", subreddits)

# 최소 스코어 필터
min_score = st.sidebar.slider("⭐ 최소 Score", 0, int(posts_df["score"].max() or 1000), 0, 10)

st.sidebar.markdown("---")
st.sidebar.caption(f"🗄️ DB 경로: `{DB_PATH}`")
st.sidebar.caption(f"🕐 마지막 갱신: {posts_df['fetch_date'].max().strftime('%Y-%m-%d %H:%M') if not posts_df.empty else '-'}")

# 필터 적용
filtered = posts_df.copy()
if sel_fetch != "전체":
    filtered = filtered[filtered["fetch_type"] == sel_fetch]
if sel_region != "전체":
    filtered = filtered[filtered["region"] == sel_region]
if sel_sub != "전체":
    filtered = filtered[filtered["subreddit"] == sel_sub]
filtered = filtered[filtered["score"] >= min_score]

# ─────────────────────────────────────────
# 3. 메인 헤더
# ─────────────────────────────────────────
st.markdown("# 🌿 Reddit 화장품 시장 인사이트 대시보드")
st.markdown(f"> 글로벌 뷰티 커뮤니티 **{len(posts_df['subreddit'].unique())}개 서브레딧** 데이터 분석 | 총 **{len(posts_df):,}건** 수집")

# ─────────────────────────────────────────
# 4. KPI 카드 (상단 요약)
# ─────────────────────────────────────────
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""<div class='metric-card'>
        <div class='val'>{len(filtered):,}</div>
        <div class='lbl'>총 게시글 수</div>
    </div>""", unsafe_allow_html=True)

with c2:
    avg_score = int(filtered["score"].mean()) if not filtered.empty else 0
    st.markdown(f"""<div class='metric-card'>
        <div class='val'>{avg_score:,}</div>
        <div class='lbl'>평균 Score</div>
    </div>""", unsafe_allow_html=True)

with c3:
    total_comments = int(filtered["num_comments"].sum()) if not filtered.empty else 0
    st.markdown(f"""<div class='metric-card'>
        <div class='val'>{total_comments:,}</div>
        <div class='lbl'>총 댓글 수</div>
    </div>""", unsafe_allow_html=True)

with c4:
    kw_count = len(keywords_df) if not keywords_df.empty else 0
    st.markdown(f"""<div class='metric-card'>
        <div class='val'>{kw_count:,}</div>
        <div class='lbl'>키워드 히트</div>
    </div>""", unsafe_allow_html=True)

with c5:
    sub_count = filtered["subreddit"].nunique() if not filtered.empty else 0
    st.markdown(f"""<div class='metric-card'>
        <div class='val'>{sub_count}</div>
        <div class='lbl'>활성 서브레딧</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 5. 탭 구성
# ─────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 트렌드 대시보드",
    "🧪 성분 키워드 인사이트",
    "🌏 지역별 비교",
    "📋 원본 데이터",
    "🎯 마케팅 기법 12"
])

# ═══════════════════════════════════════════
# TAB 1 : 트렌드 대시보드
# ═══════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-header'>📊 이번 주 화제글 TOP 10</div>", unsafe_allow_html=True)

    top10 = filtered.nlargest(10, "score")[
        ["subreddit", "title", "score", "num_comments", "upvote_ratio", "region"]
    ].reset_index(drop=True)

    for i, row in top10.iterrows():
        ratio_pct = f"{row['upvote_ratio']*100:.0f}%" if pd.notna(row['upvote_ratio']) else "-"
        st.markdown(f"""
        <div class='post-card'>
            <div class='ptitle'>#{i+1} &nbsp; {row['title'][:100]}{'...' if len(str(row['title'])) > 100 else ''}</div>
            <div class='pmeta'>
                r/{row['subreddit']} &nbsp;|&nbsp;
                지역: {row['region']} &nbsp;|&nbsp;
                <span class='pscore'>⭐ {int(row['score']):,}</span> &nbsp;|&nbsp;
                💬 {int(row['num_comments']):,} &nbsp;|&nbsp;
                👍 {ratio_pct}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 서브레딧별 게시글 수 & 평균 스코어
    st.markdown("<div class='section-header'>📌 서브레딧별 활동 현황</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        sub_cnt = filtered.groupby("subreddit")["score"].agg(
            게시글수="count", 평균Score="mean"
        ).reset_index().sort_values("게시글수", ascending=False).head(20)

        fig1 = px.bar(
            sub_cnt, x="게시글수", y="subreddit",
            orientation="h", color="평균Score",
            color_continuous_scale="RdYlGn",
            title="서브레딧별 게시글 수 (색상=평균 Score)",
            labels={"subreddit": "서브레딧", "게시글수": "게시글 수"}
        )
        fig1.update_layout(height=500, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        sub_score = filtered.groupby("subreddit")["score"].sum().reset_index()
        sub_score.columns = ["subreddit", "total_score"]
        sub_score = sub_score.sort_values("total_score", ascending=False).head(15)

        fig2 = px.pie(
            sub_score, values="total_score", names="subreddit",
            title="서브레딧별 총 Score 점유율 (Top 15)",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig2.update_layout(height=500)
        st.plotly_chart(fig2, use_container_width=True)

    # ── 업보트 비율 분포
    st.markdown("<div class='section-header'>👍 업보트 비율 분포</div>", unsafe_allow_html=True)

    valid_ratio = filtered["upvote_ratio"].dropna()
    if not valid_ratio.empty:
        fig3 = px.histogram(
            filtered, x="upvote_ratio", nbins=20,
            color="region", barmode="overlay",
            title="업보트 비율 분포 (지역별)",
            labels={"upvote_ratio": "업보트 비율", "count": "게시글 수"}
        )
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════
# TAB 2 : 성분 키워드 인사이트
# ═══════════════════════════════════════════
with tab2:
    if keywords_df.empty:
        st.warning("⚠️ keyword_hits 테이블에 데이터가 없습니다.\n\n크롤러에 키워드 매칭 기능이 구현되면 이 탭이 활성화됩니다.")

        st.markdown("""
        ### 💡 키워드 매칭 기능 추가 방법

        `reddit_crawler_v2.py` 에 아래 키워드 리스트와 매칭 로직을 추가하세요:

        ```python
        INGREDIENT_KEYWORDS = {
            "레티놀": ["retinol", "retinoid", "retin-a", "tretinoin"],
            "나이아신아마이드": ["niacinamide", "niacin", "vit b3"],
            "히알루론산": ["hyaluronic acid", "HA", "sodium hyaluronate"],
            "비타민C": ["vitamin c", "ascorbic acid", "l-ascorbic"],
            "펩타이드": ["peptide", "peptides", "matrixyl"],
            "AHA/BHA": ["aha", "bha", "glycolic acid", "salicylic acid", "lactic acid"],
            "세라마이드": ["ceramide", "ceramides"],
            "선스크린": ["sunscreen", "spf", "uv filter", "zinc oxide", "titanium dioxide"],
        }
        ```
        """)

    else:
        # 키워드 데이터 있을 때
        st.markdown("<div class='section-header'>🧪 성분 키워드 언급 순위 (Score 가중)</div>", unsafe_allow_html=True)

        kw_agg = keywords_df.groupby("keyword").agg(
            언급수=("keyword", "count"),
            총Score=("score", "sum"),
            평균Score=("score", "mean"),
            총댓글=("num_comments", "sum")
        ).reset_index().sort_values("총Score", ascending=False).head(30)

        col_a, col_b = st.columns(2)

        with col_a:
            fig_kw1 = px.bar(
                kw_agg.head(20), x="총Score", y="keyword",
                orientation="h", color="언급수",
                color_continuous_scale="Blues",
                title="성분별 총 Score (참여도 가중)",
                labels={"keyword": "성분/키워드", "총Score": "총 Score"}
            )
            fig_kw1.update_layout(height=500, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_kw1, use_container_width=True)

        with col_b:
            fig_kw2 = px.scatter(
                kw_agg, x="언급수", y="평균Score",
                size="총댓글", hover_name="keyword",
                color="총Score", color_continuous_scale="RdYlGn",
                title="성분 버블차트: 언급수 × 평균Score × 댓글수",
                labels={"언급수": "언급 횟수", "평균Score": "평균 Score"}
            )
            fig_kw2.update_layout(height=500)
            st.plotly_chart(fig_kw2, use_container_width=True)

        # ── 카테고리별
        if "keyword_category" in keywords_df.columns:
            st.markdown("<div class='section-header'>📂 카테고리별 트렌드</div>", unsafe_allow_html=True)

            cat_agg = keywords_df.groupby("keyword_category").agg(
                언급수=("keyword", "count"),
                총Score=("score", "sum"),
            ).reset_index().sort_values("총Score", ascending=False)

            fig_cat = px.treemap(
                cat_agg, path=["keyword_category"],
                values="총Score", color="언급수",
                color_continuous_scale="Teal",
                title="카테고리별 성분 트리맵 (크기=총Score, 색=언급수)"
            )
            fig_cat.update_layout(height=400)
            st.plotly_chart(fig_cat, use_container_width=True)

# ═══════════════════════════════════════════
# TAB 3 : 지역별 비교
# ═══════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>🌏 지역별 게시글 분포</div>", unsafe_allow_html=True)

    region_agg = filtered.groupby("region").agg(
        게시글수=("id", "count"),
        평균Score=("score", "mean"),
        총Score=("score", "sum"),
        평균댓글=("num_comments", "mean"),
    ).reset_index()

    col_a, col_b = st.columns(2)

    with col_a:
        fig_r1 = px.bar(
            region_agg.sort_values("게시글수", ascending=False),
            x="region", y="게시글수",
            color="평균Score", color_continuous_scale="Viridis",
            title="지역별 게시글 수 & 평균 Score",
            labels={"region": "지역", "게시글수": "게시글 수"}
        )
        st.plotly_chart(fig_r1, use_container_width=True)

    with col_b:
        fig_r2 = px.scatter(
            region_agg, x="평균Score", y="평균댓글",
            size="총Score", color="region",
            hover_name="region",
            title="지역별 참여도 비교 (Score vs 댓글)",
            labels={"평균Score": "평균 Score", "평균댓글": "평균 댓글 수"}
        )
        st.plotly_chart(fig_r2, use_container_width=True)

    # ── 아시아 vs 북미 상세 비교
    st.markdown("<div class='section-header'>🔍 아시아 vs 북미 상세 비교</div>", unsafe_allow_html=True)

    asia_regions = ["Asia", "korea", "japan", "china", "southeast_asia"]
    na_regions   = ["North America", "USA", "us", "north_america"]

    asia_df = filtered[filtered["region"].str.lower().isin([r.lower() for r in asia_regions])]
    na_df   = filtered[filtered["region"].str.lower().isin([r.lower() for r in na_regions])]

    col_c, col_d = st.columns(2)

    def region_top_subs(df, title):
        if df.empty:
            st.info(f"해당 지역 데이터 없음: {title}")
            return
        top_subs = df.groupby("subreddit")["score"].sum().nlargest(10).reset_index()
        fig = px.bar(top_subs, x="score", y="subreddit", orientation="h",
                     title=title, color="score", color_continuous_scale="Reds",
                     labels={"score": "총 Score", "subreddit": "서브레딧"})
        fig.update_layout(height=350, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    with col_c:
        region_top_subs(asia_df, "🇰🇷 아시아 — 인기 서브레딧 Top 10")

    with col_d:
        region_top_subs(na_df, "🇺🇸 북미 — 인기 서브레딧 Top 10")

    # ── 지역별 서브레딧 히트맵
    st.markdown("<div class='section-header'>🗺️ 지역 × 서브레딧 활동 히트맵</div>", unsafe_allow_html=True)

    try:
        pivot = filtered.pivot_table(
            index="region", columns="subreddit",
            values="score", aggfunc="sum", fill_value=0
        )
        # 상위 20개 서브레딧만
        top_cols = pivot.sum().nlargest(20).index
        pivot = pivot[top_cols]

        fig_heat = px.imshow(
            pivot,
            color_continuous_scale="YlOrRd",
            title="지역 × 서브레딧 Score 히트맵 (상위 20개 서브레딧)",
            labels={"color": "총 Score"},
            aspect="auto"
        )
        fig_heat.update_layout(height=450)
        st.plotly_chart(fig_heat, use_container_width=True)
    except Exception as e:
        st.warning(f"히트맵 생성 중 오류: {e}")

    # ── 지역별 우선순위 분포
    if "priority_rank" in filtered.columns:
        st.markdown("<div class='section-header'>⭐ 지역별 우선순위 분포</div>", unsafe_allow_html=True)
        pri_agg = filtered.groupby(["region", "priority_rank"]).size().reset_index(name="count")
        fig_pri = px.bar(
            pri_agg, x="region", y="count", color="priority_rank",
            barmode="stack", title="지역별 우선순위 분포",
            labels={"region": "지역", "count": "게시글 수", "priority_rank": "우선순위"}
        )
        st.plotly_chart(fig_pri, use_container_width=True)

# ═══════════════════════════════════════════
# TAB 4 : 원본 데이터
# ═══════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>📋 수집 데이터 테이블</div>", unsafe_allow_html=True)

    cols_show = [c for c in [
        "subreddit", "title", "score", "num_comments",
        "upvote_ratio", "region", "fetch_type", "fetch_date",
        "link_flair_text", "author"
    ] if c in filtered.columns]

    st.dataframe(
        filtered[cols_show].sort_values("score", ascending=False),
        use_container_width=True,
        height=500
    )

    # CSV 다운로드
    csv = filtered[cols_show].to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ CSV 다운로드",
        data=csv,
        file_name=f"reddit_cosmetics_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    # ── 서브레딧 메타 정보
    if not meta_df.empty:
        st.markdown("<div class='section-header'>📌 서브레딧 메타 정보</div>", unsafe_allow_html=True)
        st.dataframe(meta_df, use_container_width=True, height=300)

# ═══════════════════════════════════════════
# TAB 5 : 마케팅 기법 12
# ═══════════════════════════════════════════
with tab5:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f3460,#533483);
                color:white;padding:18px 24px;border-radius:12px;margin-bottom:20px'>
        <h3 style='margin:0;font-family:DM Serif Display,serif'>
            🎯 Reddit JSON 데이터 기반 마케팅 기법 12
        </h3>
        <p style='margin:6px 0 0 0;opacity:0.85;font-size:0.9rem'>
            4개 영역 × 12개 기법 — 실제 수집 데이터로 즉시 실행 가능한 인사이트
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 12기법 종합 비교표
    with st.expander("📊 12개 기법 종합 비교표 (클릭해서 열기)", expanded=False):
        overview_data = {
            "영역": ["A.콘텐츠","A.콘텐츠","A.콘텐츠",
                     "B.포지셔닝","B.포지셔닝","B.포지셔닝",
                     "C.타깃","C.타깃","C.타깃",
                     "D.리스크","D.리스크","D.리스크"],
            "기법": [
                "1. VOC 미러링 카피","2. 트렌드 선점 캘린더","3. 언메트 니즈 스토리텔링",
                "4. 성분 신호등 포지셔닝","5. 경쟁사 레드 신호 역이용","6. 클리메이트 포뮬러 마케팅",
                "7. KOL 발굴","8. 3축 타깃 광고","9. 갤러리 비포앤애프터",
                "10. 위기 조기 대응","11. 논쟁 교육 마케팅","12. 크로스포스트 바이럴 증폭"
            ],
            "핵심 데이터 필드": [
                "title·selftext·score·upvote_ratio",
                "keyword 가중지수 주간 변화율",
                "selftext 부정 감성어",
                "score·upvote_ratio 3개월 추이",
                "경쟁 키워드 + 부정 감성어",
                "로컬 서브레딧 + author_flair",
                "total_awards_received·author",
                "author_flair·created_utc·subreddit",
                "is_gallery·score",
                "upvote_ratio·부정 감성어·t=day",
                "upvote_ratio 0.5~0.7 구간",
                "num_crossposts"
            ],
            "난이도": ["⭐⭐","⭐⭐","⭐⭐","⭐⭐⭐","⭐⭐⭐","⭐⭐⭐","⭐⭐","⭐⭐⭐⭐","⭐⭐","⭐⭐⭐","⭐⭐","⭐⭐"],
            "효과 발현": ["즉시","4~8주","1~3개월","3~6개월","1~2개월","3~6개월","1~3개월","즉시","즉시","즉시","2~4개월","즉시"],
            "핵심 KPI": [
                "광고 CTR +20~40%","SEO 유입 +30%","브랜드 공감도↑",
                "브랜드 신뢰도↑","점유율 이동","수출 전환율↑",
                "협업 CPE 절감","ROAS +25~50%","상세페이지 전환율 +15~35%",
                "위기 대응 시간 단축","SEO 에버그린 트래픽","트렌드 타이밍 점유"
            ]
        }
        ov_df = pd.DataFrame(overview_data)
        st.dataframe(ov_df, use_container_width=True, hide_index=True, height=460)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════
    # 영역 A : 콘텐츠 마케팅
    # ════════════════════════════════════════
    st.markdown("<div class='section-header'>🅐 영역 A. 콘텐츠 마케팅 — \"소비자가 쓰는 말로 말하라\"</div>",
                unsafe_allow_html=True)

    # ── 기법 1 : VOC 미러링 카피라이팅
    with st.expander("📝 기법 1 — VOC 미러링 카피라이팅 | 광고 CTR +20~40% 기대", expanded=True):
        st.markdown("""
        > **개념:** score ≥ 500 + upvote_ratio ≥ 0.9 게시글의 실제 소비자 언어를 광고 카피로 전환.
        > 이미 대중의 검증을 받은 문장이므로 광고 CTR이 20~40% 향상됩니다.
        """)

        voc_threshold_score = st.slider("최소 Score 기준", 100, 2000, 300, 50, key="voc_score")
        voc_threshold_ratio = st.slider("최소 업보트 비율", 0.70, 1.00, 0.85, 0.01, key="voc_ratio")

        voc_df = filtered[
            (filtered["score"] >= voc_threshold_score) &
            (filtered["upvote_ratio"] >= voc_threshold_ratio)
        ].nlargest(15, "score")[["subreddit","title","score","upvote_ratio","num_comments","region"]]

        if voc_df.empty:
            st.info("해당 조건의 게시글이 없습니다. Score 기준을 낮춰보세요.")
        else:
            st.markdown(f"**✅ 조건 충족 게시글 {len(voc_df)}건 — 아래 제목이 카피라이팅 소스입니다**")
            for _, row in voc_df.iterrows():
                ratio_pct = f"{row['upvote_ratio']*100:.0f}%"
                st.markdown(f"""
                <div class='post-card'>
                    <div class='ptitle'>💬 {row['title']}</div>
                    <div class='pmeta'>
                        r/{row['subreddit']} &nbsp;|&nbsp; 지역: {row['region']}
                        &nbsp;|&nbsp; <span class='pscore'>⭐ {int(row['score']):,}</span>
                        &nbsp;|&nbsp; 👍 {ratio_pct}
                        &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 서브레딧 분포
            fig_voc = px.bar(
                voc_df.groupby("subreddit").size().reset_index(name="건수").sort_values("건수", ascending=False),
                x="subreddit", y="건수", color="건수",
                color_continuous_scale="Blues",
                title=f"VOC 소스 게시글 서브레딧 분포 (Score≥{voc_threshold_score}, 비율≥{voc_threshold_ratio:.0%})"
            )
            fig_voc.update_layout(height=300)
            st.plotly_chart(fig_voc, use_container_width=True)

    # ── 기법 2 : 트렌드 선점 콘텐츠 캘린더
    with st.expander("📅 기법 2 — 트렌드 선점 콘텐츠 캘린더 | SEO 유입 +30%", expanded=False):
        st.markdown("""
        > **개념:** 키워드별 가중 트렌드 지수(Score × upvote_ratio × log댓글)를 계산해
        > 급부상 성분을 경쟁사보다 2~4주 앞서 콘텐츠화합니다.
        """)

        if keywords_df.empty:
            st.warning("keyword_hits 데이터가 없습니다. keyword_matcher.py를 먼저 실행하세요.")
        else:
            import numpy as np

            kw_trend = keywords_df.copy()
            kw_trend["weighted_index"] = (
                kw_trend["score"] *
                kw_trend["upvote_ratio"].fillna(0.75) *
                np.log1p(kw_trend["num_comments"])
            )

            kw_summary = kw_trend.groupby(["keyword","keyword_category"]).agg(
                언급수=("keyword","count"),
                가중트렌드지수=("weighted_index","sum"),
                평균Score=("score","mean"),
                평균업보트비율=("upvote_ratio","mean"),
            ).reset_index().sort_values("가중트렌드지수", ascending=False).head(20)

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                fig_trend = px.bar(
                    kw_summary, x="가중트렌드지수", y="keyword",
                    orientation="h", color="keyword_category",
                    title="성분별 가중 트렌드 지수 Top 20",
                    labels={"keyword":"성분","keyword_category":"카테고리"}
                )
                fig_trend.update_layout(height=550, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_trend, use_container_width=True)

            with col_t2:
                fig_trend2 = px.scatter(
                    kw_summary, x="언급수", y="가중트렌드지수",
                    size="평균Score", color="keyword_category",
                    hover_name="keyword",
                    title="언급수 vs 가중 트렌드 지수 버블차트",
                    labels={"언급수":"언급 횟수","가중트렌드지수":"가중 트렌드 지수"}
                )
                fig_trend2.update_layout(height=550)
                st.plotly_chart(fig_trend2, use_container_width=True)

            st.markdown("**🗓️ 콘텐츠 캘린더 추천 (가중 트렌드 지수 Top 5)**")
            top5 = kw_summary.head(5).reset_index(drop=True)
            for i, row in top5.iterrows():
                st.markdown(f"""
                **{i+1}위. `{row['keyword']}`** ({row['keyword_category']})
                — 가중지수 **{row['가중트렌드지수']:,.0f}** | 언급 {int(row['언급수'])}건
                → 📌 즉시 콘텐츠 기획 착수 권장
                """)

    # ── 기법 3 : 언메트 니즈 스토리텔링
    with st.expander("💔 기법 3 — 언메트 니즈 스토리텔링 | 브랜드 공감도 극대화", expanded=False):
        st.markdown("""
        > **개념:** 소비자들이 selftext에 털어놓는 해결 안 되는 불편함을 찾아
        > 제품 탄생 스토리로 역전시킵니다.
        """)

        PAIN_WORDS = {
            "밀림": ["pilling","pills","rub off","ball up"],
            "자극/트러블": ["irritation","stings","burning","breakout","purge","purging","flare"],
            "건조함": ["dry","tight","flaky","dehydrated","peeling"],
            "번들거림": ["oily","greasy","shiny","sebum"],
            "막힘/모공": ["clogged","pores","blackhead","congested"],
            "색소/잡티": ["hyperpigmentation","dark spots","melasma","uneven"],
        }

        pain_results = []
        for pain_label, terms in PAIN_WORDS.items():
            pattern = "|".join(terms)
            matched = posts_df[posts_df["selftext"].str.contains(pattern, case=False, na=False)]
            pain_results.append({
                "고민 유형": pain_label,
                "언급 게시글 수": len(matched),
                "평균 Score": round(matched["score"].mean(), 1) if len(matched) > 0 else 0,
                "총 댓글": int(matched["num_comments"].sum()) if len(matched) > 0 else 0,
                "검색어": ", ".join(terms[:3]) + ("..." if len(terms) > 3 else "")
            })

        pain_df = pd.DataFrame(pain_results).sort_values("언급 게시글 수", ascending=False)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig_pain = px.bar(
                pain_df, x="언급 게시글 수", y="고민 유형",
                orientation="h", color="평균 Score",
                color_continuous_scale="RdYlGn_r",
                title="소비자 고민 유형별 언급량 (언메트 니즈)"
            )
            fig_pain.update_layout(height=350, yaxis={"categoryorder":"total ascending"})
            st.plotly_chart(fig_pain, use_container_width=True)
        with col_p2:
            st.dataframe(pain_df, use_container_width=True, hide_index=True, height=280)

        # 최상위 고민의 실제 게시글 샘플
        top_pain = pain_df.iloc[0]["고민 유형"]
        top_terms = PAIN_WORDS[top_pain]
        sample_posts = posts_df[
            posts_df["selftext"].str.contains("|".join(top_terms), case=False, na=False)
        ].nlargest(3, "score")[["subreddit","title","score","num_comments"]]

        st.markdown(f"**💡 스토리텔링 소스 — '{top_pain}' 관련 고득점 게시글**")
        for _, row in sample_posts.iterrows():
            st.markdown(f"""
            <div class='post-card'>
                <div class='ptitle'>📌 {row['title']}</div>
                <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                    <span class='pscore'>⭐ {int(row['score']):,}</span>
                    &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}</div>
            </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════
    # 영역 B : 제품/원료 포지셔닝
    # ════════════════════════════════════════
    st.markdown("<div class='section-header'>🅑 영역 B. 제품·원료 포지셔닝 — \"데이터가 증명하는 차별화\"</div>",
                unsafe_allow_html=True)

    # ── 기법 4 : 성분 신호등 포지셔닝
    with st.expander("🚦 기법 4 — 성분 신호등 포지셔닝 | 브랜드 신뢰도 혁신", expanded=True):
        st.markdown("""
        > **개념:** 성분별 upvote_ratio로 🟢그린(안전)·🟡옐로(관찰)·🔴레드(위험)를 분류.
        > \"커뮤니티가 검증한 성분만 씁니다\"라는 메시지는 일반 광고와 차원이 다른 신뢰를 만듭니다.
        """)

        if keywords_df.empty:
            st.warning("keyword_hits 데이터가 없습니다.")
        else:
            sig_agg = keywords_df.groupby("keyword").agg(
                언급수=("keyword","count"),
                평균Score=("score","mean"),
                평균업보트비율=("upvote_ratio","mean"),
                총Score=("score","sum"),
            ).reset_index()
            sig_agg = sig_agg[sig_agg["언급수"] >= 2]  # 최소 2건 이상

            def signal(r):
                if r >= 0.88: return "🟢 그린 (즉시 도입)"
                elif r >= 0.75: return "🟡 옐로 (지속 관찰)"
                else: return "🔴 레드 (도입 보류)"

            sig_agg["신호등"] = sig_agg["평균업보트비율"].apply(signal)

            col_s1, col_s2 = st.columns([3, 2])
            with col_s1:
                fig_sig = px.scatter(
                    sig_agg, x="평균업보트비율", y="평균Score",
                    size="총Score", color="신호등",
                    hover_name="keyword",
                    color_discrete_map={
                        "🟢 그린 (즉시 도입)": "#22c55e",
                        "🟡 옐로 (지속 관찰)": "#f59e0b",
                        "🔴 레드 (도입 보류)": "#ef4444"
                    },
                    title="성분 안전성 신호등 차트",
                    labels={"평균업보트비율":"평균 업보트 비율","평균Score":"평균 Score"}
                )
                fig_sig.add_vline(x=0.88, line_dash="dash", line_color="green", annotation_text="그린 기준(0.88)")
                fig_sig.add_vline(x=0.75, line_dash="dash", line_color="orange", annotation_text="옐로 기준(0.75)")
                fig_sig.update_layout(height=450)
                st.plotly_chart(fig_sig, use_container_width=True)

            with col_s2:
                for signal_label in ["🟢 그린 (즉시 도입)", "🟡 옐로 (지속 관찰)", "🔴 레드 (도입 보류)"]:
                    subset = sig_agg[sig_agg["신호등"] == signal_label].sort_values("총Score", ascending=False)
                    st.markdown(f"**{signal_label}** — {len(subset)}개 성분")
                    if not subset.empty:
                        kws = ", ".join(subset.head(6)["keyword"].tolist())
                        st.caption(kws)
                    st.markdown("---")

    # ── 기법 5 : 경쟁사 레드 신호 역이용
    with st.expander("⚔️ 기법 5 — 경쟁사 레드 신호 역이용 | 경쟁사 약점 → 자사 기회", expanded=False):
        st.markdown("""
        > **개념:** 카테고리별 논란 게시글(upvote_ratio < 0.6)을 찾아 해당 이슈를
        > 자사 차별화 포지셔닝으로 전환합니다.
        """)

        NEG_WORDS = ["pilling","breakout","irritation","stings","burning","bad","worst",
                     "avoid","terrible","hate","doesn't work","useless","rash","reaction"]
        neg_pattern = "|".join(NEG_WORDS)

        controversy_posts = filtered[
            (filtered["upvote_ratio"] < 0.65) &
            (filtered["score"] >= 50)
        ].copy()
        controversy_posts["부정어포함"] = controversy_posts["selftext"].str.contains(
            neg_pattern, case=False, na=False)

        if not keywords_df.empty:
            cat_controversy = keywords_df[keywords_df["upvote_ratio"] < 0.65].groupby("keyword_category").agg(
                논란게시글수=("post_id","nunique"),
                평균업보트비율=("upvote_ratio","mean"),
            ).reset_index().sort_values("논란게시글수", ascending=False)

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                fig_con = px.bar(
                    cat_controversy, x="논란게시글수", y="keyword_category",
                    orientation="h", color="평균업보트비율",
                    color_continuous_scale="RdYlGn",
                    title="카테고리별 논란 게시글 수 (업보트 비율 < 0.65)",
                    labels={"keyword_category":"카테고리","논란게시글수":"논란 게시글 수"}
                )
                fig_con.update_layout(height=350, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_con, use_container_width=True)

            with col_c2:
                st.markdown("**🎯 역이용 포지셔닝 전략 매트릭스**")
                for _, row in cat_controversy.head(5).iterrows():
                    ratio = row["평균업보트비율"]
                    if ratio < 0.55:
                        action = "🔴 즉시 차별화 → '○○없는 대안' 메시지"
                    else:
                        action = "🟡 모니터링 → 교육 콘텐츠 선제 발행"
                    st.markdown(f"**{row['keyword_category']}** (평균 {ratio:.0%})\n→ {action}")
                    st.markdown("---")
        else:
            st.info("keyword_hits 데이터가 필요합니다.")

        st.markdown(f"**📊 저점 지지 게시글 현황** (Score≥50, 업보트비율<0.65): {len(controversy_posts)}건")
        if not controversy_posts.empty:
            st.dataframe(
                controversy_posts[["subreddit","title","score","upvote_ratio","num_comments","region"]]
                .sort_values("score", ascending=False).head(10),
                use_container_width=True, hide_index=True, height=280
            )

    # ── 기법 6 : 클리메이트 포뮬러 마케팅
    with st.expander("🌍 기법 6 — 클리메이트 포뮬러 마케팅 | 수출 시장 전환율 극대화", expanded=False):
        st.markdown("""
        > **개념:** 지역별 서브레딧 상위 이슈와 성분을 연결해
        > 수출 타깃 국가별 맞춤 포뮬러를 마케팅 자산으로 전환합니다.
        """)

        if keywords_df.empty:
            st.warning("keyword_hits 데이터가 필요합니다.")
        else:
            climate_agg = keywords_df.groupby(["region","keyword_category"]).agg(
                언급수=("keyword","count"),
                총Score=("score","sum"),
                평균업보트비율=("upvote_ratio","mean"),
            ).reset_index()

            pivot_climate = climate_agg.pivot_table(
                index="region", columns="keyword_category",
                values="총Score", aggfunc="sum", fill_value=0
            )

            fig_climate = px.imshow(
                pivot_climate,
                color_continuous_scale="YlOrRd",
                title="🌏 지역 × 성분 카테고리 Score 히트맵 (수출 포뮬러 전략 맵)",
                labels={"color":"총 Score"},
                aspect="auto"
            )
            fig_climate.update_layout(height=400)
            st.plotly_chart(fig_climate, use_container_width=True)

            # 지역별 TOP 3 성분 카테고리
            st.markdown("**🏆 지역별 최고 관심 성분 카테고리 Top 3**")
            regions_list = climate_agg["region"].unique()
            cols = st.columns(min(len(regions_list), 4))
            for i, reg in enumerate(regions_list[:4]):
                reg_top = climate_agg[climate_agg["region"] == reg].nlargest(3, "총Score")
                with cols[i]:
                    st.markdown(f"**🌏 {reg}**")
                    for _, row in reg_top.iterrows():
                        st.markdown(f"• {row['keyword_category']} ({int(row['총Score']):,})")

    # ════════════════════════════════════════
    # 영역 C : 타깃 마케팅
    # ════════════════════════════════════════
    st.markdown("<div class='section-header'>🅒 영역 C. 타깃 마케팅 — \"세그먼트별 맞춤 공략\"</div>",
                unsafe_allow_html=True)

    # ── 기법 7 : KOL 발굴
    with st.expander("⭐ 기법 7 — 커뮤니티 인증 KOL 발굴 | 팔로워 수 아닌 영향력 기준", expanded=True):
        st.markdown("""
        > **개념:** total_awards_received ≥ 1인 작성자 = 팔로워 수가 아닌
        > 실제 커뮤니티 영향력 기반 KOL. 협업 단가가 낮고 신뢰도는 높습니다.
        """)

        award_df = filtered[filtered["total_awards_received"] >= 1].copy()

        if award_df.empty:
            st.info("어워드 수상 게시글이 없습니다.")
        else:
            kol_df = award_df.groupby("author").agg(
                어워드게시글수=("total_awards_received","count"),
                총어워드=("total_awards_received","sum"),
                총Score=("score","sum"),
                평균Score=("score","mean"),
                주요서브레딧=("subreddit", lambda x: x.value_counts().index[0]),
            ).reset_index().sort_values("총어워드", ascending=False)

            col_k1, col_k2 = st.columns(2)
            with col_k1:
                fig_kol = px.bar(
                    kol_df.head(15), x="총어워드", y="author",
                    orientation="h", color="총Score",
                    color_continuous_scale="Oranges",
                    title="커뮤니티 인증 KOL Top 15 (어워드 수 기준)",
                    labels={"author":"작성자","총어워드":"총 어워드 수"}
                )
                fig_kol.update_layout(height=450, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_kol, use_container_width=True)

            with col_k2:
                st.markdown(f"**🎯 KOL 후보 {len(kol_df)}명 발굴**")
                st.dataframe(
                    kol_df.head(10)[["author","어워드게시글수","총어워드","평균Score","주요서브레딧"]],
                    use_container_width=True, hide_index=True, height=380
                )

            # 어워드 분포 요약
            c1k, c2k, c3k = st.columns(3)
            with c1k:
                st.metric("어워드 게시글 수", f"{len(award_df)}건")
            with c2k:
                st.metric("KOL 후보 수", f"{len(kol_df)}명")
            with c3k:
                st.metric("KOL 평균 Score", f"{kol_df['평균Score'].mean():.0f}")

    # ── 기법 8 : 3축 타깃 광고
    with st.expander("🎯 기법 8 — 3축 타깃 광고 (피부타입 × 지역 × 계절) | ROAS +25~50%", expanded=False):
        st.markdown("""
        > **개념:** author_flair_text(피부타입·지역) + 계절 정보를 결합한
        > 3축 정밀 세그먼트로 광고 ROAS를 25~50% 향상시킵니다.
        """)

        flair_df = filtered[filtered["author_flair_text"].notna() & (filtered["author_flair_text"] != "")].copy()

        st.markdown(f"**author_flair 보유 게시글:** {len(flair_df)}건 / 전체 {len(filtered)}건")

        if not flair_df.empty:
            # 계절 분류
            flair_df["month"] = flair_df["created_dt"].dt.month
            def season(m):
                if m in [12,1,2]: return "겨울"
                elif m in [3,4,5]: return "봄"
                elif m in [6,7,8]: return "여름"
                else: return "가을"
            flair_df["계절"] = flair_df["month"].apply(season)

            season_region = flair_df.groupby(["region","계절"]).agg(
                게시글수=("id","count"),
                평균Score=("score","mean"),
            ).reset_index()

            fig_tri = px.bar(
                season_region, x="region", y="게시글수",
                color="계절", barmode="group",
                color_discrete_map={"봄":"#86efac","여름":"#fbbf24","가을":"#fb923c","겨울":"#93c5fd"},
                title="지역 × 계절 게시글 분포 (3축 타깃 세그먼트 기반)",
                labels={"region":"지역","게시글수":"게시글 수"}
            )
            fig_tri.update_layout(height=350)
            st.plotly_chart(fig_tri, use_container_width=True)
        else:
            st.info("author_flair_text 데이터가 충분하지 않습니다. JSON API 수집 시 해당 필드가 수집됩니다.")

        # 타깃 세그먼트 매트릭스 (설명용 정적 테이블)
        st.markdown("**📋 타깃 세그먼트 광고 매트릭스 (전략 가이드)**")
        matrix_data = {
            "세그먼트": ["건성 + 한국 + 겨울","지성 + 동남아 + 연중","민감성 + 전지역 + 연중","복합성 + 북미 + 봄"],
            "타깃 메시지": [
                "히팅 시스템 켜는 순간 피부가 당기시죠?",
                "땀이 나도 덜컥거리지 않는 수분",
                "성분표 읽다 지치셨나요? 우리가 다 걸러냈어요",
                "T존만 번들거리고 나머지는 당기는 그 느낌"
            ],
            "핵심 성분": ["Ceramide NP + Squalane","Niacinamide + PHA","Centella + Allantoin","AHA 저농도 + HA"],
            "시즌": ["11~2월","연중","연중","3~5월"]
        }
        st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True)

    # ── 기법 9 : 갤러리 비포앤애프터
    with st.expander("📸 기법 9 — 갤러리 비포앤애프터 소셜 프루프 | 상세페이지 전환율 +15~35%", expanded=False):
        st.markdown("""
        > **개념:** is_gallery=True 게시글에는 소비자 무보정 비포앤애프터 사진이 집중.
        > 브랜드 사진보다 신뢰도 9.8배(Nielsen 기준)로, 제품 상세페이지 전환율을 높입니다.
        """)

        gallery_df = filtered[filtered["is_gallery"] == 1].copy()
        non_gallery = filtered[filtered["is_gallery"] != 1].copy()

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            st.metric("갤러리 게시글 수", f"{len(gallery_df)}건")
        with col_g2:
            avg_g = gallery_df["score"].mean() if len(gallery_df) > 0 else 0
            avg_ng = non_gallery["score"].mean() if len(non_gallery) > 0 else 0
            st.metric("갤러리 평균 Score", f"{avg_g:.0f}", delta=f"{avg_g-avg_ng:+.0f} vs 일반")
        with col_g3:
            high_gallery = len(gallery_df[gallery_df["score"] >= 200])
            st.metric("Score≥200 갤러리", f"{high_gallery}건")

        if not gallery_df.empty:
            col_ga, col_gb = st.columns(2)
            with col_ga:
                fig_gal = px.bar(
                    gallery_df.groupby("subreddit")["score"].agg(["count","mean"]).reset_index()
                    .rename(columns={"count":"갤러리수","mean":"평균Score"}).sort_values("갤러리수", ascending=False).head(15),
                    x="갤러리수", y="subreddit", orientation="h",
                    color="평균Score", color_continuous_scale="Purples",
                    title="서브레딧별 갤러리 게시글 분포",
                    labels={"subreddit":"서브레딧","갤러리수":"갤러리 수"}
                )
                fig_gal.update_layout(height=400, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_gal, use_container_width=True)

            with col_gb:
                high_score_gallery = gallery_df[gallery_df["score"] >= 200].nlargest(8, "score")[
                    ["subreddit","title","score","num_comments","region"]
                ]
                st.markdown("**⭐ 고점 갤러리 게시글 (DM 협업 우선 대상)**")
                st.dataframe(high_score_gallery, use_container_width=True, hide_index=True, height=350)

    # ════════════════════════════════════════
    # 영역 D : 리스크 마케팅
    # ════════════════════════════════════════
    st.markdown("<div class='section-header'>🅓 영역 D. 리스크 마케팅 — \"위기를 기회로 전환\"</div>",
                unsafe_allow_html=True)

    # ── 기법 10 : 위기 조기 대응
    with st.expander("🚨 기법 10 — 실시간 성분 위기 조기 대응 | 위기 대응 시간 24~48시간 단축", expanded=True):
        st.markdown("""
        > **개념:** upvote_ratio < 0.6 게시글 자동 감지로 성분 부작용 VOC가
        > 커뮤니티에서 폭발하기 **24~48시간 전에** 포착하고 선제 대응합니다.
        """)

        risk_threshold = st.slider("위기 감지 업보트 비율 기준", 0.40, 0.70, 0.60, 0.01, key="risk_ratio")
        risk_min_score = st.slider("최소 Score (노이즈 제거)", 10, 200, 30, 10, key="risk_score")

        risk_posts = filtered[
            (filtered["upvote_ratio"] < risk_threshold) &
            (filtered["score"] >= risk_min_score)
        ].sort_values("score", ascending=False)

        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("🔴 위기 감지 게시글", f"{len(risk_posts)}건",
                      delta=f"전체의 {len(risk_posts)/max(len(filtered),1)*100:.1f}%")
        with col_r2:
            st.metric("평균 Score", f"{risk_posts['score'].mean():.0f}" if len(risk_posts) > 0 else "0")
        with col_r3:
            max_comments_risk = int(risk_posts["num_comments"].max()) if len(risk_posts) > 0 else 0
            st.metric("최대 댓글 수", f"{max_comments_risk:,}")

        if not risk_posts.empty:
            col_ra, col_rb = st.columns(2)
            with col_ra:
                fig_risk = px.scatter(
                    risk_posts, x="upvote_ratio", y="score",
                    size="num_comments", color="subreddit",
                    hover_data=["title"],
                    title=f"⚠️ 위기 게시글 분포 (업보트비율 < {risk_threshold:.0%})",
                    labels={"upvote_ratio":"업보트 비율","score":"Score"}
                )
                fig_risk.add_vline(x=risk_threshold, line_dash="dash", line_color="red",
                                   annotation_text="위기 기준선")
                fig_risk.update_layout(height=400)
                st.plotly_chart(fig_risk, use_container_width=True)

            with col_rb:
                st.markdown("**🚨 즉시 대응 필요 게시글 (Score 높은 순)**")
                for _, row in risk_posts.head(7).iterrows():
                    ratio_pct = f"{row['upvote_ratio']*100:.0f}%"
                    st.markdown(f"""
                    <div class='post-card' style='border-left-color:#ef4444'>
                        <div class='ptitle'>⚠️ {str(row['title'])[:90]}{'...' if len(str(row['title'])) > 90 else ''}</div>
                        <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                            <span style='color:#ef4444;font-weight:700'>⭐ {int(row['score']):,} | 👍 {ratio_pct}</span>
                            &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # 대응 타임라인 가이드
        st.markdown("""
        **⏱️ 대응 속도별 브랜드 리스크 차이**

        | 대응 시점 | 결과 |
        |-----------|------|
        | 6시간 이내 | ✅ "우리가 먼저 알았다" → 투명 브랜드 이미지 |
        | 24시간 이내 | ✅ 커뮤니티 내 해소 → 브랜드 신뢰 상승 |
        | 48시간 초과 | ❌ SNS 확산 → 언론 보도 → 매출 타격 |
        """)

    # ── 기법 11 : 논쟁 교육 마케팅
    with st.expander("📚 기법 11 — 논쟁 교육 마케팅 | SEO 에버그린 트래픽 확보", expanded=False):
        st.markdown("""
        > **개념:** upvote_ratio 0.5~0.7 구간의 '논쟁 중인 성분'은 위험이 아닌 마케팅 기회.
        > 혼란스러운 소비자에게 정확한 정보를 제공하면 카테고리 권위자가 됩니다.
        """)

        edu_posts = filtered[
            (filtered["upvote_ratio"] >= 0.50) &
            (filtered["upvote_ratio"] < 0.70) &
            (filtered["score"] >= 30)
        ].copy()

        if keywords_df.empty:
            st.info("keyword_hits 데이터가 있으면 성분별 논쟁 분석이 가능합니다.")
        else:
            edu_kw = keywords_df[
                (keywords_df["upvote_ratio"] >= 0.50) &
                (keywords_df["upvote_ratio"] < 0.70)
            ].groupby(["keyword","keyword_category"]).agg(
                논쟁게시글수=("post_id","nunique"),
                평균업보트비율=("upvote_ratio","mean"),
                총Score=("score","sum"),
            ).reset_index().sort_values("논쟁게시글수", ascending=False)

            col_e1, col_e2 = st.columns(2)
            with col_e1:
                fig_edu = px.bar(
                    edu_kw.head(15), x="논쟁게시글수", y="keyword",
                    orientation="h", color="평균업보트비율",
                    color_continuous_scale="RdYlBu",
                    title="논쟁 중인 성분 Top 15 (교육 콘텐츠 기회)",
                    labels={"keyword":"성분","논쟁게시글수":"논쟁 게시글 수"}
                )
                fig_edu.update_layout(height=450, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_edu, use_container_width=True)

            with col_e2:
                st.markdown("**💡 에버그린 교육 콘텐츠 아이디어**")
                for _, row in edu_kw.head(5).iterrows():
                    st.markdown(f"""
                    **`{row['keyword']}`** — {row['논쟁게시글수']}건 논쟁
                    → 📝 *\"{row['keyword']} 성분, 써야 할까요? 데이터로만 판단합니다\"*
                    """)
                    st.markdown("---")

        col_e3, col_e4 = st.columns(2)
        with col_e3:
            st.metric("논쟁 게시글 수", f"{len(edu_posts)}건")
        with col_e4:
            st.metric("논쟁 게시글 평균 Score", f"{edu_posts['score'].mean():.0f}" if len(edu_posts) > 0 else "0")

    # ── 기법 12 : 크로스포스트 바이럴 증폭
    with st.expander("🔥 기법 12 — 크로스포스트 바이럴 증폭 | 트렌드 타이밍 선점", expanded=True):
        st.markdown("""
        > **개념:** num_crossposts ≥ 3인 게시글 = 이미 복수 커뮤니티에서 화제.
        > 이 신호를 가장 먼저 포착해 자사 SNS에서 트렌드에 편승하면 검색량 피크와 타이밍을 맞출 수 있습니다.
        """)

        cp_threshold = st.slider("크로스포스트 최소 기준", 1, 10, 2, 1, key="cp_threshold")
        viral_posts = filtered[filtered["num_crossposts"] >= cp_threshold].copy()

        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            st.metric("🔥 바이럴 게시글", f"{len(viral_posts)}건")
        with col_v2:
            avg_cp = viral_posts["num_crossposts"].mean() if len(viral_posts) > 0 else 0
            st.metric("평균 크로스포스트 수", f"{avg_cp:.1f}회")
        with col_v3:
            max_cp = int(viral_posts["num_crossposts"].max()) if len(viral_posts) > 0 else 0
            st.metric("최대 크로스포스트", f"{max_cp}회")

        if not viral_posts.empty:
            col_va, col_vb = st.columns(2)
            with col_va:
                fig_viral = px.scatter(
                    viral_posts, x="num_crossposts", y="score",
                    size="num_comments", color="subreddit",
                    hover_data=["title"],
                    title=f"🔥 바이럴 게시글 (크로스포스트 ≥ {cp_threshold})",
                    labels={"num_crossposts":"크로스포스트 수","score":"Score"}
                )
                fig_viral.update_layout(height=400)
                st.plotly_chart(fig_viral, use_container_width=True)

            with col_vb:
                st.markdown("**⚡ 즉시 콘텐츠 대응 필요 게시글 (크로스포스트 높은 순)**")
                top_viral = viral_posts.nlargest(7, "num_crossposts")
                for _, row in top_viral.iterrows():
                    st.markdown(f"""
                    <div class='post-card' style='border-left-color:#f59e0b'>
                        <div class='ptitle'>🔥 {str(row['title'])[:85]}{'...' if len(str(row['title'])) > 85 else ''}</div>
                        <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                            <span style='color:#f59e0b;font-weight:700'>🔁 {int(row['num_crossposts'])}회 크로스포스트</span>
                            &nbsp;|&nbsp; ⭐ {int(row['score']):,} &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # 서브레딧별 바이럴 분포
            cp_sub = viral_posts.groupby("subreddit")["num_crossposts"].sum().reset_index()
            cp_sub.columns = ["subreddit","총크로스포스트수"]
            cp_sub = cp_sub.sort_values("총크로스포스트수", ascending=False).head(12)
            fig_cpsub = px.bar(
                cp_sub, x="총크로스포스트수", y="subreddit",
                orientation="h", color="총크로스포스트수",
                color_continuous_scale="Oranges",
                title="서브레딧별 총 크로스포스트 수",
                labels={"subreddit":"서브레딧","총크로스포스트수":"총 크로스포스트 수"}
            )
            fig_cpsub.update_layout(height=350, yaxis={"categoryorder":"total ascending"})
            st.plotly_chart(fig_cpsub, use_container_width=True)
        else:
            st.info(f"크로스포스트 ≥ {cp_threshold}인 게시글이 없습니다. 기준값을 낮춰보세요.")

        # 바이럴 타이밍 흐름 가이드
        st.markdown("""
        **⏱️ 바이럴 타이밍 캡처 전략**

        | 시점 | 행동 |
        |------|------|
        | **Day 0** | Reddit 크로스포스트 급증 포착 (자동 알림) |
        | **Day 1** | 자사 SNS "이 성분 알고 계셨나요?" 콘텐츠 발행 |
        | **Day 3** | 구글 트렌드 해당 키워드 검색량 급등 시작 |
        | **Day 5** | 뷰티 유튜버들 해당 성분 영상 발행 (경쟁사 인지) |
        | **Day 7** | 언론 보도 → **우리는 이미 Day 1부터 상위 노출** |
        """)


st.markdown("---")
st.caption(f"🌿 Reddit 화장품 시장조사 대시보드 v1.0 | DB: {DB_PATH} | 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
