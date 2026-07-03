import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Override via environment in any real deployment.
SECRET_KEY = os.environ.get("STA_SECRET_KEY", "dev-only-secret-key-not-for-production-use")
TOKEN_EXPIRE_HOURS = 12

# First-run admin account, seeded on startup if no admin exists yet.
SEED_ADMIN_USERNAME = os.environ.get("STA_ADMIN_USERNAME", "admin")
SEED_ADMIN_PASSWORD = os.environ.get("STA_ADMIN_PASSWORD", "adminpass123")

DATABASE_URL = os.environ.get(
    "STA_DATABASE_URL", f"sqlite:///{BASE_DIR / 'sta_debugger.db'}"
)

# Optional server-side Groq key for the AI explanation feature.
# Users can also supply their own key per request from the UI.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB is plenty for a text report
