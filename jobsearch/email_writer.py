import json
import os

from openai import OpenAI

from agent import config

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "job_email_prompt.md")
_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "profile.md")


def _load(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_profile() -> str:
    profile = _load(_PROFILE_PATH)
    if "[Your full name]" in profile:
        raise ValueError(
            f"{_PROFILE_PATH} still has placeholder text — fill in your real background "
            "before drafting application emails."
        )
    return profile


def draft_application_email(job: dict, profile: str | None = None) -> dict:
    """Draft a tailored application email for a job dict (title, company, snippet, link).
    If `profile` isn't given, it's loaded from jobsearch/profile.md (CLI use); the web UI
    passes the profile text entered in the form instead. Returns {"subject", "body"}."""
    config.require("OPENAI_API_KEY")
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    profile = profile.strip() if profile else load_profile()
    system_prompt = _load(_PROMPT_PATH)
    user_prompt = (
        f"Candidate profile:\n{profile}\n\n"
        f"Job posting:\n"
        f"Title: {job.get('title')}\n"
        f"Company: {job.get('company')}\n"
        f"Location: {job.get('location')}\n"
        f"Description snippet: {job.get('snippet')}\n"
        f"Listing link: {job.get('link')}\n\n"
        "Write the application email as instructed."
    )

    response = client.chat.completions.create(
        model=config.TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    return {"subject": data["subject"].strip(), "body": data["body"].strip()}
