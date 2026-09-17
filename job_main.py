import argparse
import json
import os
import sys
from datetime import datetime

from agent import config
from jobsearch import contact_finder, email_alerts, email_writer, jooble_client


def print_job_list(jobs: list[dict]) -> None:
    print(f"\nFound {len(jobs)} job(s):\n")
    for i, job in enumerate(jobs, 1):
        source = f" [{job['source']}]" if job.get("source") else ""
        print(f"[{i}] {job['title']} — {job['company']} ({job['location']}){source}")
        print(f"    {job['link']}")


def process_job(job: dict, out_dir: str) -> None:
    print(f"\n=== {job['title']} at {job['company']} ===")

    print("Finding company domain and contact candidates...")
    contacts = contact_finder.find_contacts(job["company"])

    if contacts["domain"]:
        print(f"  Domain: {contacts['domain']}")
        print(f"  Generic email guesses: {', '.join(contacts['generic_emails'])}")
        if contacts["named_contacts"]:
            print("  Named contacts (Hunter.io):")
            for c in contacts["named_contacts"]:
                print(f"    - {c['email']} ({c.get('position') or 'unknown role'}, "
                      f"confidence {c.get('confidence')})")
        else:
            print("  No named contacts found (Hunter.io not configured or no results) — "
                  "use the generic guesses above, or the job listing link to apply directly.")
    else:
        print("  Could not confidently identify the company's domain — "
              "you'll need to find the contact/application method manually via the "
              "job listing link below.")

    print("Drafting application email...")
    try:
        draft = email_writer.draft_application_email(job)
    except ValueError as e:
        print(f"  Skipped: {e}")
        return

    print(f"\n--- DRAFT EMAIL ---\nSubject: {draft['subject']}\n\n{draft['body']}\n"
          f"-------------------\n")
    print(f"Apply link (for reference / Easy Apply / manual review): {job['link']}")
    print("This draft was NOT sent. Review, personalize, and send it yourself.")

    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = "".join(c if c.isalnum() else "_" for c in job["company"])[:40]
    out_path = os.path.join(out_dir, f"{timestamp}_{safe_company}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"job": job, "contacts": contacts, "draft": draft}, f, indent=2)
    print(f"Saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search jobs via Jooble, find likely company contacts, and draft "
                     "(never send) a tailored application email for each."
    )
    parser.add_argument("--keywords", default="IT Project Manager",
                         help="Job search keywords (default: 'IT Project Manager')")
    parser.add_argument("--location", default="Dubai, United Arab Emirates",
                         help="Job search location (default: 'Dubai, United Arab Emirates'). "
                              "Jooble needs a specific location string — plain 'Dubai' alone "
                              "returns no results for some queries.")
    parser.add_argument("--limit", type=int, default=10,
                         help="Max number of jobs to fetch (default: 10)")
    parser.add_argument("--include-email-alerts", action="store_true",
                         help="Also parse LinkedIn/Naukri Gulf job-alert emails from your "
                              "own inbox via IMAP (requires IMAP_EMAIL/IMAP_APP_PASSWORD "
                              "in .env, and that you've set up saved-search alerts on "
                              "both sites yourself — see README.md).")
    args = parser.parse_args()

    try:
        config.require("JOOBLE_API_KEY", "OPENAI_API_KEY", "SERPAPI_API_KEY")
    except config.MissingConfigError as e:
        print(e)
        sys.exit(1)

    jobs = jooble_client.search_jobs(args.keywords, args.location)[: args.limit]

    if args.include_email_alerts:
        print("Checking LinkedIn/Naukri Gulf job-alert emails in your inbox...")
        try:
            alert_jobs = email_alerts.fetch_all_alert_jobs()
            print(f"  Found {len(alert_jobs)} job(s) from email alerts.")
            jobs += alert_jobs
        except config.MissingConfigError as e:
            print(f"  Skipped: {e}")

    if not jobs:
        print("No jobs found for that search.")
        sys.exit(0)

    print_job_list(jobs)
    selection = input(
        "\nEnter job number(s) to draft an application for (comma-separated), "
        "'all', or blank to quit: "
    ).strip()

    if not selection:
        return

    if selection.lower() == "all":
        chosen = jobs
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            chosen = [jobs[i] for i in indices if 0 <= i < len(jobs)]
        except ValueError:
            print("Invalid selection.")
            sys.exit(1)

    for job in chosen:
        process_job(job, out_dir="output/job_drafts")


if __name__ == "__main__":
    main()
