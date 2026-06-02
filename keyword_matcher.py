"""
keyword_matcher.py  v1.0
─────────────────────────────────────────────────────────────
reddit_data.db의 reddit_posts 테이블을 스캔하여
성분 키워드를 자동 감지하고 keyword_hits 테이블에 저장합니다.

실행 방법:
    python keyword_matcher.py

주의:
    - reddit_import_json.py 실행 후 실행하세요 (DB 최신 상태 유지)
    - 매월 수집 후 재실행하면 증분 업데이트됩니다 (중복 방지)
─────────────────────────────────────────────────────────────
"""

import sqlite3
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "reddit_data.db")

# ─────────────────────────────────────────────────────────────
# ★ 성분 키워드 사전
#   구조: { "카테고리": { "한글명": ["영문 검색어1", "영문 검색어2", ...] } }
#   검색어는 소문자 기준. 부분 문자열 매칭 적용.
# ─────────────────────────────────────────────────────────────
INGREDIENT_KEYWORDS = {

    "기능성_레티노이드": {
        "레티놀":       ["retinol", "retinyl"],
        "레티노이드":   ["retinoid", "retin-a", "retinoic acid"],
        "트레티노인":   ["tretinoin", "tret"],
        "아다팔렌":     ["adapalene", "differin"],
    },

    "기능성_비타민C": {
        "비타민C":      ["vitamin c", "ascorbic acid", "l-ascorbic", "ascorbyl"],
        "비타민C유도체":["magnesium ascorbyl", "ascorbyl glucoside", "sodium ascorbyl"],
    },

    "기능성_나이아신아마이드": {
        "나이아신아마이드": ["niacinamide", "nicotinamide", "vit b3", "vitamin b3"],
    },

    "기능성_펩타이드": {
        "펩타이드":     ["peptide", "matrixyl", "argireline", "leuphasyl"],
        "구리펩타이드": ["copper peptide", "ghk-cu", "ghk cu"],
    },

    "기능성_AHA_BHA_PHA": {
        "AHA":          ["aha", "alpha hydroxy", "glycolic acid", "lactic acid", "mandelic acid", "malic acid"],
        "BHA":          ["bha", "beta hydroxy", "salicylic acid"],
        "PHA":          ["pha", "poly hydroxy", "gluconolactone", "lactobionic"],
    },

    "보습_히알루론산": {
        "히알루론산":   ["hyaluronic acid", "sodium hyaluronate", "ha serum"],
    },

    "보습_세라마이드": {
        "세라마이드":   ["ceramide", "ceramides"],
    },

    "보습_스쿠알란": {
        "스쿠알란":     ["squalane", "squalene"],
    },

    "보습_판테놀": {
        "판테놀":       ["panthenol", "provitamin b5", "vitamin b5"],
    },

    "자외선_선스크린": {
        "선스크린":     ["sunscreen", "sun screen", "spf", "uv filter", "sun protection"],
        "징크옥사이드": ["zinc oxide"],
        "티타늄다이옥사이드": ["titanium dioxide"],
        "화학필터":     ["avobenzone", "oxybenzone", "octinoxate", "octocrylene", "homosalate", "tinosorb"],
    },

    "진정_센텔라": {
        "센텔라":       ["centella", "cica", "asiaticoside", "madecassoside", "centella asiatica"],
    },

    "진정_알란토인": {
        "알란토인":     ["allantoin"],
    },

    "진정_아줄렌": {
        "아줄렌":       ["azulene", "chamomile", "bisabolol"],
    },

    "항산화_레스베라트롤": {
        "레스베라트롤": ["resveratrol"],
    },

    "항산화_코엔자임Q10": {
        "코엔자임Q10":  ["coenzyme q10", "coq10", "ubiquinone"],
    },

    "성분_콜라겐": {
        "콜라겐":       ["collagen", "hydrolyzed collagen"],
    },

    "트렌드_클린뷰티": {
        "클린뷰티":     ["clean beauty", "clean skincare", "non-toxic", "fragrance free", "fragrance-free"],
        "비건":         ["vegan", "cruelty free", "cruelty-free"],
        "천연성분":     ["natural ingredient", "organic", "plant-based", "botanical"],
    },

    "트렌드_한국화장품": {
        "K뷰티":        ["k-beauty", "kbeauty", "korean beauty", "korean skincare"],
        "선크림":       ["korean sunscreen", "k-sunscreen"],
    },
}

