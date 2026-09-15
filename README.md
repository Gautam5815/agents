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

## Brand voice / writer prompt

The system prompt that defines tone, audience, and formatting rules for the generated
posts lives in [prompts/writer_prompt.md](prompts/writer_prompt.md) — edit it there to
change the brand voice or how/when TNC Quiz and TNC Track get mentioned, without touching
any code.
