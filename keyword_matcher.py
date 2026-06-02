"""
keyword_matcher.py  v2.0 (English)
─────────────────────────────────────────────────────────────
Scans reddit_data.db posts for ingredient keywords and
writes results to the keyword_hits table.

Usage:
    python keyword_matcher.py

Notes:
    - Run AFTER reddit_import_json.py (keep DB up to date)
    - Re-run monthly after each data import (incremental update)
─────────────────────────────────────────────────────────────
"""

import sqlite3
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "reddit_data.db")

# ─────────────────────────────────────────────────────────────
# Ingredient keyword dictionary
# Structure: { "Category": { "Ingredient Name": ["search term 1", ...] } }
# All search terms are lowercase; partial-string matching is applied.
# ─────────────────────────────────────────────────────────────
INGREDIENT_KEYWORDS = {

    "Retinoids": {
        "Retinol":          ["retinol", "retinyl"],
        "Retinoid":         ["retinoid", "retin-a", "retinoic acid"],
        "Tretinoin":        ["tretinoin", "tret"],
        "Adapalene":        ["adapalene", "differin"],
    },

    "Vitamin C": {
        "Vitamin C":        ["vitamin c", "ascorbic acid", "l-ascorbic", "ascorbyl"],
        "Vitamin C Deriv.": ["magnesium ascorbyl", "ascorbyl glucoside", "sodium ascorbyl"],
    },

    "Niacinamide": {
        "Niacinamide":      ["niacinamide", "nicotinamide", "vit b3", "vitamin b3"],
    },

    "Peptides": {
        "Peptide":          ["peptide", "matrixyl", "argireline", "leuphasyl"],
        "Copper Peptide":   ["copper peptide", "ghk-cu", "ghk cu"],
    },

    "Exfoliants (AHA/BHA/PHA)": {
        "AHA":              ["aha", "alpha hydroxy", "glycolic acid", "lactic acid",
                             "mandelic acid", "malic acid"],
        "BHA":              ["bha", "beta hydroxy", "salicylic acid"],
        "PHA":              ["pha", "poly hydroxy", "gluconolactone", "lactobionic"],
    },

    "Humectants": {
        "Hyaluronic Acid":  ["hyaluronic acid", "sodium hyaluronate", "ha serum"],
    },

    "Barrier Repair": {
        "Ceramide":         ["ceramide", "ceramides"],
        "Squalane":         ["squalane", "squalene"],
        "Panthenol":        ["panthenol", "provitamin b5", "vitamin b5"],
    },

    "UV Protection": {
        "Sunscreen":        ["sunscreen", "sun screen", "spf", "uv filter", "sun protection"],
        "Zinc Oxide":       ["zinc oxide"],
        "Titanium Dioxide": ["titanium dioxide"],
        "Chemical Filter":  ["avobenzone", "oxybenzone", "octinoxate", "octocrylene",
                             "homosalate", "tinosorb"],
    },

    "Soothing": {
        "Centella":         ["centella", "cica", "asiaticoside", "madecassoside",
                             "centella asiatica"],
        "Allantoin":        ["allantoin"],
        "Azulene":          ["azulene", "chamomile", "bisabolol"],
    },

    "Antioxidants": {
        "Resveratrol":      ["resveratrol"],
        "CoQ10":            ["coenzyme q10", "coq10", "ubiquinone"],
    },

    "Structural": {
        "Collagen":         ["collagen", "hydrolyzed collagen"],
    },

    "Trends": {
        "Clean Beauty":     ["clean beauty", "clean skincare", "non-toxic",
                             "fragrance free", "fragrance-free"],
        "Vegan / CF":       ["vegan", "cruelty free", "cruelty-free"],
        "Natural":          ["natural ingredient", "organic", "plant-based", "botanical"],
        "K-Beauty":         ["k-beauty", "kbeauty", "korean beauty", "korean skincare"],
    },
}

# ─────────────────────────────────────────────────────────────
# DB schema
# ─────────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS keyword_hits (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id          INTEGER NOT NULL,
    keyword          TEXT NOT NULL,
    keyword_category TEXT NOT NULL,
    match_field      TEXT NOT NULL,
    matched_term     TEXT NOT NULL,
    matched_date     TEXT NOT NULL,
    UNIQUE(post_id, keyword, match_field)
);
"""
CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_kh_post_id  ON keyword_hits(post_id);
CREATE INDEX IF NOT EXISTS idx_kh_keyword  ON keyword_hits(keyword);
CREATE INDEX IF NOT EXISTS idx_kh_category ON keyword_hits(keyword_category);
"""


