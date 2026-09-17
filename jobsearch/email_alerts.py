"""Reads job-alert emails from your own inbox via IMAP and parses them into job listings.

This is NOT scraping: LinkedIn and Naukri Gulf send these emails because you subscribed
to a saved-search alert on their site (a normal, intended feature of both platforms). The
agent only reads mail already sitting in your inbox, using your own IMAP credentials.

Email HTML templates are undocumented and can change over time, so the parsers here use
loose heuristics (any link to a job-view URL, plus its link text as the title). If a
provider changes their template and parsing breaks, the fix is to inspect a real sample
email's HTML and adjust the parser here.
"""
import email
import imaplib
import re
from datetime import datetime, timedelta
from email.header import decode_header

from bs4 import BeautifulSoup

from agent import config


def _connect() -> imaplib.IMAP4_SSL:
    config.require("IMAP_EMAIL", "IMAP_APP_PASSWORD")
    conn = imaplib.IMAP4_SSL(config.IMAP_HOST)
    conn.login(config.IMAP_EMAIL, config.IMAP_APP_PASSWORD)
    return conn


def _decode(value) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = ""
    for text, enc in parts:
        decoded += text.decode(enc or "utf-8", errors="ignore") if isinstance(text, bytes) else text
    return decoded


def _fetch_html_bodies(sender: str, since_days: int) -> list[str]:
    """Fetch HTML bodies of recent emails from a given sender."""
    conn = _connect()
    try:
        conn.select("INBOX")
        since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        status, data = conn.search(None, f'(FROM "{sender}" SINCE "{since_date}")')
        if status != "OK":
            return []

        bodies = []
        for msg_id in data[0].split():
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])

            html = None
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        html = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="ignore"
                        )
                        break
            elif msg.get_content_type() == "text/html":
                html = msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8", errors="ignore"
                )

            if html:
                bodies.append(html)
        return bodies
    finally:
        conn.logout()


def _extract_jobs_from_links(html: str, url_pattern: str, source: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    seen_links = set()
    jobs = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(url_pattern, href):
            continue
        link = href.split("?")[0]
        if link in seen_links:
            continue
        seen_links.add(link)

        title = a.get_text(strip=True)
        if not title or len(title) < 3:
            continue

        jobs.append({
            "title": title,
            "company": "Unknown company (see listing)",
            "location": "",
            "snippet": "",
            "salary": "",
            "link": link,
            "updated": "",
            "source": source,
        })
    return jobs


def fetch_linkedin_alert_jobs(since_days: int = 7) -> list[dict]:
    bodies = _fetch_html_bodies(config.LINKEDIN_ALERT_SENDER, since_days)
    jobs = []
    for html in bodies:
        jobs.extend(_extract_jobs_from_links(html, r"linkedin\.com/(jobs|comm/jobs)", "linkedin_alert"))
    return jobs


def fetch_naukrigulf_alert_jobs(since_days: int = 7) -> list[dict]:
    bodies = _fetch_html_bodies(config.NAUKRIGULF_ALERT_SENDER, since_days)
    jobs = []
    for html in bodies:
        jobs.extend(_extract_jobs_from_links(html, r"naukrigulf\.com/.*job", "naukrigulf_alert"))
    return jobs


def fetch_all_alert_jobs(since_days: int = 7) -> list[dict]:
    return fetch_linkedin_alert_jobs(since_days) + fetch_naukrigulf_alert_jobs(since_days)
