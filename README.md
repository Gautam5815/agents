# LinkedIn Marketing Agent

A CLI agent that, given a topic:
1. Researches the topic on the web (SerpApi/Google Search).
2. Writes a LinkedIn post with GPT, grounded in that research.
3. Generates an accompanying image with OpenAI's image model.
4. Shows you a preview and, on confirmation, publishes the post + image to your LinkedIn profile.

## 1. Install dependencies

```
pip install -r requirements.txt
```

## 2. Configure API keys

Copy `.env.example` to `.env` and fill in the values:

```
copy .env.example .env
```

- `OPENAI_API_KEY` — your existing OpenAI key (used for text + image generation).
- `SERPAPI_API_KEY` — get one free at https://serpapi.com (used for web research).
- `LINKEDIN_ACCESS_TOKEN` / `LINKEDIN_PERSON_URN` / `LINKEDIN_ORG_URN` — see setup below.
- `DRY_RUN` — set to `true` to run the full pipeline (research, draft, image) without
  publishing to LinkedIn. Useful for testing prompt/pipeline changes safely.

## 3. LinkedIn setup (one-time)

LinkedIn requires an OAuth access token from an app you register — you can't just use a
username/password. Steps:

1. **Create an app**: go to https://www.linkedin.com/developers/apps → "Create app".
   - You need an associated LinkedIn Company Page to create an app (you can create a
     free one for yourself if you don't have one).
2. **Add products**: on your app's "Products" tab, request/add:
   - "Sign In with LinkedIn using OpenID Connect"
   - "Share on LinkedIn"
   These are self-serve and get approved instantly for your own account.
3. **Get an authorization code**: on the app's "Auth" tab, note your Client ID and Client
   Secret, and add a redirect URL (e.g. `https://www.linkedin.com/developers/tools/oauth/redirect`
   or `http://localhost:8000/callback`). Then visit this URL in your browser (replace values):

   ```
   https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URL&scope=openid%20profile%20w_member_social
   ```

   Approve access; LinkedIn redirects you to your redirect URL with a `?code=...` param.
4. **Exchange the code for an access token**:

   ```
   curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
     -d grant_type=authorization_code \
     -d code=THE_CODE_FROM_STEP_3 \
     -d redirect_uri=YOUR_REDIRECT_URL \
     -d client_id=YOUR_CLIENT_ID \
     -d client_secret=YOUR_CLIENT_SECRET
   ```

   The response's `access_token` is valid for ~60 days. Put it in `.env` as
   `LINKEDIN_ACCESS_TOKEN`.
5. **(Optional) Person URN**: you can leave `LINKEDIN_PERSON_URN` blank — the agent will
   fetch it automatically from LinkedIn's `/v2/userinfo` endpoint using your access token.

Note: since the access token expires in ~60 days, you'll need to repeat steps 3-4
periodically (or implement the refresh-token flow if your app supports it).

### Posting as the Trynocode company page instead of a personal profile

By default the agent posts as the authenticated person. To post as the Trynocode company
page instead:
- Request the `w_organization_social` scope in step 3's authorization URL (in addition to
  `openid profile w_member_social`), and make sure the authenticating account is an admin
  of the LinkedIn company page.
