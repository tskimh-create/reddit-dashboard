"""
🌿 Reddit 화장품 시장조사 대시보드 v4.0
변경 이력:
  v2.0 - Google Drive DB 자동 다운로드
  v3.0 - 탭 순서 재정렬 + 소비자 VOC 분석 탭 추가
  v4.0 - [개선] permalink 실링크 연동 / 지역 그룹 필터 / 기본정보 탭 추가
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta
import os
import gdown

# ─────────────────────────────────────────
# 0. 페이지 기본 설정 ★ 반드시 첫 번째 Streamlit 명령 ★
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Reddit 화장품 인사이트",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# ★ Google Drive에서 DB 자동 다운로드
# ─────────────────────────────────────────
DB_PATH        = "reddit_data.db"
GDRIVE_FILE_ID = "1-nuBg81wfomyeCoqvF6JMURzSCBWM9Fz"   # ← 본인 파일 ID로 교체!

@st.cache_resource(show_spinner="📥 데이터베이스 로딩 중...")
def ensure_db():
    if not os.path.exists(DB_PATH):
        try:
            url = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}&export=download"
            gdown.download(url, DB_PATH, quiet=False)
        except Exception as e1:
            try:
                url2 = f"https://drive.google.com/file/d/{GDRIVE_FILE_ID}/view"
                gdown.download(url2, DB_PATH, quiet=False, fuzzy=True)
            except Exception as e2:
                st.error(f"""
                ❌ DB 다운로드 실패.

                **확인사항:**
                1. Google Drive 파일 공유 → '링크가 있는 모든 사용자'로 설정됐는지 확인
                2. 파일 ID가 정확한지 확인: `{GDRIVE_FILE_ID}`
                3. 오류 상세: {e2}
                """)
                st.stop()
    return DB_PATH

ensure_db()

# ─────────────────────────────────────────
# 공통 CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}
h1, h2, h3 { font-family: 'DM Serif Display', serif; }

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

.section-header {
    background: linear-gradient(90deg, #0f3460, #533483);
    color: white;
    padding: 10px 20px;
    border-radius: 8px;
    margin: 24px 0 16px 0;
    font-size: 1.1rem;
    font-weight: 600;
}

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

/* VOC 탭 전용 */
.voc-header {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    color: white;
    padding: 14px 20px;
    border-radius: 10px;
    margin-bottom: 16px;
}
.voc-header h3 { margin: 0; font-size: 1rem; font-family: 'DM Serif Display', serif; }
.voc-header p  { margin: 4px 0 0 0; opacity: .8; font-size: .85rem; }
.urs-card {
    background: #fff8f0;
    border-left: 4px solid #e94560;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 6px 0;
}
.urs-card .uc-title { font-weight: 600; font-size: 0.9rem; color: #1a1a2e; }
.urs-card .uc-meta  { font-size: 0.78rem; color: #718096; margin-top: 3px; }
.urs-card .uc-score { font-weight: 700; color: #e94560; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 1. DB 연결 & 데이터 로드
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)

        # 실제 테이블 컬럼 목록 확인 (구버전 DB 호환)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(reddit_posts)")
        existing_cols = {row[1] for row in cur.fetchall()}

        base_cols = """id, reddit_id, subreddit, title, selftext,
                   score, upvote_ratio, num_comments,
                   link_flair_text, author, author_flair_text,
                   total_awards_received, num_crossposts,
                   is_gallery, is_self,
                   created_utc, fetch_date, fetch_type,
                   region, priority_rank"""

        # permalink / url 컬럼이 없는 구버전 DB도 정상 작동
        extra = ", ".join(
            f"COALESCE({c}, '') as {c}"
            for c in ["permalink", "url"]
            if c in existing_cols
        )
        select_sql = f"SELECT {base_cols}{', ' + extra if extra else ''} FROM reddit_posts"

        posts = pd.read_sql_query(select_sql, conn)

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
        st.error(f"❌ DB 연결 오류: {e}")
        st.info(f"📂 `{DB_PATH}` 파일이 dashboard.py와 같은 폴더에 있는지 확인하세요.")
        st.stop()

posts_df, keywords_df, meta_df = load_data()

posts_df["fetch_date"] = pd.to_datetime(posts_df["fetch_date"], errors="coerce")
posts_df["created_dt"] = pd.to_datetime(posts_df["created_utc"], unit="s", errors="coerce")

# ─────────────────────────────────────────
# 지역 그룹 매핑 (region 컬럼 값 → 6개 상위 그룹)
# 실제 DB의 region 값에 맞게 키워드를 추가/수정하세요.
# ─────────────────────────────────────────
REGION_GROUP_MAP = {
    "글로벌·범용":          ["범용", "mass", "general", "다인종", "원료 데이터", "global_general", "표준"],
    "글로벌·전문소비자":    ["전문", "expert", "diy", "연구", "고관여", "가성비", "enthusiast"],
    "글로벌·특정타깃":      ["타깃", "target", "시니어", "senior", "고소득", "k-beauty", "미세연지", "온도"],
    "글로벌·피부고민":      ["피부고민", "skin_concern", "acne", "호르몬", "지성", "트러블", "여드름"],
    "북미/유럽·오세아니아": ["north", "europe", "usa", "uk", "australia", "canada", "western",
                            "서구", "북미", "유럽", "호주", "뉴질", "영국"],
    "아시아·태평양":        ["asia", "pacific", "korea", "japan", "china", "india",
                            "southeast", "singapore", "아시아", "태평양", "동남아", "인도", "싱가"],
}

def get_region_group(region_val):
    """region 값을 6개 그룹 중 하나로 분류. 매핑 불가 시 '미분류' 반환."""
    if pd.isna(region_val) or str(region_val).strip() == "":
        return "미분류"
    rv = str(region_val).lower()
    for group, keywords in REGION_GROUP_MAP.items():
        if any(kw.lower() in rv for kw in keywords):
            return group
    return "미분류"

posts_df["region_group"] = posts_df["region"].apply(get_region_group)

# permalink → 완전한 Reddit URL 생성
def make_reddit_url(row):
    """permalink 컬럼이 있으면 사용, 없으면 subreddit+reddit_id로 대체 URL 생성."""
    pl = row.get("permalink", "")
    if pl and str(pl) not in ("", "nan", "None"):
        return f"https://www.reddit.com{pl}"
    rid = row.get("reddit_id", "")
    sub = row.get("subreddit", "")
    if rid and sub:
        return f"https://www.reddit.com/r/{sub}/comments/{rid}/"
    return ""

posts_df["reddit_url"] = posts_df.apply(make_reddit_url, axis=1)

# ─────────────────────────────────────────
# 2. 사이드바 — 필터
# ─────────────────────────────────────────
st.sidebar.markdown("## 🌿 Reddit 인사이트\n**화장품 시장조사 대시보드**")
st.sidebar.markdown("---")

# ── 수집 기간 필터 ──────────────────────────────────
st.sidebar.markdown("**📅 수집 기간**")
period_mode = st.sidebar.radio("", ["전체(누계)", "기간 선택"], horizontal=True, label_visibility="collapsed")
if period_mode == "기간 선택":
    available_years  = sorted(posts_df["fetch_date"].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
    sel_year  = st.sidebar.selectbox("연도", available_years)
    available_months = ["전체"] + [f"{m:02d}" for m in sorted(
        posts_df[posts_df["fetch_date"].dt.year == sel_year]["fetch_date"].dt.month.dropna().unique().astype(int).tolist()
    )]
    sel_month = st.sidebar.selectbox("월", available_months)
else:
    sel_year = sel_month = None

# ── 지역 그룹 필터 ─────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("**🌏 지역 그룹**")
rg_options = ["전체"] + [g for g in REGION_GROUP_MAP.keys()] + ["미분류"]
sel_rgroup = st.sidebar.selectbox("지역 그룹 선택", rg_options, label_visibility="collapsed")

# 그룹 선택 후 하위 지역 필터
if sel_rgroup != "전체":
    region_in_group = sorted(
        posts_df[posts_df["region_group"] == sel_rgroup]["region"].dropna().unique().tolist()
    )
    region_options = ["전체"] + region_in_group
else:
    region_options = ["전체"] + sorted(posts_df["region"].dropna().unique().tolist())

sel_region = st.sidebar.selectbox("└ 세부 지역", region_options, label_visibility="visible")

# ── 서브레딧 필터 ───────────────────────────────────
st.sidebar.markdown("---")
subreddits = ["전체"] + sorted(posts_df["subreddit"].dropna().unique().tolist())
sel_sub = st.sidebar.selectbox("📌 서브레딧", subreddits)

# ── Score 필터 ──────────────────────────────────────
min_score = st.sidebar.slider("⭐ 최소 Score", 0, int(posts_df["score"].max() or 1000), 0, 10)

st.sidebar.markdown("---")
st.sidebar.caption(f"🗄️ DB: `{DB_PATH}`")
st.sidebar.caption(f"🕐 최근 수집: {posts_df['fetch_date'].max().strftime('%Y-%m-%d') if not posts_df.empty else '-'}")
st.sidebar.caption(f"📦 총 {len(posts_df):,}건 · {posts_df['subreddit'].nunique()}개 서브레딧")

# ── 필터 적용 ───────────────────────────────────────
filtered = posts_df.copy()
# 수집 기간
if period_mode == "기간 선택" and sel_year:
    filtered = filtered[filtered["fetch_date"].dt.year == sel_year]
    if sel_month != "전체":
        filtered = filtered[filtered["fetch_date"].dt.month == int(sel_month)]
# 지역 그룹
if sel_rgroup != "전체":
    filtered = filtered[filtered["region_group"] == sel_rgroup]
# 세부 지역
if sel_region != "전체":
    filtered = filtered[filtered["region"] == sel_region]
# 서브레딧
if sel_sub != "전체":
    filtered = filtered[filtered["subreddit"] == sel_sub]
# 최소 Score
filtered = filtered[filtered["score"] >= min_score]

# ─────────────────────────────────────────
# 3. 메인 헤더
# ─────────────────────────────────────────
st.markdown("# 🌿 Reddit 화장품 시장 인사이트 대시보드")
st.markdown(f"> 글로벌 뷰티 커뮤니티 **{len(posts_df['subreddit'].unique())}개 서브레딧** 데이터 분석 | 총 **{len(posts_df):,}건** 수집")

# ─────────────────────────────────────────
# 4. KPI 카드
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
# 5. 탭 구성 (v3.0 순서: 중요도 기준)
# ─────────────────────────────────────────
tab1, tab2, tab_voc, tab3, tab5, tab4, tab6 = st.tabs([
    "📊 트렌드 대시보드",
    "🧪 성분 키워드 인사이트",
    "💬 소비자 VOC 분석",
    "🌏 지역별 비교",
    "🎯 마케팅 기법 12",
    "📋 원본 데이터",
    "📌 기본정보",
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
        url       = row.get("reddit_url", "")
        title_str = str(row['title'])[:100] + ('...' if len(str(row['title'])) > 100 else '')
        title_html = (f'<a href="{url}" target="_blank" style="color:#1a1a2e;text-decoration:none;">'
                      f'{title_str}</a>') if url else title_str
        st.markdown(f"""
        <div class='post-card'>
            <div class='ptitle'>#{i+1} &nbsp; {title_html}</div>
            <div class='pmeta'>
                r/{row['subreddit']} &nbsp;|&nbsp;
                지역: {row['region']} ({row.get('region_group','')}) &nbsp;|&nbsp;
                <span class='pscore'>⭐ {int(row['score']):,}</span> &nbsp;|&nbsp;
                💬 {int(row['num_comments']):,} &nbsp;|&nbsp;
                👍 {ratio_pct}
                {f'&nbsp;|&nbsp; <a href="{url}" target="_blank" style="font-size:0.75rem;color:#718096;">원문 ↗</a>' if url else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
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
# TAB VOC : 소비자 VOC 분석
# (불만사항 · 개선요청 · URS 우선순위 매트릭스)
# ═══════════════════════════════════════════
with tab_voc:

    st.markdown("""
    <div class='voc-header'>
        <h3>💬 소비자 VOC 분석 — 불만사항 & 개선 요청</h3>
        <p>Reddit 게시글 제목·본문(selftext)에서 소비자 불만·개선 요청을 자동 감지·분류합니다.<br>
        <b>URS (User Requirement Specification)</b>: 소비자가 제품에 요구하는 기능·성능·특성을 체계적으로 정리한 사양서.
        하단의 우선순위 매트릭스로 즉시 개선 과제를 도출합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 불만 키워드 사전 ──────────────────────────────────
    COMPLAINT_DICT = {
        "밀림·뭉침": ["pilling", "pills", "rub off", "ball up", "peeling off", "flakes off"],
        "자극·트러블": ["irritation", "irritated", "stings", "burning", "breakout", "purge",
                   "purging", "flare", "redness", "rash", "reaction", "allergic"],
        "건조·당김": ["dry", "tight", "flaky", "dehydrated", "peeling", "dryness", "flaking"],
        "번들거림·과잉분비": ["oily", "greasy", "shiny", "sebum", "excess oil", "slippery"],
        "막힘·모공·블랙헤드": ["clogged", "clogs", "pores", "blackhead", "blackheads",
                          "congested", "congestion", "comedone"],
        "색소·잡티": ["hyperpigmentation", "dark spots", "melasma", "uneven",
                  "discoloration", "pigmentation"],
        "냄새·텍스처 불쾌": ["smell", "smells", "sticky", "tacky", "heavy texture",
                        "thick", "goopy", "fragrance"],
        "효과 없음": ["doesn't work", "no effect", "useless", "waste", "disappointed",
                  "overhyped", "overrated"],
    }

    # ── 개선 요청 키워드 사전 ─────────────────────────────
    IMPROVEMENT_DICT = {
        "성분 개선 요청": ["wish it had", "needs more", "should add", "would be better with",
                     "improve formula", "better formula", "reformulate"],
        "용량·패키징 개선": ["packaging", "pump", "dispenser", "tube", "jar", "too small",
                      "bigger size", "refill", "travel size"],
        "가격 개선 요청": ["too expensive", "price drop", "overpriced", "cheaper",
                     "affordable", "dupe", "budget friendly"],
        "향·색 개선": ["fragrance free", "no scent", "unscented", "color", "tint", "shade"],
        "발림성·흡수 개선": ["takes too long", "absorb faster", "lighter texture",
                       "more lightweight", "less sticky", "lighter formula"],
        "민감성 배려": ["sensitive skin", "gentle", "non-irritating",
                   "hypoallergenic", "fragrance free version"],
    }

    # ── 집계 함수 ────────────────────────────────────────
    def count_voc(df, kw_dict, label_col):
        results = []
        for cat, terms in kw_dict.items():
            pattern = "|".join(terms)
            m_title = df[df["title"].str.contains(pattern, case=False, na=False)]
            m_body  = df[df["selftext"].str.contains(pattern, case=False, na=False)]
            matched = pd.concat([m_title, m_body]).drop_duplicates(subset="id")
            results.append({
                label_col:        cat,
                "언급 게시글":    len(matched),
                "평균 Score":     round(matched["score"].mean(), 1) if len(matched) > 0 else 0,
                "총 댓글":        int(matched["num_comments"].sum()) if len(matched) > 0 else 0,
                "검색어(예시)":   ", ".join(terms[:3]) + ("…" if len(terms) > 3 else ""),
            })
        return pd.DataFrame(results).sort_values("언급 게시글", ascending=False)

    complaint_df = count_voc(filtered, COMPLAINT_DICT,  "불만 유형")
    improve_df   = count_voc(filtered, IMPROVEMENT_DICT, "개선 요청 유형")

    # ══ 섹션 1: 불만사항 ══════════════════════════════════
    st.markdown("<div class='section-header'>😤 불만사항 분석 (Complaints)</div>", unsafe_allow_html=True)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        fig_comp = px.bar(
            complaint_df, x="언급 게시글", y="불만 유형",
            orientation="h", color="평균 Score",
            color_continuous_scale="RdYlGn_r",
            title="불만 유형별 언급 게시글 수",
            labels={"불만 유형": "불만 유형", "언급 게시글": "게시글 수"}
        )
        fig_comp.update_layout(height=380, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_c2:
        st.dataframe(
            complaint_df[["불만 유형", "언급 게시글", "평균 Score", "총 댓글", "검색어(예시)"]],
            use_container_width=True, hide_index=True, height=350
        )

    # 상위 불만 유형 실제 게시글 샘플
    if not complaint_df.empty and complaint_df["언급 게시글"].max() > 0:
        top_comp_cat = complaint_df.iloc[0]["불만 유형"]
        top_terms    = COMPLAINT_DICT[top_comp_cat]
        pattern      = "|".join(top_terms)
        sample_comp  = filtered[
            filtered["title"].str.contains(pattern, case=False, na=False) |
            filtered["selftext"].str.contains(pattern, case=False, na=False)
        ].nlargest(5, "score")[["subreddit", "title", "score", "num_comments", "upvote_ratio"]]

        st.markdown(f"**💡 '{top_comp_cat}' 관련 고득점 게시글 — 카피라이팅 & 제품 개선 소스**")
        for _, row in sample_comp.iterrows():
            ratio_pct = f"{row['upvote_ratio']*100:.0f}%" if pd.notna(row['upvote_ratio']) else "-"
            st.markdown(f"""
            <div class='post-card'>
                <div class='ptitle'>📌 {row['title']}</div>
                <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                    <span class='pscore'>⭐ {int(row['score']):,}</span>
                    &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}
                    &nbsp;|&nbsp; 👍 {ratio_pct}
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("현재 필터 조건에서 감지된 불만 게시글이 없습니다. 필터를 조정해 보세요.")

    # ══ 섹션 2: 개선 요청 ════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>✅ 개선 요청 분석 (Improvement Requests)</div>", unsafe_allow_html=True)

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        fig_imp = px.bar(
            improve_df, x="언급 게시글", y="개선 요청 유형",
            orientation="h", color="평균 Score",
            color_continuous_scale="Blues",
            title="개선 요청 유형별 언급 게시글 수",
            labels={"개선 요청 유형": "요청 유형", "언급 게시글": "게시글 수"}
        )
        fig_imp.update_layout(height=340, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_imp, use_container_width=True)

    with col_i2:
        st.dataframe(
            improve_df[["개선 요청 유형", "언급 게시글", "평균 Score", "총 댓글"]],
            use_container_width=True, hide_index=True, height=310
        )

    # 상위 개선 요청 게시글 샘플
    if not improve_df.empty and improve_df["언급 게시글"].max() > 0:
        top_imp_cat = improve_df.iloc[0]["개선 요청 유형"]
        top_i_terms = IMPROVEMENT_DICT[top_imp_cat]
        pattern_i   = "|".join(top_i_terms)
        sample_imp  = filtered[
            filtered["title"].str.contains(pattern_i, case=False, na=False) |
            filtered["selftext"].str.contains(pattern_i, case=False, na=False)
        ].nlargest(3, "score")[["subreddit", "title", "score", "num_comments"]]

        st.markdown(f"**💡 '{top_imp_cat}' 관련 상위 게시글**")
        for _, row in sample_imp.iterrows():
            st.markdown(f"""
            <div class='post-card'>
                <div class='ptitle'>📌 {row['title']}</div>
                <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                    <span class='pscore'>⭐ {int(row['score']):,}</span>
                    &nbsp;|&nbsp; 💬 {int(row['num_comments']):,}
                </div>
            </div>""", unsafe_allow_html=True)

    # ══ 섹션 3: URS 우선순위 매트릭스 ═══════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>📋 URS 우선순위 매트릭스 — 제품 개선 과제 도출</div>", unsafe_allow_html=True)

    st.markdown("""
    > **URS 매트릭스 계산 방식:** `우선순위 점수 = 언급 게시글 수 × 평균 Score`
    > 언급이 많고 참여도(Score)도 높은 불만일수록 소비자 체감 강도가 강한 핵심 개선 과제입니다.
    """)

    complaint_df["우선순위 점수"] = (
        complaint_df["언급 게시글"] * complaint_df["평균 Score"]
    ).round(0)

    col_u1, col_u2 = st.columns([3, 2])
    with col_u1:
        fig_urs = px.scatter(
            complaint_df,
            x="언급 게시글", y="평균 Score",
            size="우선순위 점수",
            text="불만 유형",
            color="우선순위 점수",
            color_continuous_scale="RdYlGn_r",
            title="URS 우선순위 매트릭스 (크기 = 우선순위 점수)",
            labels={
                "언급 게시글": "언급 빈도 (게시글 수)",
                "평균 Score":  "참여도 (평균 Score)"
            }
        )
        fig_urs.update_traces(textposition="top center", textfont_size=9)
        fig_urs.update_layout(height=420)
        st.plotly_chart(fig_urs, use_container_width=True)

    with col_u2:
        top_urs = (
            complaint_df
            .nlargest(5, "우선순위 점수")
            [["불만 유형", "언급 게시글", "평균 Score", "우선순위 점수"]]
            .reset_index(drop=True)
        )
        top_urs.index += 1

        st.markdown("**🔴 즉시 개선 필요 — Top 5**")
        for i, row in top_urs.iterrows():
            label = "🔴" if i == 1 else ("🟠" if i == 2 else "🟡")
            st.markdown(f"""
            <div class='urs-card'>
                <div class='uc-title'>{label} {i}위. {row['불만 유형']}</div>
                <div class='uc-meta'>
                    언급 {int(row['언급 게시글'])}건 &nbsp;|&nbsp;
                    평균 Score <span class='uc-score'>{row['평균 Score']:,.0f}</span>
                </div>
                <div class='uc-meta'>우선순위 점수: <b>{row['우선순위 점수']:,.0f}</b></div>
            </div>
            """, unsafe_allow_html=True)

    # 불만 + 개선 합산 요약 메트릭
    st.markdown("<br>", unsafe_allow_html=True)
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    total_comp_posts = int(complaint_df["언급 게시글"].sum())
    total_imp_posts  = int(improve_df["언급 게시글"].sum())
    with col_m1:
        st.metric("감지된 불만 게시글", f"{total_comp_posts:,}건")
    with col_m2:
        st.metric("불만 유형 수", f"{len(complaint_df)}개")
    with col_m3:
        st.metric("개선 요청 게시글", f"{total_imp_posts:,}건")
    with col_m4:
        st.metric("개선 요청 유형 수", f"{len(improve_df)}개")

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

    st.markdown("<div class='section-header'>🗺️ 지역 × 서브레딧 활동 히트맵</div>", unsafe_allow_html=True)

    try:
        pivot = filtered.pivot_table(
            index="region", columns="subreddit",
            values="score", aggfunc="sum", fill_value=0
        )
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

    st.markdown("<div class='section-header'>🅐 영역 A. 콘텐츠 마케팅 — \"소비자가 쓰는 말로 말하라\"</div>",
                unsafe_allow_html=True)

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

            fig_voc = px.bar(
                voc_df.groupby("subreddit").size().reset_index(name="건수").sort_values("건수", ascending=False),
                x="subreddit", y="건수", color="건수",
                color_continuous_scale="Blues",
                title=f"VOC 소스 게시글 서브레딧 분포 (Score≥{voc_threshold_score}, 비율≥{voc_threshold_ratio:.0%})"
            )
            fig_voc.update_layout(height=300)
            st.plotly_chart(fig_voc, use_container_width=True)

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
                )
                fig_trend2.update_layout(height=550)
                st.plotly_chart(fig_trend2, use_container_width=True)

    with st.expander("💔 기법 3 — 언메트 니즈 스토리텔링 | 브랜드 공감도 극대화", expanded=False):
        st.markdown("""
        > **개념:** 소비자들이 selftext에 털어놓는 해결 안 되는 불편함을 찾아
        > 제품 탄생 스토리로 역전시킵니다.
        > 💡 **팁:** 'VOC 분석' 탭의 불만사항 데이터와 함께 활용하세요.
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

        if not pain_df.empty and pain_df["언급 게시글 수"].max() > 0:
            top_pain  = pain_df.iloc[0]["고민 유형"]
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

    st.markdown("<div class='section-header'>🅑 영역 B. 제품·원료 포지셔닝 — \"데이터가 증명하는 차별화\"</div>",
                unsafe_allow_html=True)

    with st.expander("🚦 기법 4 — 성분 신호등 포지셔닝 | 브랜드 신뢰도 혁신", expanded=True):
        st.markdown("""
        > **개념:** 성분별 upvote_ratio로 🟢그린(안전)·🟡옐로(관찰)·🔴레드(위험)를 분류.
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
            sig_agg = sig_agg[sig_agg["언급수"] >= 2]

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
                        st.caption(", ".join(subset.head(6)["keyword"].tolist()))
                    st.markdown("---")

    with st.expander("⚔️ 기법 5 — 경쟁사 레드 신호 역이용 | 경쟁사 약점 → 자사 기회", expanded=False):
        NEG_WORDS = ["pilling","breakout","irritation","stings","burning","bad","worst",
                     "avoid","terrible","hate","doesn't work","useless","rash","reaction"]
        neg_pattern = "|".join(NEG_WORDS)

        controversy_posts = filtered[
            (filtered["upvote_ratio"] < 0.65) &
            (filtered["score"] >= 50)
        ].copy()
        controversy_posts["부정어포함"] = controversy_posts["selftext"].str.contains(
            neg_pattern, case=False, na=False)

        st.markdown(f"**📊 저점 지지 게시글 현황** (Score≥50, 업보트비율<0.65): {len(controversy_posts)}건")
        if not controversy_posts.empty:
            st.dataframe(
                controversy_posts[["subreddit","title","score","upvote_ratio","num_comments","region"]]
                .sort_values("score", ascending=False).head(10),
                use_container_width=True, hide_index=True, height=280
            )

    with st.expander("🌍 기법 6 — 클리메이트 포뮬러 마케팅 | 수출 시장 전환율 극대화", expanded=False):
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
                title="🌏 지역 × 성분 카테고리 Score 히트맵",
                aspect="auto"
            )
            fig_climate.update_layout(height=400)
            st.plotly_chart(fig_climate, use_container_width=True)

    st.markdown("<div class='section-header'>🅒 영역 C. 타깃 마케팅 — \"세그먼트별 맞춤 공략\"</div>",
                unsafe_allow_html=True)

    with st.expander("⭐ 기법 7 — 커뮤니티 인증 KOL 발굴 | 팔로워 수 아닌 영향력 기준", expanded=True):
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
                    title="커뮤니티 인증 KOL Top 15",
                )
                fig_kol.update_layout(height=450, yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig_kol, use_container_width=True)
            with col_k2:
                st.dataframe(
                    kol_df.head(10)[["author","어워드게시글수","총어워드","평균Score","주요서브레딧"]],
                    use_container_width=True, hide_index=True, height=380
                )

    with st.expander("🎯 기법 8 — 3축 타깃 광고 (피부타입 × 지역 × 계절) | ROAS +25~50%", expanded=False):
        flair_df = filtered[filtered["author_flair_text"].notna() & (filtered["author_flair_text"] != "")].copy()
        st.markdown(f"**author_flair 보유 게시글:** {len(flair_df)}건 / 전체 {len(filtered)}건")

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

    with st.expander("📸 기법 9 — 갤러리 비포앤애프터 소셜 프루프 | 상세페이지 전환율 +15~35%", expanded=False):
        gallery_df  = filtered[filtered["is_gallery"] == 1].copy()
        non_gallery = filtered[filtered["is_gallery"] != 1].copy()

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            st.metric("갤러리 게시글 수", f"{len(gallery_df)}건")
        with col_g2:
            avg_g  = gallery_df["score"].mean() if len(gallery_df) > 0 else 0
            avg_ng = non_gallery["score"].mean() if len(non_gallery) > 0 else 0
            st.metric("갤러리 평균 Score", f"{avg_g:.0f}", delta=f"{avg_g-avg_ng:+.0f} vs 일반")
        with col_g3:
            st.metric("Score≥200 갤러리", f"{len(gallery_df[gallery_df['score'] >= 200])}건")

    st.markdown("<div class='section-header'>🅓 영역 D. 리스크 마케팅 — \"위기를 기회로 전환\"</div>",
                unsafe_allow_html=True)

    with st.expander("🚨 기법 10 — 실시간 성분 위기 조기 대응 | 위기 대응 시간 24~48시간 단축", expanded=True):
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
            st.metric("최대 댓글 수", f"{int(risk_posts['num_comments'].max()):,}" if len(risk_posts) > 0 else "0")

        if not risk_posts.empty:
            col_ra, col_rb = st.columns(2)
            with col_ra:
                fig_risk = px.scatter(
                    risk_posts, x="upvote_ratio", y="score",
                    size="num_comments", color="subreddit",
                    hover_data=["title"],
                    title=f"⚠️ 위기 게시글 분포 (업보트비율 < {risk_threshold:.0%})",
                )
                fig_risk.add_vline(x=risk_threshold, line_dash="dash", line_color="red")
                fig_risk.update_layout(height=400)
                st.plotly_chart(fig_risk, use_container_width=True)
            with col_rb:
                st.markdown("**🚨 즉시 대응 필요 게시글 (Score 높은 순)**")
                for _, row in risk_posts.head(7).iterrows():
                    ratio_pct = f"{row['upvote_ratio']*100:.0f}%"
                    st.markdown(f"""
                    <div class='post-card' style='border-left-color:#ef4444'>
                        <div class='ptitle'>⚠️ {str(row['title'])[:90]}</div>
                        <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                            <span style='color:#ef4444;font-weight:700'>⭐ {int(row['score']):,} | 👍 {ratio_pct}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    with st.expander("📚 기법 11 — 논쟁 교육 마케팅 | SEO 에버그린 트래픽 확보", expanded=False):
        edu_posts = filtered[
            (filtered["upvote_ratio"] >= 0.50) &
            (filtered["upvote_ratio"] < 0.70) &
            (filtered["score"] >= 30)
        ].copy()

        col_e3, col_e4 = st.columns(2)
        with col_e3:
            st.metric("논쟁 게시글 수", f"{len(edu_posts)}건")
        with col_e4:
            st.metric("논쟁 게시글 평균 Score", f"{edu_posts['score'].mean():.0f}" if len(edu_posts) > 0 else "0")

    with st.expander("🔥 기법 12 — 크로스포스트 바이럴 증폭 | 트렌드 타이밍 선점", expanded=True):
        cp_threshold = st.slider("크로스포스트 최소 기준", 1, 10, 2, 1, key="cp_threshold")
        viral_posts  = filtered[filtered["num_crossposts"] >= cp_threshold].copy()

        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            st.metric("🔥 바이럴 게시글", f"{len(viral_posts)}건")
        with col_v2:
            st.metric("평균 크로스포스트 수", f"{viral_posts['num_crossposts'].mean():.1f}회" if len(viral_posts) > 0 else "0")
        with col_v3:
            st.metric("최대 크로스포스트", f"{int(viral_posts['num_crossposts'].max())}회" if len(viral_posts) > 0 else "0")

        if not viral_posts.empty:
            st.markdown("**⚡ 즉시 콘텐츠 대응 필요 게시글 (크로스포스트 높은 순)**")
            for _, row in viral_posts.nlargest(7, "num_crossposts").iterrows():
                st.markdown(f"""
                <div class='post-card' style='border-left-color:#f59e0b'>
                    <div class='ptitle'>🔥 {str(row['title'])[:85]}</div>
                    <div class='pmeta'>r/{row['subreddit']} &nbsp;|&nbsp;
                        <span style='color:#f59e0b;font-weight:700'>🔁 {int(row['num_crossposts'])}회 크로스포스트</span>
                        &nbsp;|&nbsp; ⭐ {int(row['score']):,}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB 4 : 원본 데이터
# ═══════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>📋 수집 데이터 테이블</div>", unsafe_allow_html=True)

    cols_show = [c for c in [
        "subreddit", "title", "score", "num_comments",
        "upvote_ratio", "region", "region_group", "fetch_type", "fetch_date",
        "link_flair_text", "author", "reddit_url"
    ] if c in filtered.columns]

    # 제목에 링크 포함한 표시용 컬럼 추가
    df_show = filtered[cols_show].sort_values("score", ascending=False).copy()
    if "reddit_url" in df_show.columns:
        df_show["원문 링크"] = df_show["reddit_url"].apply(
            lambda u: f"[↗ 원문]({u})" if u else ""
        )
        df_show = df_show.drop(columns=["reddit_url"])

    st.dataframe(df_show, use_container_width=True, height=500)

    csv_cols = [c for c in cols_show if c != "reddit_url"]
    csv = filtered[csv_cols].to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ CSV 다운로드",
        data=csv,
        file_name=f"reddit_cosmetics_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    if not meta_df.empty:
        st.markdown("<div class='section-header'>📌 서브레딧 메타 정보</div>", unsafe_allow_html=True)
        st.dataframe(meta_df, use_container_width=True, height=300)

# ═══════════════════════════════════════════
# TAB 6 : 기본정보
# ═══════════════════════════════════════════
with tab6:

    # ── KPI 요약 ────────────────────────────────────────
    st.markdown("<div class='section-header'>🗄️ DB 기본 정보</div>", unsafe_allow_html=True)

    db_size_str = "-"
    if os.path.exists(DB_PATH):
        db_bytes = os.path.getsize(DB_PATH)
        db_size_str = f"{db_bytes / 1024:.1f} KB" if db_bytes < 1024*1024 else f"{db_bytes / 1024 / 1024:.2f} MB"

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("총 수집 건수",    f"{len(posts_df):,}건")
    with m2:
        st.metric("서브레딧 수",     f"{posts_df['subreddit'].nunique()}개")
    with m3:
        first_dt = posts_df["fetch_date"].min()
        st.metric("최초 수집일", first_dt.strftime("%Y-%m-%d") if pd.notna(first_dt) else "-")
    with m4:
        last_dt = posts_df["fetch_date"].max()
        st.metric("최근 수집일", last_dt.strftime("%Y-%m-%d") if pd.notna(last_dt) else "-")
    with m5:
        st.metric("DB 파일 크기", db_size_str)

    fetch_type_counts = posts_df["fetch_type"].value_counts()
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.metric("주간 수집",  f"{fetch_type_counts.get('weekly', 0):,}건")
    with mc2:
        st.metric("월간 수집",  f"{fetch_type_counts.get('monthly', 0):,}건")
    with mc3:
        st.metric("미분류 지역", f"{(posts_df['region_group'] == '미분류').sum():,}건")

    # ── 서브레딧별 수집 현황 ─────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>📋 서브레딧별 수집 현황</div>", unsafe_allow_html=True)

    sub_status = (
        posts_df.groupby("subreddit")
        .agg(
            수집건수=("id", "count"),
            최근수집일=("fetch_date", "max"),
            평균Score=("score", "mean"),
            지역그룹=("region_group", lambda x: x.value_counts().index[0] if len(x) > 0 else "-"),
        )
        .reset_index()
        .sort_values("수집건수", ascending=False)
    )
    sub_status["최근수집일"] = sub_status["최근수집일"].dt.strftime("%Y-%m-%d")
    sub_status["평균Score"]  = sub_status["평균Score"].round(1)

    st.dataframe(sub_status, use_container_width=True, hide_index=True, height=400)

    # ── 수집 트렌드 (월별) ───────────────────────────────
    st.markdown("<div class='section-header'>📈 수집 트렌드 (월별)</div>", unsafe_allow_html=True)

    posts_df["ym"] = posts_df["fetch_date"].dt.to_period("M").astype(str)
    monthly = (
        posts_df.groupby(["ym", "fetch_type"])
        .size()
        .reset_index(name="건수")
        .sort_values("ym")
    )

    if not monthly.empty:
        fig_trend = px.bar(
            monthly, x="ym", y="건수", color="fetch_type",
            barmode="stack",
            color_discrete_map={"weekly": "#185FA5", "monthly": "#1D9E75"},
            title="월별 수집 건수 (수집 유형별 누적)",
            labels={"ym": "연월", "건수": "수집 건수", "fetch_type": "수집 유형"}
        )
        fig_trend.update_layout(height=320, xaxis_tickangle=-30)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("수집 날짜 데이터가 없습니다.")

    # ── 지역 그룹 분포 ───────────────────────────────────
    col_rg1, col_rg2 = st.columns(2)

    with col_rg1:
        st.markdown("<div class='section-header'>🌏 지역 그룹 분포</div>", unsafe_allow_html=True)
        rg_cnt = posts_df["region_group"].value_counts().reset_index()
        rg_cnt.columns = ["지역 그룹", "게시글 수"]
        fig_rg = px.pie(
            rg_cnt, values="게시글 수", names="지역 그룹",
            title="지역 그룹별 게시글 비중",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_rg.update_layout(height=350)
        st.plotly_chart(fig_rg, use_container_width=True)

    with col_rg2:
        st.markdown("<div class='section-header'>📊 지역 그룹 상세</div>", unsafe_allow_html=True)
        rg_detail = (
            posts_df.groupby("region_group")
            .agg(
                게시글수=("id", "count"),
                서브레딧수=("subreddit", "nunique"),
                평균Score=("score", "mean"),
            )
            .reset_index()
            .sort_values("게시글수", ascending=False)
        )
        rg_detail["평균Score"] = rg_detail["평균Score"].round(1)
        st.dataframe(rg_detail, use_container_width=True, hide_index=True, height=320)

# ─────────────────────────────────────────
st.markdown("---")
st.caption(f"🌿 Reddit 화장품 시장조사 대시보드 v4.0 | DB: {DB_PATH} | 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
