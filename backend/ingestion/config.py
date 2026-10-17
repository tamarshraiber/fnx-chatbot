from pathlib import Path

BASE_URL = "https://www.fnx.co.il"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
ROBOTS_URL = f"{BASE_URL}/robots.txt"

USER_AGENT = "Mozilla/5.0 (compatible; FnxRagHackathonBot/1.0)"

# Seconds to wait between two page requests (be polite to the website).
DELAY_SECONDS = 1.5

# Where the scraper saves one JSON file per page.
RAW_DIR = Path("data/raw")

# Where the chunker saves all chunks in one JSON file.
CHUNKS_DIR = Path("data/chunks")

# Chunk sizes are in characters.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
# A piece shorter than this is merged with its neighbour.
MIN_CHUNK_SIZE = 200

# Step 12: first path part of the pages we crawl (claims, products, customer service, guides, savings).
INCLUDE_SECTIONS = {
    "claims-customer-service",
    "customer-service",
    "car-insurance",
    "health-insurance",
    "apartment-insurance",
    "travel-insurance",
    "mortgage-insurance",
    "pets-insurance",
    "life-insurance",
    "other-insurances",
    "disability-and-incapacity-to-work",
    "business-insurance",
    "truck-insurance",
    "marine_aviation_insurance",
    "pension-savings",
    "gemel",
    "savings",
    "ishtalmutfund",
    "pension_retirement",
    "loans",
    "fnx-insurance-ltd",
    "takanottashlum",
    "alternativeinvestments",
}

# Only pages on this host are crawled (login/form subdomains are left out).
ALLOWED_HOST = "www.fnx.co.il"

# Step 2 test pages (kept for quick tests).
TEST_URLS = [
    "https://www.fnx.co.il/claims-customer-service/claims-health-insurance/surgery-treatment-covers/",
    "https://www.fnx.co.il/car-insurance/car_information/appraiser/",
    "https://www.fnx.co.il/health-insurance/surgeries/",
    "https://www.fnx.co.il/mortgage-insurance/mortgage-insurance-info/mortgage-life-insurance/",
    "https://www.fnx.co.il/customer-service/car-insurance/car_towing_services/",
]
