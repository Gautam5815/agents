# CLAUDE.md — LinkedIn Marketing Agent

This file guides Claude Code when working in this repository. It describes what the agent does, how it's structured, and the conventions to follow when building or modifying it.

## Project Overview

An autonomous agent that turns a **topic** into a **published LinkedIn post**, end to end:

1. User provides a topic (e.g. "employee engagement trends 2026" or "why startups need HR tools").
2. Agent researches the topic (web search / news / trends).
3. Agent drafts a LinkedIn post (hook, body, hashtags, CTA) based on the research.
4. Agent generates an accompanying image via the OpenAI Images API.
5. Agent posts the text + image directly to a connected LinkedIn account.

This is being built for **Trynocode Technology**, to support LinkedIn content for **TNC Quiz** (employee engagement/quiz platform) and **TNC Track** (HR/workforce management platform for startups). Posts should generally speak to HR leaders, startup founders, and people-ops audiences.

**Confirmed setup:** Python · posting to a personal LinkedIn profile (not a company page) · Claude Haiku 4.5 (low-cost) for both research (via `web_search`) and writing, each defined as an Agent Skill · OpenAI Images API for the image · **fully autonomous, direct publish — the pipeline runs research → write → image → publish end-to-end with no human review or approval step, and the post goes live on LinkedIn automatically** · **triggered by cron on a schedule — no manual step to start it either.**

## Pipeline / Agent Steps

```
Topic (user input)
   │
   ▼
[1] Research Agent → skills/research/SKILL.md (Claude Haiku 4.5 + web_search + code execution)
   - Claude follows the research skill: searches, gathers findings, cites sources
   - Extract 3-5 key facts/insights worth referencing
   │
   ▼
[2] Writer Agent → skills/writer/SKILL.md (Claude Haiku 4.5)
   - Draft LinkedIn post using research findings, per the writer skill's instructions
   - Hook (first 1-2 lines, must work pre-"see more" cutoff)
   - Body (short paragraphs, no walls of text)
   - Optional stat/insight from research
   - CTA + 3-5 relevant hashtags
   - Match brand voice (see "Brand Voice" below)
   │
   ▼
[3] Image Agent (OpenAI Images API)
   - Turn post's core idea into an image prompt
   - Call OpenAI Images API to generate the image
   - Save locally / get a URL for upload
   │
   ▼
[4] LinkedIn Publish Agent
   - Upload image via LinkedIn API
   - Create UGC post with text + image asset
   - Return the live post URL
```

## Tech Stack

- **Language:** Python 3.11+
- **Orchestration:** simple sequential pipeline (function calls in order) — no heavy agent framework needed
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) — **confirmed for research**, and currently used for writing too. Anthropic's lowest-cost current model. If post quality from the writer step isn't good enough, the writer model can be revisited independently; research stays on Haiku 4.5 either way.
- **Research:** a Claude **Agent Skill** (`skills/research/SKILL.md`) that uses the `web_search` tool to find recent facts/angles on the topic and hands back a structured research summary
- **Copywriting:** a Claude **Agent Skill** (`skills/writer/SKILL.md`) that takes the research summary + brand voice and drafts the LinkedIn post
- **Image generation:** OpenAI Images API (`gpt-image-1` or `dall-e-3`)
- **LinkedIn publishing:** LinkedIn's official REST API, posting as a **personal profile** (`w_member_social` scope — no organization/company-page scope needed)

### Why Agent Skills instead of raw prompts

Agent Skills are `SKILL.md` files (YAML frontmatter + markdown instructions) that Claude loads and follows for a given task, rather than instructions baked into your Python code as strings. Using them for research and writing means:
- Each skill's behavior lives in one editable file, not buried in `.format()` calls
- You (or Claude Code) can iterate on tone/research approach by editing the `.md` file, no code changes needed
- On the Claude API, Skills run through the **code execution tool** — you pass `skill_id`s in the `container` parameter alongside `code_execution` enabled. This is a real infrastructure requirement, not just an organizational nicety — plan for it in `research.py`/`writer.py`.

## Environment Variables