# ─────────────────────────────────────────────────────────────
# DB 초기화: keyword_hits 테이블 생성
# ─────────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS keyword_hits (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id        INTEGER NOT NULL,
    keyword        TEXT NOT NULL,
    keyword_category TEXT NOT NULL,
    match_field    TEXT NOT NULL,
    matched_term   TEXT NOT NULL,
    matched_date   TEXT NOT NULL,
    UNIQUE(post_id, keyword, match_field)
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_kh_post_id  ON keyword_hits(post_id);
CREATE INDEX IF NOT EXISTS idx_kh_keyword  ON keyword_hits(keyword);
CREATE INDEX IF NOT EXISTS idx_kh_category ON keyword_hits(keyword_category);
"""


def build_pattern_map():
    """키워드 사전 → { 한글명: (카테고리, [검색어 패턴]) } 변환."""
    pm = {}
    for category, kw_dict in INGREDIENT_KEYWORDS.items():
        for kor_name, terms in kw_dict.items():
            pm[kor_name] = (category, [re.compile(re.escape(t), re.IGNORECASE) for t in terms])
    return pm


def scan_text(text, pattern_map):
    """텍스트에서 매칭되는 키워드 목록 반환 → [(kor_name, category, matched_term), ...]"""
    if not text:
        return []
    hits = []
    for kor_name, (category, patterns) in pattern_map.items():
        for pat in patterns:
            m = pat.search(text)
            if m:
                hits.append((kor_name, category, m.group(0).lower()))
                break  # 같은 키워드는 첫 매칭만
    return hits


def main():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print("  Reddit Keyword Matcher  v1.0")
    print(f"  실행일시 : {now_str}")
    print(f"  DB       : {DB_PATH}")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"\n[ERROR] DB 파일 없음: {DB_PATH}")
        print("  reddit_import_json.py 를 먼저 실행하세요.")
        input("\n아무 키나 누르세요..."); return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # 테이블·인덱스 생성
    cur.executescript(CREATE_TABLE_SQL + CREATE_INDEX_SQL)
    conn.commit()

    # 기존 keyword_hits 건수
    cur.execute("SELECT COUNT(*) FROM keyword_hits")
    before = cur.fetchone()[0]

    # 아직 처리되지 않은 posts만 스캔 (증분)
    # → keyword_hits에 post_id가 없는 게시글 대상
    cur.execute("""
        SELECT rp.id, rp.title, rp.selftext
        FROM reddit_posts rp
        WHERE rp.id NOT IN (SELECT DISTINCT post_id FROM keyword_hits)
    """)
    posts = cur.fetchall()

    if not posts:
        print("\n[INFO] 새로 처리할 게시글이 없습니다. (모두 기분석됨)")
        print(f"       기존 keyword_hits: {before:,}건")
        input("\n아무 키나 누르세요..."); conn.close(); return

    print(f"\n처리 대상 게시글: {len(posts):,}건  (기존 {before:,}건 스킵)\n")

    pattern_map = build_pattern_map()
    matched_date = datetime.now().strftime("%Y-%m-%d")

    total_hits = 0
    dup_skip   = 0

    for idx, (post_id, title, selftext) in enumerate(posts, 1):
        if idx % 200 == 0:
            print(f"  처리 중... {idx:,}/{len(posts):,}건 ({idx/len(posts)*100:.0f}%)")

        for field, text in [("title", title), ("selftext", selftext)]:
            for kor_name, category, matched_term in scan_text(text, pattern_map):
                try:
                    cur.execute("""
                        INSERT INTO keyword_hits
                            (post_id, keyword, keyword_category, match_field, matched_term, matched_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (post_id, kor_name, category, field, matched_term, matched_date))
                    total_hits += 1
                except sqlite3.IntegrityError:
                    dup_skip += 1  # UNIQUE 제약으로 중복 스킵

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM keyword_hits")
    after = cur.fetchone()[0]

    # 결과 요약
    print("\n" + "─" * 60)
    print(f"  처리 완료 게시글 : {len(posts):,}건")
    print(f"  신규 키워드 히트 : +{total_hits:,}건")
    print(f"  중복 스킵        : {dup_skip:,}건")
    print(f"  keyword_hits 합계: {before:,} → {after:,}건")

    # 카테고리별 TOP 요약
    print("\n  ── 카테고리별 히트 현황 ──")
    cur.execute("""
        SELECT keyword_category, COUNT(*) as cnt
        FROM keyword_hits
        GROUP BY keyword_category
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for cat, cnt in cur.fetchall():
        print(f"    {cat:<30} {cnt:>6}건")

    print("\n  ── 키워드별 TOP 10 ──")
    cur.execute("""
        SELECT kh.keyword, COUNT(*) as cnt, AVG(rp.score) as avg_score
        FROM keyword_hits kh
        JOIN reddit_posts rp ON kh.post_id = rp.id
        GROUP BY kh.keyword
        ORDER BY cnt DESC
        LIMIT 10
    """)
    print(f"  {'키워드':<20} {'언급수':>6} {'평균Score':>10}")
    print("  " + "─" * 40)
    for kw, cnt, avg in cur.fetchall():
        print(f"  {kw:<20} {cnt:>6}건  {avg:>9.0f}")

    conn.close()
    print("\n" + "=" * 60)
    print("  완료! dashboard.py 를 재실행하면 성분 탭이 활성화됩니다.")
    input("  아무 키나 누르세요...")


if __name__ == "__main__":
    main()
