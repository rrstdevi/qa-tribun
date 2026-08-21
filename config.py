# config.py

# ==========================================
# CONFIGURATION SETTINGS
# ==========================================

API_KEY = "c2c32d37d870c155cfc9ee62d03db1dd38c980cde42f8cf20113719bf23a9e36"

# 1. API Testing Parameters
# These are passed to the backend API and used by the validator
MMR_LAMBDA = 0.7  # Maps to lambda_param in the API
SIMILARITY_THRESHOLD = 60.0 # Maps to similarity_threshold in the API
SIMILARITY_ANOMALY_GAP = 25.0 # Max allowed gap between ratio and token similarity before flagged as WARNING

# 2. Client ID Configuration
# Mode can be "range" or "list". 
# Format will always be padded to 3 digits (e.g. test-001)
CLIENT_ID_CONFIG = {
    "mode": "list", # "range" or "list"
    # "range_start": 500,
    # "range_end": 999,
    "list": ["test-9118"] # Only used if mode is "list"
}

# 930 - 949 

# 3. Article Recommendation Scenarios
# You can define multiple test cases here to test different contexts for the /article endpoint
ARTICLE_TEST_SCENARIOS = [
    {
        # "scenario_id": "SCN-001",
        # "scenario_name": "Berita Padang",
        # "item_id": "175149",
        # "site": "padang",
        # "article_title": "GM for a Day 2026 Dibuka di Santika Premiere Padang, Anak-anak Berpeluang Jadi GM Sehari"
        "scenario_id": "SCN-004",
        "scenario_name": "Berita Cuaca",
        "item_id": "176823",
        "site": "padang",
        "article_title": "Breaking News: Hujan Deras Guyur Padang, Sungai Meluap hingga Merendam Rumah Warga di Sungai Lareh"
    }
]

# 4. Latency Settings
LATENCY_THRESHOLD_MS = 200
LATENCY_TOLERANCE_MS = 300

# 4. Composition Rules
HOMEPAGE_MAX_ARTICLES = 20
HOMEPAGE_MAX_PERSONALIZED = 10
ARTICLE_TOTAL = 8
ARTICLE_SIMILARITY = 7
ARTICLE_TOP_NEWS = 1

# 5. Recency Rules (in days) - for Homepage
RECENCY_TOP_NEWS_MAX_DAYS = 3
RECENCY_PERSONALIZED_MAX_DAYS = 8

# 5.1 Recency Rules (in hours) - for Article
RECENCY_TOP_NEWS_MAX_HOURS = 6
RECENCY_PERSONALIZED_MAX_HOURS = 6

# 6. Blacklist Regex
BLACKLIST_REGEX_PATTERN = r"(?i)(lirik lagu|chord|kunci jawaban|zodiak|lowongan kerja)"

# 7. File Paths
# These paths are relative to the 'Data Product' root directory
IP_DATA_CSV_PATH = "IP address data.csv"
OUTPUT_DIR = "output/"

# 8. Report Batch Settings
BATCH_SIZE = 10

# 9. Validation Settings
# Endpoints to validate. Options: "/homepage", "/article"
VALIDATE_ENDPOINTS = ["/homepage", "/article", "/latest_feed"]

# Endpoints to test during test.py
TEST_ARTICLE_ENDPOINT = True
TEST_HOMEPAGE_ENDPOINT = True
TEST_HEADER_TAG_ENDPOINT = True
TEST_LATEST_FEED_ENDPOINT = True

#==========CONFIGURATION END==========#

#==========================

#2. CONFIGURATION SETTINGS FOR HEADER/TAG

#=========================
#0. Endpoint & Auth untuk Header/Tag
HEADER_TAG_BASE_URL = "https://stg-reco-app.tribundata.com" 
HEADER_TAG_ENDPOINT_PATH = "/api/v3/header/tag"
HEADER_TAG_CLIENT_ID = "test-009"

#1. Trending tags mode
#Exactly backend API only supports 'popular' mode for trending tags, this parameter is required
PAGE_MODE = "popular"

#2. Rekomendasi tags mode
#list of tags that will be return max 20. parameter is optional
NUM_RECOMMENDATIONS = 20

#3. Web Domain (source url).  parameter is optional
SOURCE_URL = "web domain"

#4. This is an optional parameter that specifies the minimum similarity score required for two tags to be considered duplicates. 
# If the parameter is not provided, the system uses the default value of 60.0.
SIMILARITY_SCORE = 60.0

#5. Blacklist Tag untuk Endpoint Header/Tag
BLACKLISTED_TAGS = [
    "ai optimized", "running news", "runningnews", "sripokucom",
    "lainnya", "viral", "virallokal", "lowongan kerja", "loker", "lowongan",
    "breakingnews", "breaking news", "kebakaran", "berita viral", "redeem",
    "suryacoid", "banjarmasinpostcoid", "pos-kupang.com", "poskupangcom",
    "serambinewscom", "serambinews", "poskupang", "kunci jawaban",
    "free fire", "ml", "mobile legend", "freefire",
    "ganja", "sabu", "heroin", "kokain", "ekstasi", "LSD", "morfin",
    "opium", "shabu", "cimeng",
    "seks", "seksual", "hubungan intim", "intim", "hubungan seksual", "hubungan badan",
    "pemerkosaan", "setubuhi", "hubungan suami istri", "hubungan biologis",
    "pencabulan", "cabul", "pelecehan"
]

#==========================
#3. CONFIGURATION SETTINGS FOR LATEST FEED
#=========================
LATEST_FEED_BASE_URL = "https://stg-reco-app.tribundata.com" 
LATEST_FEED_ENDPOINT_PATH = "/api/v3/homepage/recommendation"
LATEST_FEED_PAGE_MODE = "latest"

LATEST_FEED_TEST_SCENARIOS = [
    {
        "tc_id": "TC-001,004,005,014,015",
        "name": "Core Behavior (Sort, Dedup, Latency, No-Recency)",
        "num_recommendation": 20,
        "source_url": None,
        "note": "Validasi sorting, dedup, duplicate ID, latency, dan no-recency-limit"
    },
    {
        "tc_id": "TC-002",
        "name": "Article Count Limit (num_recommendation=10)",
        "num_recommendation": 10,
        "source_url": None,
        "note": "Validasi count <= 10"
    },
    {
        "tc_id": "TC-003",
        "name": "Default Article Count (no num_recommendation param)",
        "num_recommendation": None,
        "source_url": None,
        "note": "Validasi default max 20 artikel"
    },
    {
        "tc_id": "TC-013",
        "name": "Source Handling - Web (source_url filled)",
        "num_recommendation": 20,
        "source_url": "https://www.tribunnews.com",
        "note": "Untuk dibandingkan struktur keys vs Mobile (tanpa source_url)"
    }
]


# Mode localized yang diuji (TC-006, TC-009, TC-010)
LATEST_FEED_LOCALIZED_MODES = [
    {"value": "true",   "label": "Localized"},
   #{"value": "false",  "label": "Global"},
    #{"value": "mix",    "label": "Mix"},
]
