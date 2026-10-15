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

# Step 2 test pages. The full list will come from the sitemap in step 12.
TEST_URLS = [
    "https://www.fnx.co.il/claims-customer-service/claims-health-insurance/surgery-treatment-covers/",
    "https://www.fnx.co.il/car-insurance/car_information/appraiser/",
    "https://www.fnx.co.il/health-insurance/surgeries/",
    "https://www.fnx.co.il/mortgage-insurance/mortgage-insurance-info/mortgage-life-insurance/",
    "https://www.fnx.co.il/customer-service/car-insurance/car_towing_services/",
]
