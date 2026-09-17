from urllib.parse import urlparse

import requests

from agent import config, research

GENERIC_PREFIXES = ["careers", "hr", "jobs", "recruitment"]

# Domains that are never the company's own site (job boards, aggregators, socials)
# even if they show up in search results for "<company> official website".
_EXCLUDED_DOMAINS = {
    "linkedin.com", "naukrigulf.com", "naukri.com", "indeed.com", "bayt.com",
    "glassdoor.com", "jooble.org", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "wikipedia.org", "crunchbase.com",
}


def find_company_domain(company_name: str) -> str | None:
    """Best-effort discovery of a company's official domain using the same
    SerpApi research step the LinkedIn agent uses, not scraping."""
    results = research.search_topic(f"{company_name} official website", num_results=5)
    for r in results:
        link = r.get("link", "")
        if not link:
            continue
        domain = urlparse(link).netloc.lower().removeprefix("www.")
        if domain and not any(domain.endswith(excl) for excl in _EXCLUDED_DOMAINS):
            return domain
    return None


def guess_generic_emails(domain: str) -> list[str]:
    return [f"{prefix}@{domain}" for prefix in GENERIC_PREFIXES]


def hunter_domain_search(domain: str) -> list[dict]:
    """Look up named contacts at a domain via Hunter.io (legitimate, ToS-compliant
    business email finder). Returns [] if HUNTER_API_KEY isn't configured or no
    results are found."""
    if not config.HUNTER_API_KEY:
        return []

    resp = requests.get(
        "https://api.hunter.io/v2/domain-search",
        params={"domain": domain, "api_key": config.HUNTER_API_KEY, "limit": 10},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()

    contacts = []
    for email in data.get("data", {}).get("emails", []):
        contacts.append({
            "email": email.get("value"),
            "type": email.get("type"),
            "position": email.get("position"),
            "confidence": email.get("confidence"),
        })
    return contacts


def find_contacts(company_name: str) -> dict:
    """Returns {"domain": str|None, "generic_emails": [...], "named_contacts": [...]}."""
    domain = find_company_domain(company_name)
    if not domain:
        return {"domain": None, "generic_emails": [], "named_contacts": []}

    return {
        "domain": domain,
        "generic_emails": guess_generic_emails(domain),
        "named_contacts": hunter_domain_search(domain),
    }
