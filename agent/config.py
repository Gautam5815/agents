import os

from dotenv import load_dotenv


class MissingConfigError(RuntimeError):
    pass

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")
LINKEDIN_ORG_URN = os.getenv("LINKEDIN_ORG_URN")

# Job search agent (jobsearch/) — Jooble is required, Hunter.io is optional (falls back
# to generic careers@/hr@ email guesses if not set).
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")

# Email job-alert parsing (jobsearch/email_alerts.py) — reads job alert emails you've
# subscribed to on LinkedIn/Naukri Gulf from your own inbox via IMAP. Not scraping: these
# are emails the platforms send you because you asked for them via a saved search alert.
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_EMAIL = os.getenv("IMAP_EMAIL")
IMAP_APP_PASSWORD = os.getenv("IMAP_APP_PASSWORD")
LINKEDIN_ALERT_SENDER = os.getenv("LINKEDIN_ALERT_SENDER", "jobalerts-noreply@linkedin.com")
NAUKRIGULF_ALERT_SENDER = os.getenv("NAUKRIGULF_ALERT_SENDER", "alerts@naukrigulf.com")

TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

# When true, the pipeline runs end-to-end (research, draft, image) but skips the actual
# LinkedIn publish call — for safely testing changes to the prompt/pipeline.
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in ("1", "true", "yes")

# Shared secret for the /api/cron/daily-post endpoint. Set this as a Vercel project env
# var named exactly CRON_SECRET — Vercel then automatically sends it as
# "Authorization: Bearer <value>" on requests it makes to cron endpoints, so the endpoint
# can verify the request actually came from Vercel Cron and not a public/unauthenticated
# caller triggering an unwanted autonomous post.
CRON_SECRET = os.getenv("CRON_SECRET")


def require(*names: str) -> None:
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise MissingConfigError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values, then try again."
        )
