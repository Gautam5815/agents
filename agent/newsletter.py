import json
import os

from openai import OpenAI

from . import config, research

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "newsletter_prompt.md")


def _load_prompt() -> str:
    with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def research_ai_news(num_results: int = 15) -> list[dict]:
    """Broad search for recent AI news to draw the newsletter's items from."""
    return research.search_topic("latest AI news this week", num_results=num_results)


def generate_newsletter(results: list[dict]) -> dict:
    """Drafts the newsletter from research results. Returns a dict with title, intro,
    items (each with heading/body/source_url/source_verified), and image_prompt.

    source_verified is computed here, not trusted from the model: each item's
    source_url is checked against the actual URLs in `results` and marked
    unverified (rather than dropped) if the model didn't copy one exactly, so a
    human reviewing the draft can see at a glance which claims are actually backed
    by a real source before publishing.
    """
    config.require("OPENAI_API_KEY")
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    valid_urls = {r["link"] for r in results if r.get("link")}
    research_text = research.format_research_for_prompt(results)

    response = client.chat.completions.create(
        model=config.TEXT_MODEL,
        messages=[
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": f"Research results:\n{research_text}"},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)

    for item in data.get("items", []):
        item["source_verified"] = item.get("source_url") in valid_urls

    return data
