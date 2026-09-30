from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLE_DIR = DATA_DIR / "sample"
RESULTS_DIR = ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"
CHARTS_DIR = RESULTS_DIR / "charts"
REPORT_DIR = ROOT / "report"

ZIP_PATH = RAW_DIR / "UserBehavior.csv.zip"
SAMPLE_PATH = SAMPLE_DIR / "UserBehavior_sample.csv.gz"
CLEAN_PATH = SAMPLE_DIR / "UserBehavior_clean.csv.gz"
MANIFEST_PATH = DATA_DIR / "source_manifest.json"
METRICS_PATH = RESULTS_DIR / "metrics.json"
DB_PATH = DATA_DIR / "analysis.db"

OFFICIAL_URL = "https://tianchi.aliyun.com/dataset/649"
MIRROR_DOWNLOAD_URL = "https://www.kaggle.com/api/v1/datasets/download/marwa80/userbehavior"
COLUMNS = ["user_id", "item_id", "category_id", "behavior", "timestamp"]
VALID_BEHAVIORS = {"pv", "cart", "fav", "buy"}
START_DATE = "2017-11-25"
END_DATE = "2017-12-03"
SAMPLE_MODULUS = 100
SAMPLE_REMAINDER = 0


def ensure_directories():
    for path in [RAW_DIR, SAMPLE_DIR, RESULTS_DIR, TABLES_DIR, CHARTS_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)
