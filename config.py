# ═══════════════════════════════════════════════════════════════════
# config.py — Constants, CSS, Region/Ingredient/VOC Mappings
# Reddit Beauty Market Intelligence Dashboard v7.0
# ═══════════════════════════════════════════════════════════════════

DB_PATH        = "reddit_data.db"
GDRIVE_FILE_ID = "1-nuBg81wfomyeCoqvF6JMURzSCBWM9Fz"

# ╔══════════════════════════════════════╗
# ║  SECTION: CSS  [LOCKED v7]          ║
# ╚══════════════════════════════════════╝
CSS = """
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

.sub-card {
    background: #f0f6ff; border-left: 4px solid #185FA5;
    border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 6px 0;
}
.sub-card .sc-name  { font-weight: 700; font-size: 0.95rem; color: #1a1a2e; }
.sub-card .sc-meta  { font-size: 0.8rem; color: #718096; margin-top: 3px; }

div[data-testid="stSidebar"] div[data-testid="stRadio"][aria-label="region_group_radio"] > div {
    gap: 6px;
    flex-direction: column;
}
/* ── Card base ── */
div[data-testid="stSidebar"] div[data-testid="stRadio"][aria-label="region_group_radio"] label {
    background: #e8edf2;
    border: 1.5px solid #cbd5e0;
    border-radius: 10px;
    padding: 9px 13px 9px 13px;
    cursor: pointer;
    width: 100%;
    margin: 0 !important;
    transition: all 0.15s ease;
    white-space: pre-wrap;
    font-size: 0.75rem;
    line-height: 1.5;
    color: #4a5568;
}
/* ── First line: large bold title ── */
div[data-testid="stSidebar"] div[data-testid="stRadio"][aria-label="region_group_radio"] label::first-line {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1a202c;
}
/* ── Hover ── */
div[data-testid="stSidebar"] div[data-testid="stRadio"][aria-label="region_group_radio"] label:hover {
    border-color: #185FA5;
    background: #d6e4f7;
    box-shadow: 0 2px 8px rgba(24,95,165,0.15);
}
/* ── Selected (active) ── */
div[data-testid="stSidebar"] div[data-testid="stRadio"][aria-label="region_group_radio"] label[data-selected="true"] {
    border-left: 4px solid #185FA5 !important;
    border-color: #185FA5 !important;
    background: #bfdbfe !important;
    color: #1e3a5f !important;
    box-shadow: 0 2px 10px rgba(24,95,165,0.22);
}
div[data-testid="stSidebar"] div[data-testid="stRadio"][aria-label="region_group_radio"] label[data-selected="true"]::first-line {
    font-weight: 800;
    color: #1e3a5f;
}
</style>
"""
# ══ END SECTION: CSS ════════════════════════════════════════════════

# ╔══════════════════════════════════════════════╗
# ║  SECTION: REGION_MAPPINGS  [LOCKED v7]      ║
# ╚══════════════════════════════════════════════╝
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

# Sidebar radio cards — (display label, internal key, icon, description)  ALL ENGLISH
REGION_CARDS = [
    ("All",                       "All",                       "🌐", "All collected posts"),
    ("Global · General",          "Global · General",          "🌍", "No region / skin-type restriction"),
    ("Global · Expert Consumer",  "Global · Expert Consumer",  "🔬", "Ingredient-focused, DIY, high-engagement"),
    ("Global · Specific Target",  "Global · Specific Target",  "🎯", "Age / income / interest-based segments"),
    ("Global · Skin Concerns",    "Global · Skin Concerns",    "💆", "Acne, oily, hormonal skin posts"),
    ("Western Markets (NA/EU)",   "Western Markets (NA/EU)",   "🌎", "NA · EU · Australia · Canada"),
    ("Asia-Pacific",              "Asia-Pacific",              "🌏", "Asia · India · SEA · Singapore"),
    ("Uncategorized",             "Uncategorized",             "📂", "Unclassified posts"),
]
# ══ END SECTION: REGION_MAPPINGS ════════════════════════════════════

