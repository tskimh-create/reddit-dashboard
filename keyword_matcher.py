"""
🧪 키워드 매칭 모듈 — keyword_matcher.py  (v1.1 수정판)
─────────────────────────────────────────
역할: reddit_posts DB에 이미 수집된 게시글에서
      성분/원료 키워드를 찾아 keyword_hits 테이블에 저장

수정 내역 (v1.1):
  - 기존 setup_db.py로 생성된 keyword_hits 테이블에
    matched_term 컬럼이 없을 경우 자동으로 추가

사용법:
    python keyword_matcher.py
"""

import sqlite3
import re
from datetime import datetime

DB_PATH = "reddit_data.db"

# ─────────────────────────────────────────
# 화장품 원료 키워드 사전
# 카테고리 → { 한국어명: [영어 검색어 목록] }
# ─────────────────────────────────────────
INGREDIENT_KEYWORDS = {

    # ── 레티노이드
    "레티노이드": {
        "retinol":        ["retinol", "0.1% retinol", "0.5% retinol", "1% retinol"],
        "tretinoin":      ["tretinoin", "retin-a", "retin a", "retinoid"],
        "retinal":        ["retinal", "retinaldehyde"],
        "bakuchiol":      ["bakuchiol"],
    },

    # ── 비타민C
    "비타민C 계열": {
        "vitamin_c":      ["vitamin c", "vit c", "ascorbic acid", "l-ascorbic acid",
                           "ascorbyl glucoside", "sodium ascorbyl phosphate",
                           "magnesium ascorbyl phosphate"],
        "tetrahexyldecyl":["thd ascorbate", "tetrahexyldecyl ascorbate"],
    },

    # ── 나이아신아마이드
    "나이아신아마이드": {
        "niacinamide":    ["niacinamide", "niacin", "vitamin b3", "vit b3", "nicotinamide"],
    },

    # ── 히알루론산
    "히알루론산 계열": {
        "hyaluronic_acid":["hyaluronic acid", "ha serum", "sodium hyaluronate",
                           "hyaluronan"],
        "polyglutamic":   ["polyglutamic acid", "pga"],
    },

    # ── 펩타이드
    "펩타이드": {
        "peptide":        ["peptide", "peptides", "matrixyl", "argireline",
                           "palmitoyl", "copper peptide", "ghk-cu"],
    },

    # ── AHA/BHA/PHA
    "AHA/BHA/PHA": {
        "glycolic_acid":  ["glycolic acid", "aha", "alpha hydroxy acid"],
        "salicylic_acid": ["salicylic acid", "bha", "beta hydroxy acid"],
        "lactic_acid":    ["lactic acid"],
        "mandelic_acid":  ["mandelic acid"],
        "pha":            ["pha", "gluconolactone", "lactobionic acid"],
    },

    # ── 세라마이드
    "세라마이드/장벽": {
        "ceramide":       ["ceramide", "ceramides", "skin barrier",
                           "moisture barrier", "lipid barrier"],
        "cholesterol":    ["cholesterol", "fatty acid"],
    },

    # ── 선케어
    "선케어": {
        "sunscreen":      ["sunscreen", "sun screen", "spf", "uv filter",
                           "sunblock", "sun protection"],
        "zinc_oxide":     ["zinc oxide"],
        "titanium_diox":  ["titanium dioxide"],
        "uva_uvb":        ["uva", "uvb", "broad spectrum", "pa+++"],
    },

    # ── 보습/수분
    "보습/수분": {
        "squalane":       ["squalane", "squalene"],
        "glycerin":       ["glycerin", "glycerol"],
        "panthenol":      ["panthenol", "pro-vitamin b5", "vitamin b5", "vit b5"],
        "allantoin":      ["allantoin"],
        "urea":           ["urea"],
    },

    # ── 항산화/기타
    "항산화/기능성": {
        "coenzyme_q10":   ["coenzyme q10", "coq10", "ubiquinone"],
        "resveratrol":    ["resveratrol"],
        "azelaic_acid":   ["azelaic acid"],
        "tranexamic_acid":["tranexamic acid", "txa"],
        "kojic_acid":     ["kojic acid"],
        "nrf2":           ["nrf2", "antioxidant"],
    },

    # ── K-뷰티 특화
    "K-뷰티 특화": {
        "snail":          ["snail mucin", "snail filtrate", "snail secretion"],
        "centella":       ["centella", "cica", "tiger grass", "madecassoside",
                           "asiaticoside"],
        "green_tea":      ["green tea", "egcg", "epigallocatechin"],
        "propolis":       ["propolis"],
        "ginseng":        ["ginseng", "panax ginseng"],
        "mugwort":        ["mugwort", "artemisia"],
        "rice":           ["rice water", "rice extract", "fermented rice"],
    },

    # ── 클렌징
    "클렌징": {
        "double_cleanse": ["double cleanse", "double cleansing"],
        "micellar":       ["micellar water", "micellar"],
        "oil_cleanse":    ["cleansing oil", "oil cleanser"],
    },
}

