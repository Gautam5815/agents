import base64
import datetime
import json
import os

from flask import Flask, jsonify, render_template, request

from agent import config, content, daily_topic, github_store, image_gen, linkedin_client, newsletter, research
from jobsearch import contact_finder, email_alerts, email_writer, jooble_client

app = Flask(__name__)

_NEWSLETTER_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "newsletter_latest.json")


@app.route("/")
def index():
    return render_template("index.html", dry_run=config.DRY_RUN)


@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")


@app.route("/newsletter")
def newsletter_page():
    draft = None
    if os.path.exists(_NEWSLETTER_DATA_PATH):
        with open(_NEWSLETTER_DATA_PATH, "r", encoding="utf-8") as f:
            draft = json.load(f)
    return render_template("newsletter.html", draft=draft)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    topic = (request.json or {}).get("topic", "").strip()
    if not topic:
        return jsonify({"error": "Topic is required."}), 400

    try:
        results = research.search_topic(topic)
        research_text = research.format_research_for_prompt(results)

        generated = content.generate_post_and_image_prompt(topic, research_text)
        post_text = generated["post"]
        image_prompt = generated["image_prompt"]

        image_b64 = image_gen.generate_image_b64(image_prompt)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "post": post_text,
        "image_prompt": image_prompt,
        "image_b64": image_b64,
        "research_count": len(results),
    })


@app.route("/api/publish", methods=["POST"])
def api_publish():
    if config.DRY_RUN:
        return jsonify({"error": "DRY_RUN is enabled — publishing is disabled."}), 400

    body = request.json or {}
    post_text = (body.get("post") or "").strip()
    image_b64 = body.get("image_b64")

    if not post_text or not image_b64:
        return jsonify({"error": "Both 'post' and 'image_b64' are required."}), 400

    try:
        image_bytes = base64.b64decode(image_b64)
        result = linkedin_client.post_with_image_bytes(post_text, image_bytes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"result": result})


@app.route("/api/cron/daily-post", methods=["GET", "POST"])
def api_cron_daily_post():
    """Fully autonomous daily post: picks a topic deterministically (no human input),
    researches, drafts, generates an image, and publishes straight to LinkedIn with no
    review step. Triggered by Vercel Cron (see vercel.json). This is an explicit,
    confirmed exception to this app's normal confirm-before-publish behavior — see
    README.md "Daily automated post" for the tradeoffs.

    Protected by CRON_SECRET: Vercel automatically sends
    "Authorization: Bearer <CRON_SECRET>" on requests it makes to this endpoint when
    CRON_SECRET is set as a project env var, so any other caller is rejected."""
    if config.CRON_SECRET:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.CRON_SECRET}":
            return jsonify({"error": "Unauthorized."}), 401

    topic = daily_topic.pick_daily_topic()
    log = {"topic": topic, "dry_run": config.DRY_RUN}

    try:
        results = research.search_topic(topic)
        research_text = research.format_research_for_prompt(results)
        log["research_count"] = len(results)

        generated = content.generate_post_and_image_prompt(topic, research_text)
        post_text = generated["post"]
        image_prompt = generated["image_prompt"]
        log["post"] = post_text
        log["image_prompt"] = image_prompt

        image_b64 = image_gen.generate_image_b64(image_prompt)
    except Exception as e:
        log["error"] = f"Generation failed: {e}"
        print(log)
        return jsonify(log), 500

    if config.DRY_RUN:
        log["published"] = False
        log["note"] = "DRY_RUN is enabled — skipped publish."
        print(log)
        return jsonify(log)

    try:
        image_bytes = base64.b64decode(image_b64)
        result = linkedin_client.post_with_image_bytes(post_text, image_bytes)
        log["published"] = True
        log["linkedin_result"] = result
    except Exception as e:
        log["published"] = False
        log["error"] = f"Publish failed: {e}"
        print(log)
        return jsonify(log), 500

    print(log)
    return jsonify(log)


@app.route("/api/cron/weekly-newsletter", methods=["GET", "POST"])
def api_cron_weekly_newsletter():
    """Weekly (Monday 8am UTC, see vercel.json) newsletter draft generation. This does
    NOT publish anything — LinkedIn has no API for Newsletter editions, so this only
    prepares a draft (research -> write -> header image -> source verification) and
    commits it to the repo (via GitHub, since serverless functions don't share a
    filesystem across invocations) so the /newsletter page can display it for you to
    manually copy into LinkedIn and publish yourself.

    Protected by CRON_SECRET the same way as /api/cron/daily-post."""
    if config.CRON_SECRET:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.CRON_SECRET}":
            return jsonify({"error": "Unauthorized."}), 401

    try:
        results = newsletter.research_ai_news()
        draft = newsletter.generate_newsletter(results)
        draft["image_b64"] = image_gen.generate_image_b64(draft["image_prompt"])
        draft["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

        github_store.write_json(
            "data/newsletter_latest.json",
            draft,
            message=f"Weekly newsletter draft: {draft.get('title', 'untitled')}",
        )
    except Exception as e:
        print({"newsletter_error": str(e)})
        return jsonify({"error": str(e)}), 500

    print({"newsletter_generated": draft.get("title")})
    return jsonify({"status": "ok", "title": draft.get("title")})


@app.route("/api/jobs/search", methods=["POST"])
def api_jobs_search():
    body = request.json or {}
    keywords = (body.get("keywords") or "").strip()
    location = (body.get("location") or "").strip()
    limit = int(body.get("limit") or 10)

    if not keywords or not location:
        return jsonify({"error": "Both 'keywords' and 'location' are required."}), 400

    try:
        jobs = jooble_client.search_jobs(keywords, location)[:limit]
    except config.MissingConfigError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"jobs": jobs})


@app.route("/api/jobs/email-alerts", methods=["POST"])
def api_jobs_email_alerts():
    """Reads LinkedIn/Naukri Gulf job-alert emails from the user's own inbox via IMAP —
    not scraping, these are emails the user subscribed to via a saved-search alert."""
    try:
        jobs = email_alerts.fetch_all_alert_jobs()
    except config.MissingConfigError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"jobs": jobs})


@app.route("/api/jobs/draft", methods=["POST"])
def api_jobs_draft():
    body = request.json or {}
    job = body.get("job")
    profile = (body.get("profile") or "").strip()

    if not job or not job.get("company"):
        return jsonify({"error": "A job with at least a 'company' is required."}), 400
    if not profile:
        return jsonify({"error": "Your background/profile is required to draft an honest email."}), 400

    try:
        contacts = contact_finder.find_contacts(job["company"])
        draft = email_writer.draft_application_email(job, profile=profile)
    except config.MissingConfigError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"contacts": contacts, "draft": draft})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