- Set `LINKEDIN_ORG_URN` in `.env` (format: `urn:li:organization:<page id>` — the page id
  is visible in the page's admin URL or via the Organization Lookup API).
- When `LINKEDIN_ORG_URN` is set, it takes priority over `LINKEDIN_PERSON_URN`.

## 4. Run it

```
python main.py "The future of AI agents in B2B sales"
```

Or run without arguments and it will prompt you for a topic:

```
python main.py
```

It will print the researched sources, show the generated post text and image, then ask
for confirmation before publishing. Pass `--yes` / `-y` to skip the confirmation and post
immediately. If `DRY_RUN=true` is set, the confirmation/publish step is skipped entirely.

Generated images are saved under `output/post_<timestamp>.png`, and a JSON log of every
run (topic, research results, draft post, image prompt, and publish result) is saved to
`output/run_<timestamp>.json` for traceability.

## Web UI

A small Flask web UI is included as an alternative to the CLI:

```
python app.py
```

Then open http://127.0.0.1:5000 — enter a topic, review the generated post (editable) and
image, then publish. It calls the same `agent/` modules as the CLI and requires the same
`.env` configuration.

## Deploying the web UI to Vercel

The web UI (`app.py` via `api/index.py`) is stateless — the generated image is returned as
base64 directly to the browser and round-tripped back on publish, with no server-side
files or in-memory drafts — so it works as Vercel serverless functions.

1. Push this repo to GitHub.
2. In the Vercel dashboard, import the GitHub repo (Vercel auto-detects `vercel.json`).
3. Add these environment variables in the Vercel project settings (never commit them):
   `OPENAI_API_KEY`, `SERPAPI_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, and optionally
   `LINKEDIN_PERSON_URN`, `LINKEDIN_ORG_URN`, `DRY_RUN`.
4. Deploy.

Note: the pipeline (web search + GPT + image generation) can take 20-60+ seconds.
`vercel.json` sets `maxDuration: 60` for the function, which requires a Vercel plan that
supports function durations beyond the default 10s (Pro, or Hobby with Fluid Compute) —
check your plan's limits if you see request timeouts.

## Daily automated post (fully autonomous, no review step)

`/api/cron/daily-post` runs the entire pipeline unattended once a day: it picks a topic
deterministically from [prompts/daily_topics.md](prompts/daily_topics.md) (based on the
day of the year — no repeats until the list cycles through), researches it, drafts the
post, generates the image, and **publishes straight to LinkedIn with no human review
step**.

This is a deliberate exception to this app's normal confirm-before-publish behavior
(the `/` and `/jobs` pages both require an explicit click before anything goes out) — it
trades that safety checkpoint for full automation. Understand what you're accepting:
- A bad draft (factual error, off-brand tone, hallucinated detail) goes live with nobody
  checking it first.
- The only after-the-fact visibility is Vercel's function logs (`vercel logs <url>`),
  which print the topic, draft, and publish result for every run.
- `DRY_RUN=true` makes this endpoint run the full pipeline and log the result without
  publishing — test with this for at least a few days before trusting it live.

**Setup:**
1. Edit [prompts/daily_topics.md](prompts/daily_topics.md) — one topic per line, add or
   remove as you like.
2. In Vercel project settings, add an env var `CRON_SECRET` (any random string). Vercel
   automatically sends it as `Authorization: Bearer <value>` on its own requests to this
   endpoint, so anyone else calling the URL directly gets rejected with 401.
3. The schedule lives in [vercel.json](vercel.json)'s `crons` field (default: `0 8 * * *`,
   i.e. 8am UTC daily). Vercel's Hobby plan supports daily-or-less-frequent cron jobs.
4. Deploy. Vercel picks up the cron schedule automatically from `vercel.json`.

To test manually without waiting for the schedule:
```
curl -X POST https://<your-deployment>/api/cron/daily-post -H "Authorization: Bearer <CRON_SECRET>"
```

## Weekly newsletter draft (AI news, draft-only — never auto-published)

LinkedIn has no API for publishing Newsletter editions (as opposed to regular feed
posts) — there is no way to automate that final publish step without violating
LinkedIn's terms via browser automation, which this project does not do. Instead,
`/api/cron/weekly-newsletter` runs every Monday 8am UTC and:

1. Searches for recent AI news via SerpApi.
2. Has GPT select 3-5 genuinely useful developments and draft the newsletter
   ([prompts/newsletter_prompt.md](prompts/newsletter_prompt.md)), citing a source URL
   for each item.
3. **Verifies** each cited source_url actually matches one of the real search results
   (not just trusting the model) — items that don't match are marked "unverified" in the
   UI so you can catch a hallucinated citation before publishing.
4. Generates a header image.
5. Commits the draft to the repo as `data/newsletter_latest.json` via the GitHub API —
   this is how the draft survives between the cron job and a later page view, since
   Vercel serverless functions don't share a filesystem across invocations; the commit
   also triggers Vercel's normal auto-deploy, so the page picks up the new draft shortly
   after.

Visit `/newsletter` to review the latest draft, then **copy it and publish it on LinkedIn
yourself** (profile → Write article) — nothing here ever auto-publishes a newsletter.

**Setup**, in addition to the vars already needed for daily posting:
- `GITHUB_TOKEN`: a GitHub personal access token with write access to this repo's
  contents (fine-grained token scoped to just this repo, "Contents: Read and write" — or
  a classic token with the `repo` scope).
- `GITHUB_REPO` (defaults to `Gautam5815/agents`) and `GITHUB_BRANCH` (defaults to `main`)
  if you fork this to a different repo.
- The schedule lives in `vercel.json`'s `crons` field alongside the daily post job.

## Job search + application drafting agent

`job_main.py` is a separate tool: it searches job listings via the [Jooble API](https://jooble.org/api/about)
(legitimate public API — this does not scrape LinkedIn or Naukri Gulf, since both
explicitly prohibit automated scraping in their terms of service), then for each job you
select it:
1. Finds the company's likely official domain using the same SerpApi research step the
   LinkedIn agent uses.
2. Suggests generic contact emails (`careers@`, `hr@`, `jobs@`, `recruitment@`) for that
   domain, and, if you've configured `HUNTER_API_KEY`, looks up named contacts via
   [Hunter.io](https://hunter.io) (a legitimate business-email-finder service).
3. Drafts a tailored application email with GPT, grounded strictly in your real
   background — it will not invent experience.

**It never sends anything.** Every draft is printed and saved to
`output/job_drafts/<timestamp>_<company>.json` for you to review, personalize, and send
yourself.

### Setup

1. Fill in [jobsearch/profile.md](jobsearch/profile.md) with your real background (role,
   years of experience, skills, certifications, achievements) — the email drafts are
   generated only from what's in this file.
2. Get a free Jooble API key at https://jooble.org/api/about and set `JOOBLE_API_KEY` in
   `.env`.
3. (Optional) Get a Hunter.io API key and set `HUNTER_API_KEY` in `.env` for named-contact
   lookups; without it, you'll get generic email guesses only.

### Run it

```
python job_main.py --keywords "IT Project Manager" --location "Dubai, United Arab Emirates" --limit 10
```

(Jooble needs a specific location string — plain `"Dubai"` alone returns no results for
some queries; `"Dubai, United Arab Emirates"` or `"UAE"` works.)

It lists the jobs found, lets you pick which ones to draft for (by number, comma-separated,
or `all`), then prints and saves a draft for each.

### LinkedIn / Naukri Gulf coverage via your own email alerts

Neither platform has a public API, and scraping their pages would violate their terms of
service — this tool doesn't do that. Instead, it can read job-alert emails that **you**
subscribed to, from **your own inbox**, which is a normal intended feature of both sites:

1. On LinkedIn, search for your target role/location, then turn on "Job alert" for that
   search (top of the search results page).
2. On Naukri Gulf, do the same — search, then enable email alerts for that saved search.
3. Set up an app password for your email account:
   - **Gmail**: Google Account → Security → 2-Step Verification → App passwords → generate
     one for "Mail". Use this (not your normal password) as `IMAP_APP_PASSWORD`.
   - **Outlook**: similar — generate an app password if MFA is enabled.
4. Add to `.env`: `IMAP_EMAIL`, `IMAP_APP_PASSWORD`, and `IMAP_HOST` (defaults to
   `imap.gmail.com`).
5. Run with `--include-email-alerts`:
   ```
   python job_main.py --include-email-alerts
   ```
   or click "Check LinkedIn/Naukri Gulf email alerts" on the `/jobs` web page.

This parses the HTML of alert emails using loose heuristics (any job-listing link found in
the email, using its link text as the title). Email templates are undocumented and can
change — if parsing stops finding jobs, the fix is to inspect a real alert email's HTML
source and adjust `jobsearch/email_alerts.py`'s extraction patterns.

## Brand voice / writer prompt

The system prompt that defines tone, audience, and formatting rules for the generated
posts lives in [prompts/writer_prompt.md](prompts/writer_prompt.md) — edit it there to
change the brand voice or how/when TNC Quiz and TNC Track get mentioned, without touching
any code.
