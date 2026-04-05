"""
Central configuration constants for the Widby scoring engine.
All values sourced from Algo Spec V1.1, §16 unless noted otherwise.
"""

# --- AIO Impact (Algo Spec V1.1, §16) ---
# Source: Seer Interactive (2025), SISTRIX
AIO_CTR_REDUCTION = 0.59

# Source: Ahrefs 146M SERP study
INTENT_AIO_RATES: dict[str, float] = {
    "transactional": 0.021,
    "commercial": 0.043,
    "informational": 0.436,
}

# Source: Ahrefs — local/visit-in-person queries
LOCAL_QUERY_AIO_RATE = 0.079

# --- M4 Keyword Expansion ---
M4_ALLOWED_INTENTS: tuple[str, ...] = ("transactional", "commercial", "informational")
M4_ALLOWED_TIERS: tuple[int, ...] = (1, 2, 3)
M4_ALLOWED_CONFIDENCE: tuple[str, ...] = ("high", "medium", "low")
M4_ALLOWED_AIO_RISK: tuple[str, ...] = ("low", "moderate", "high")
M4_ALLOWED_SOURCES: tuple[str, ...] = ("input", "llm", "dataforseo_suggestions", "merged")

# Confidence mapping from LLM-vs-DFS overlap ratio.
M4_CONFIDENCE_LOW_THRESHOLD = 0.30
M4_CONFIDENCE_HIGH_THRESHOLD = 0.60

# Deterministic ordering for final keyword output.
M4_INTENT_PRIORITY: dict[str, int] = {
    "transactional": 0,
    "commercial": 1,
    "informational": 2,
}

# --- Scoring Calibration ---
# To be calibrated from first 50 reports
MEDIAN_LOCAL_SERVICE_CPC = 5.00

# Composite score weights (fixed components)
FIXED_WEIGHTS: dict[str, float] = {
    "demand": 0.25,
    "monetization": 0.20,
    "ai_resilience": 0.15,
}

# Strategy profile weights (Algo Spec V1.1, §3.4)
# organic_weight + local_weight always sums to 0.35
STRATEGY_PROFILES: dict[str, dict[str, float]] = {
    "organic_first": {"organic_weight": 0.25, "local_weight": 0.10},
    "balanced": {"organic_weight": 0.15, "local_weight": 0.20},
    "local_dominant": {"organic_weight": 0.05, "local_weight": 0.35},
}

# --- DataForSEO (Algo Spec V1.1, §14) ---
DFS_BASE_URL = "https://api.dataforseo.com/v3/"
DFS_DEFAULT_LANGUAGE_CODE = "en"
DFS_DEFAULT_LOCATION_NAME = "United States"
DFS_RATE_LIMIT = 2000  # calls per minute
DFS_CACHE_TTL = 86400  # 24 hours in seconds
DFS_MAX_RETRIES = 3
DFS_QUEUE_POLL_INTERVAL = 5  # seconds between queue polls
DFS_QUEUE_MAX_WAIT = 300  # 5 minutes max for standard queue

# Per-endpoint approximate costs (USD)
DFS_COSTS: dict[str, float] = {
    "serp_organic": 0.0006,
    "serp_maps": 0.0006,
    "keyword_volume": 0.05,
    "keyword_suggestions": 0.05,
    "business_listings": 0.01,
    "google_reviews": 0.005,
    "google_my_business_info": 0.004,
    "backlinks_summary": 0.002,
    "lighthouse": 0.002,
}

# --- LLM (M3 spec) ---
DEFAULT_MODEL = "claude-sonnet-4-20250514"
CLASSIFICATION_MODEL = "claude-haiku-4-5-20251001"

# --- SERP Feature Keys (Algo Spec V1.1, §14) ---
SERP_FEATURES_TO_TRACK: dict[str, str] = {
    "ai_overview": "aio_present",
    "local_pack": "local_pack_present",
    "featured_snippet": "snippet_present",
    "people_also_ask": "paa_present",
    "top_stories": "news_present",
    "ads_top": "ads_top_present",
    "local_services_ads": "lsa_present",
    "knowledge_panel": "kp_present",
}

# --- Aggregator Domains (Algo Spec V1.1, §6.6) ---
KNOWN_AGGREGATORS: set[str] = {
    "yelp.com",
    "homeadvisor.com",
    "angi.com",
    "angieslist.com",
    "thumbtack.com",
    "bbb.org",
    "bark.com",
    "houzz.com",
    "expertise.com",
    "chamberofcommerce.com",
    "mapquest.com",
    "yellowpages.com",
    "superpages.com",
    "manta.com",
    "nextdoor.com",
    "porch.com",
    "networx.com",
    "topratedlocal.com",
    "buildzoom.com",
    "fixr.com",
}

# --- Region Definitions (M1) ---
REGIONS: dict[str, list[str]] = {
    "Southwest": ["AZ", "NM", "NV", "UT", "CO"],
    "Southeast": ["FL", "GA", "AL", "SC", "NC", "TN", "MS", "LA", "AR", "KY", "VA", "WV"],
    "Northeast": ["NY", "NJ", "PA", "CT", "MA", "RI", "NH", "VT", "ME"],
    "Midwest": ["IL", "OH", "MI", "IN", "WI", "MN", "IA", "MO", "KS", "NE", "SD", "ND"],
    "West": ["CA", "OR", "WA", "ID", "MT", "WY", "HI", "AK"],
    "South Central": ["TX", "OK"],
    "Mid-Atlantic": ["MD", "DE", "DC"],
}