def build_pattern_map():
    """Build { ingredient_name: (category, [compiled patterns]) }."""
    pm = {}
    for category, kw_dict in INGREDIENT_KEYWORDS.items():
        for name, terms in kw_dict.items():
            pm[name] = (category, [re.compile(re.escape(t), re.IGNORECASE) for t in terms])
    return pm


def scan_text(text, pattern_map):
    """Return list of (name, category, matched_term) for all ingredient hits in text."""
    if not text:
        return []
    hits = []
    for name, (category, patterns) in pattern_map.items():
        for pat in patterns:
            m = pat.search(text)
            if m:
                hits.append((name, category, m.group(0).lower()))
                break
    return hits


def main():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print("  Reddit Keyword Matcher  v2.0")
    print(f"  Run time : {now_str}")
    print(f"  DB       : {DB_PATH}")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"\n[ERROR] DB file not found: {DB_PATH}")
        print("  Run reddit_import_json.py first.")
        input("\nPress any key to exit..."); return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.executescript(CREATE_TABLE_SQL + CREATE_INDEX_SQL)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM keyword_hits")
    before = cur.fetchone()[0]

    # Incremental: only scan posts not yet in keyword_hits
    cur.execute("""
        SELECT rp.id, rp.title, rp.selftext
        FROM reddit_posts rp
        WHERE rp.id NOT IN (SELECT DISTINCT post_id FROM keyword_hits)
    """)
    posts = cur.fetchall()

    if not posts:
        print(f"\n[INFO] No new posts to process. Existing keyword_hits: {before:,}")
        input("\nPress any key to exit..."); conn.close(); return

    print(f"\nPosts to process: {len(posts):,}  (skipping {before:,} already indexed)\n")

    pattern_map  = build_pattern_map()
    matched_date = datetime.now().strftime("%Y-%m-%d")
    total_hits   = 0
    dup_skip     = 0

    for idx, (post_id, title, selftext) in enumerate(posts, 1):
        if idx % 200 == 0:
            print(f"  Processing... {idx:,}/{len(posts):,} ({idx/len(posts)*100:.0f}%)")
        for field, text in [("title", title), ("selftext", selftext)]:
            for name, category, matched_term in scan_text(text, pattern_map):
                try:
                    cur.execute("""
                        INSERT INTO keyword_hits
                            (post_id, keyword, keyword_category,
                             match_field, matched_term, matched_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (post_id, name, category, field, matched_term, matched_date))
                    total_hits += 1
                except sqlite3.IntegrityError:
                    dup_skip += 1

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM keyword_hits")
    after = cur.fetchone()[0]

    print("\n" + "─" * 60)
    print(f"  Posts processed     : {len(posts):,}")
    print(f"  New keyword hits    : +{total_hits:,}")
    print(f"  Duplicates skipped  : {dup_skip:,}")
    print(f"  keyword_hits total  : {before:,} → {after:,}")

    print("\n  ── Top categories ──")
    cur.execute("""
        SELECT keyword_category, COUNT(*) as cnt
        FROM keyword_hits GROUP BY keyword_category ORDER BY cnt DESC LIMIT 10
    """)
    for cat, cnt in cur.fetchall():
        print(f"    {cat:<35} {cnt:>6} hits")

    print("\n  ── Top 10 ingredients ──")
    cur.execute("""
        SELECT kh.keyword, COUNT(*) as cnt, AVG(rp.score) as avg_score
        FROM keyword_hits kh JOIN reddit_posts rp ON kh.post_id = rp.id
        GROUP BY kh.keyword ORDER BY cnt DESC LIMIT 10
    """)
    print(f"  {'Ingredient':<25} {'Mentions':>8} {'Avg Score':>10}")
    print("  " + "─" * 45)
    for kw, cnt, avg in cur.fetchall():
        print(f"  {kw:<25} {cnt:>8}   {avg:>9.0f}")

    conn.close()
    print("\n" + "=" * 60)
    print("  Done! Restart dashboard.py to see the Ingredient Keywords tab.")
    input("  Press any key to exit...")


if __name__ == "__main__":
    main()
