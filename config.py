import os
from dotenv import load_dotenv

load_dotenv()

# Load variables from .env into process environment if running locally
load_dotenv()

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemini-3.6-flash")
    PORT: int = int(os.getenv("PORT", "8000"))

    def validate(self):
        if not self.GEMINI_API_KEY:
            raise ValueError("CRITICAL: GEMINI_API_KEY environment variable is not set.")

settings = Settings()
settings.validate()