# ─────────────────────────────────────────
# 키워드 검색 함수
# ─────────────────────────────────────────
def find_keywords(text: str, search_terms: list) -> list:
    """텍스트에서 키워드 검색 → 매칭된 실제 단어 목록 반환"""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for term in search_terms:
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(term)
    return found

# ─────────────────────────────────────────
# 메인 실행 함수
# ─────────────────────────────────────────
def run_matcher():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── ① keyword_hits 테이블 없으면 새로 생성
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keyword_hits (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id          INTEGER REFERENCES reddit_posts(id),
            keyword          TEXT,
            keyword_category TEXT,
            match_field      TEXT,
            matched_date     TEXT
        )
    """)
    conn.commit()

    # ── ② matched_term 컬럼이 없으면 자동 추가 (기존 DB 호환)
    existing_cols = [row[1] for row in cur.execute("PRAGMA table_info(keyword_hits)").fetchall()]
    if "matched_term" not in existing_cols:
        cur.execute("ALTER TABLE keyword_hits ADD COLUMN matched_term TEXT")
        conn.commit()
        print("ℹ️  matched_term 컬럼을 keyword_hits 테이블에 추가했습니다.")

    # ── ③ 기존 매칭 삭제 (재실행 시 중복 방지)
    cur.execute("DELETE FROM keyword_hits")
    conn.commit()

    # ── ④ 게시글 로드
    posts = cur.execute(
        "SELECT id, title, selftext FROM reddit_posts"
    ).fetchall()
    print(f"🔍 총 {len(posts)}건 게시글 키워드 매칭 시작...")

    today        = datetime.now().strftime("%Y-%m-%d")
    insert_count = 0
    rows_to_insert = []

    for post_id, title, selftext in posts:
        title_text = title    or ""
        body_text  = selftext or ""

        for category, kw_dict in INGREDIENT_KEYWORDS.items():
            for kw_name, search_terms in kw_dict.items():

                # 제목 우선 검색
                hits_title = find_keywords(title_text, search_terms)
                if hits_title:
                    for term in hits_title:
                        rows_to_insert.append(
                            (post_id, kw_name, category, "title", term, today)
                        )
                        insert_count += 1
                else:
                    # 본문 검색 (제목 히트 없을 때만)
                    hits_body = find_keywords(body_text, search_terms)
                    for term in hits_body:
                        rows_to_insert.append(
                            (post_id, kw_name, category, "body", term, today)
                        )
                        insert_count += 1

    # ── ⑤ 일괄 저장 (executemany로 속도 향상)
    cur.executemany("""
        INSERT INTO keyword_hits
            (post_id, keyword, keyword_category, match_field, matched_term, matched_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows_to_insert)
    conn.commit()
    conn.close()

    print(f"✅ 키워드 매칭 완료! 총 {insert_count}건 → keyword_hits 테이블 저장")
    print("   → 대시보드를 새로고침하면 '🧪 성분 키워드 인사이트' 탭이 활성화됩니다.")


if __name__ == "__main__":
    run_matcher()