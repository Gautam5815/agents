import os
import sys

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")
LINKEDIN_ORG_URN = os.getenv("LINKEDIN_ORG_URN")

TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

# When true, the pipeline runs end-to-end (research, draft, image) but skips the actual
# LinkedIn publish call — for safely testing changes to the prompt/pipeline.
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in ("1", "true", "yes")


def require(*names: str) -> None:
    missing = [n for n in names if not globals().get(n)]
    if missing:
        print(f"Missing required environment variable(s): {', '.join(missing)}")
        print("Copy .env.example to .env and fill in the values, then try again.")
        sys.exit(1)
