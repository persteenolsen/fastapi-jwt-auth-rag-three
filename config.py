import os
from dotenv import load_dotenv

load_dotenv()

# Note: All the variables could be loaded from config.py
DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

if not DATABASE_URL:
    raise Exception("Missing DATABASE_URL")

if not VOYAGE_API_KEY:
    raise Exception("Missing VOYAGE_API_KEY")

SECRET_KEY = os.getenv("SECRET_KEY")
FAKE_USERNAME = os.getenv("FAKE_USERNAME")
FAKE_PASSWORD = os.getenv("FAKE_PASSWORD")

required_env_vars = ["SECRET_KEY", "FAKE_USERNAME", "FAKE_PASSWORD"]
for var in required_env_vars:
    if not os.getenv(var):
        raise RuntimeError(f"Missing environment variable: {var}")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
