import requests

from agent import config

JOOBLE_URL_TEMPLATE = "https://jooble.org/api/{key}"


def search_jobs(keywords: str, location: str, page: int = 1) -> list[dict]:
    """Search jobs via the Jooble API. Returns a list of
    {title, company, location, snippet, salary, link, updated} dicts."""
    config.require("JOOBLE_API_KEY")

    url = JOOBLE_URL_TEMPLATE.format(key=config.JOOBLE_API_KEY)
    resp = requests.post(
        url,
        json={"keywords": keywords, "location": location, "page": page},
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("jobs", []):
        jobs.append({
            "title": item.get("title", ""),
            "company": item.get("company", "").strip() or "Unknown company",
            "location": item.get("location", ""),
            "snippet": item.get("snippet", ""),
            "salary": item.get("salary", ""),
            "link": item.get("link", ""),
            "updated": item.get("updated", ""),
        })
    return jobs