Store all secrets in `.env`, never commit them.

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_PERSON_URN=      # urn:li:person:{your_member_id}
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
```

Add `.env` to `.gitignore` immediately if it isn't already there.

## LinkedIn API Notes (read before implementing the publish step)

- Posting as a personal profile requires the `w_member_social` scope on your access token. Confirm your LinkedIn Developer App has this scope approved before assuming publishing will "just work" — some scopes need LinkedIn's review/approval even for personal-profile posting.
- The post's `author` field in the API payload will be your personal member URN (`urn:li:person:{id}`), not an organization URN.
- Images must be uploaded first via the Assets API (`registerUpload`), then referenced by URN in the post payload — you cannot just attach a raw image URL.
- Access tokens expire (typically 60 days) — plan for refresh/re-auth, don't hardcode a token and assume it'll keep working.
- Rate limits apply per app and per user; don't loop-post in testing.

## Brand Voice

- Practical, founder/HR-leader-to-HR-leader tone — not corporate or salesy.
- Lead with a real insight or stat, not a generic opener like "In today's fast-paced world..."
- Keep paragraphs short (1-3 lines) — LinkedIn readability matters.
- End with a genuine question or CTA, not "Thoughts? 👇" clichés.
- Reference TNC Quiz / TNC Track only when it's a natural fit for the topic — don't force product mentions into every post.

## Autonomy & Safety Net

**Confirmed: direct publish, fully autonomous.** This pipeline runs research → write → image → publish with no manual approval step, and posts straight to a personal LinkedIn profile — the post is live by the time the script finishes. This was an explicit decision (not a default), so lean on these safeguards instead of a human checkpoint:

- **`DRY_RUN=true` env flag:** runs the full pipeline (including calling the LLM and image API) but skips the actual LinkedIn publish call, logging what *would* have been posted. Use this for every test run — only unset it once you trust the output.
- **Logging every step's output** (see "Conventions" below) is not optional here — since nothing gets human eyes before publishing, the logs are the only way to debug a bad post after the fact.
- **Basic content guardrails** in the writer step: length limits, a check that the post isn't empty/malformed, and ideally a simple keyword/profanity filter before the publish call fires.
- Trigger is confirmed as **cron**, but test with **manual runs first** (just run `pipeline.py` by hand, `DRY_RUN=true`) before the cron job is actually turned on — get comfortable with output quality before it's unattended on a schedule.

## File Structure (suggested)

```
/agent
  research.py         # step 1 — calls Claude w/ skills/research skill
  writer.py            # step 2 — calls Claude w/ skills/writer skill
  image.py             # step 3 — OpenAI Images API
  linkedin.py           # step 4 — auth, upload, publish
  pipeline.py           # orchestrates 1-4, entry point
/skills
  /research
    SKILL.md             # research approach, what makes a good source/fact
  /writer
    SKILL.md             # brand voice, post structure, formatting rules
.env.example
requirements.txt
CLAUDE.md
```

## Conventions

- Keep each step as an independently callable/testable function — don't couple research, writing, image gen, and publishing into one monolith.
- Log every step's output (research summary, draft text, image prompt, final post URL) so a bad post can be traced back to its cause.
- Never commit real API keys, tokens, or example posts containing real customer/company data.
- Fail loudly: if the LinkedIn publish step errors, do not silently retry-loop — surface the error.

## Open Decisions (fill in as the project takes shape)

- [x] **Trigger method — confirmed: cron (scheduled, automatic).** Combined with the confirmed direct-publish decision above, this means the pipeline runs on a schedule with **zero human involvement at any point** — no one triggers it and no one reviews it before it's live on LinkedIn. Rely on the safeguards in "Autonomy & Safety Net" (logging, `DRY_RUN` testing before going live, content guardrails) since there is no other checkpoint. Recommend validating output quality with manual runs first, then switching the actual cron job on once trusted — don't schedule cron against untested code.
- [ ] **Writer model** — currently Haiku 4.5 (same as research). If output quality isn't strong enough on real posts, worth a fallback to Sonnet for the writer step specifically. **Research stays on Haiku 4.5 regardless — confirmed.**