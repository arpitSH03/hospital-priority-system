import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory (project root: hospital-priority-system)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from project root if it exists
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Database Configuration
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", 3306))
DB_USER: str = os.getenv("DB_USER", "root")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
DB_NAME: str = os.getenv("DB_NAME", "hospital_db")

# Directory Paths
FRONTEND_DIR: Path = BASE_DIR / "frontend"