# ╔══════════════════════════════════════════════╗
# ║  SECTION: INGREDIENT_DICTS  [LOCKED v7]     ║
# ╚══════════════════════════════════════════════╝
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
# ══ END SECTION: INGREDIENT_DICTS ═══════════════════════════════════

# ╔══════════════════════════════════════════════╗
# ║  SECTION: VOC_DICTS  [LOCKED v7]            ║
# ╚══════════════════════════════════════════════╝
COMPLAINT_DICT = {
    "Pilling / Balling Up":           ["pilling", "pills", "rub off", "ball up", "peeling off", "flakes off"],
    "Irritation / Breakouts":         ["irritation", "irritated", "stings", "burning", "breakout",
                                       "purge", "purging", "flare", "redness", "rash", "reaction", "allergic"],
    "Dryness / Tightness":            ["dry", "tight", "flaky", "dehydrated", "peeling", "dryness", "flaking"],
    "Oiliness / Excess Sebum":        ["oily", "greasy", "shiny", "sebum", "excess oil", "slippery"],
    "Clogged Pores / Blackheads":     ["clogged", "clogs", "pores", "blackhead", "blackheads",
                                       "congested", "congestion", "comedone"],
    "Hyperpigmentation / Dark Spots": ["hyperpigmentation", "dark spots", "melasma", "uneven",
                                       "discoloration", "pigmentation"],
    "Unpleasant Scent / Texture":     ["smell", "smells", "sticky", "tacky", "heavy texture",
                                       "thick", "goopy", "fragrance"],
    "No Visible Effect":              ["doesn't work", "no effect", "useless", "waste",
                                       "disappointed", "overhyped", "overrated"],
}

IMPROVEMENT_DICT = {
    "Formula Improvement":     ["wish it had", "needs more", "should add", "would be better with",
                                "improve formula", "better formula", "reformulate"],
    "Packaging Improvement":   ["packaging", "pump", "dispenser", "tube", "jar", "too small",
                                "bigger size", "refill", "travel size"],
    "Pricing Concerns":        ["too expensive", "price drop", "overpriced", "cheaper",
                                "affordable", "dupe", "budget friendly"],
    "Scent / Shade Options":   ["fragrance free", "no scent", "unscented", "color", "tint", "shade"],
    "Texture / Absorption":    ["takes too long", "absorb faster", "lighter texture",
                                "more lightweight", "less sticky", "lighter formula"],
    "Sensitive Skin Friendly": ["sensitive skin", "gentle", "non-irritating",
                                "hypoallergenic", "fragrance free version"],
}

PAIN_DICT = {
    "Pilling":           ["pilling", "pills", "rub off", "ball up"],
    "Irritation":        ["irritation", "stings", "burning", "breakout", "purge", "flare"],
    "Dryness":           ["dry", "tight", "flaky", "dehydrated", "peeling"],
    "Oiliness":          ["oily", "greasy", "shiny", "sebum"],
    "Clogged Pores":     ["clogged", "pores", "blackhead", "congested"],
    "Hyperpigmentation": ["hyperpigmentation", "dark spots", "melasma", "uneven"],
}

POSITIVE_DICT = {
    "Holy Grail / Repurchase": ["holy grail", "HG", "repurchase", "rebuy", "buy again",
                                "can't live without", "must have", "staple"],
    "Skin Transformation":     ["transformed", "game changer", "completely changed",
                                "best skin", "glowing", "cleared up", "love my skin"],
    "Ingredient Praise":       ["love this ingredient", "works so well", "incredible results",
                                "miracle ingredient", "obsessed with"],
    "Brand / Product Love":    ["love this brand", "favourite brand", "underrated",
                                "hidden gem", "worth the hype", "lives up to"],
    "Gentle / Sensitive OK":   ["gentle enough", "no reaction", "sensitive skin safe",
                                "doesn't break me out", "non-irritating for me"],
}
# ══ END SECTION: VOC_DICTS ══════════════════════════════════════════

