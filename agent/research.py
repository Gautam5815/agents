import requests

from . import config

SERPAPI_URL = "https://serpapi.com/search"


def search_topic(topic: str, num_results: int = 8) -> list[dict]:
    """Run a Google search via SerpApi and return a list of
    {title, link, snippet} results for the given topic."""
    config.require("SERPAPI_API_KEY")

    resp = requests.get(
        SERPAPI_URL,
        params={
            "q": topic,
            "engine": "google",
            "num": num_results,
            "api_key": config.SERPAPI_API_KEY,
        },
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("organic_results", [])[:num_results]:
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
        )

    answer_box = data.get("answer_box")
    if answer_box:
        results.insert(
            0,
            {
                "title": answer_box.get("title", "Answer box"),
                "link": answer_box.get("link", ""),
                "snippet": answer_box.get("snippet") or answer_box.get("answer", ""),
            },
        )

    return results


def format_research_for_prompt(results: list[dict]) -> str:
    if not results:
        return "No web research results were found."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   Source: {r['link']}")
    return "\n".join(lines)
