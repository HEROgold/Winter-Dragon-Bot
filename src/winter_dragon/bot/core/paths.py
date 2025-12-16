from pathlib import Path


BOT_CONFIG = Path("config.ini")

CORE_DIR = Path(__file__).parent
PACKAGE_DIR = CORE_DIR.parent
ROOT_DIR = PACKAGE_DIR.parent
EXTENSIONS = PACKAGE_DIR / "extensions"
DYNAMIC_DIR = PACKAGE_DIR / "dynamic"
IMG_DIR = DYNAMIC_DIR / "img"
METRICS_FILE = IMG_DIR / "system_metrics.png"