# ╔══════════════════════════════════════════════╗
# ║  SECTION: KR_EN_MAPS  [LOCKED v7]           ║
# ╚══════════════════════════════════════════════╝
# Korean keyword_category → English  (from keyword_matcher.py DB values)
KEYWORD_CATEGORY_MAP = {
    # ── Suncare ──────────────────────────────────────────────
    "선케어":                   "Suncare",
    "자외선_선스크린":           "UV / Sunscreen",
    "황산화/기능성":             "Antioxidant",
    "향산화/기능성":             "Antioxidant",
    # ── Retinoids ────────────────────────────────────────────
    "기능성_레티노이드":         "Retinoid",
    "레티노이드":                "Retinoid",
    "레티놀":                   "Retinol",
    # ── Exfoliation ──────────────────────────────────────────
    "기능성_AHA_BHA_PHA":      "AHA / BHA / PHA",
    "AHA_BHA_PHA":             "AHA / BHA / PHA",
    "각질":                    "Exfoliation",
    # ── Niacinamide ──────────────────────────────────────────
    "기능성_나이아신아마이드":   "Niacinamide",
    "나이아신아마이드":          "Niacinamide",
    # ── Vitamin C ────────────────────────────────────────────
    "기능성_비타민C":           "Vitamin C",
    "비타민C 계열":             "Vitamin C",
    "비타민_C":                 "Vitamin C",
    # ── Moisturizing / Barrier ───────────────────────────────
    "보습_히알루론산":           "Hyaluronic Acid",
    "히알루론산 계열":           "Hyaluronic Acid",
    "세라마이드/장벽":           "Ceramide / Barrier",
    "보습_세라마이드":           "Ceramide / Barrier",
    "보습":                     "Moisturizing",
    "보습/수분":                 "Moisturizing",
    "보습_수분":                 "Moisturizing",
    "보습_판테놀":               "Panthenol",
    "보습_스쿠알렌":             "Squalane",
    # ── Peptide ──────────────────────────────────────────────
    "기능성_펩타이드":           "Peptide",
    "펩타이드":                  "Peptide",
    # ── Centella / Soothing ──────────────────────────────────
    "진정_센텔라":               "Centella / Soothing",
    "진정_아줄렌":               "Azulene",
    "진정_알란토인":             "Allantoin",
    "진정_올레인뷰티":           "Oleic / Soothing",
    # ── Cleansing ────────────────────────────────────────────
    "클렌징":                    "Cleansing",
    # ── Brightening ──────────────────────────────────────────
    "미백":                     "Brightening",
    # ── K-Beauty / Trend ─────────────────────────────────────
    "K-뷰티 특화":               "K-Beauty",
    "트렌드_한국화장품":         "K-Beauty Trend",
    "트렌드_레스베라트롤":       "Resveratrol",
    # ── Other ────────────────────────────────────────────────
    "자연유분산 제형":           "Natural Emulsion",
    "성분_플라겐":               "Collagen",
    "콜라겐":                   "Collagen",
}

# Korean keyword name → English  (deduplicates KR/EN pairs in DB)
KEYWORD_NAME_MAP = {
    "트레티노인":       "tretinoin",
    "선스크린":         "sunscreen",
    "나이아신아마이드": "niacinamide",
    "히알루론산":       "hyaluronic acid",
    "비타민C":          "vitamin c",
    "레티노이드":       "retinoid",
    "레티놀":           "retinol",
    "센텔라":           "centella",
    "세라마이드":       "ceramide",
    "클렌징":           "cleansing",
    "이중세안":         "double cleanse",
    "선케어":           "suncare",
    "펩타이드":         "peptide",
    "아젤라익애씨드":   "azelaic acid",
    "살리실릭애씨드":   "salicylic acid",
    "글리콜릭애씨드":   "glycolic acid",
    "스쿠알란":         "squalane",
    "시카":             "cica",
    "판테놀":           "panthenol",
    "알란토인":         "allantoin",
    "아줄렌":           "azulene",
    "구리펩타이드":     "copper peptide",
    "화학필터":         "chemical filter",
    "친연성분":         "natural ingredient",
    "레스베라트롤":     "resveratrol",
    "콜라겐":           "collagen",
    "올레인":           "oleic acid",
}
# ══ END SECTION: KR_EN_MAPS ═════════════════════════════════════════
