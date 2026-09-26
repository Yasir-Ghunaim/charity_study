# Giving Study: how people choose charity campaigns

A research platform for studying how people choose charity campaigns, to inform
the design of recommendation systems for Arabic-first donation platforms.

Participants see a consent form, pick a nickname, and answer a short
pre-survey. They then get a **virtual wallet (1,000 virtual SAR)** and allocate
it to the campaigns they choose, helped by an AI assistant. A post-survey
closes the session. Every interaction is logged for analysis.

> All campaigns and charities are synthetic, and the money is virtual. Nothing
> is paid or collected.

## Participant flow

| step | route | what's recorded |
|---|---|---|
| Consent (Arabic/English) | `/` | consent version and timestamp, nickname, language |
| Pre-survey | `/survey/pre` | demographics and giving habits |
| Allocation with the assistant | `/study`, `/campaigns/[id]` | every agent turn (question, tool calls, campaigns shown, answer, engine, model, prompt version, latency), allocations, detail-page dwell time, language switches |
| Post-survey | `/survey/post` | 8 Likert items (helpfulness, trust, control, pressure…), whether real money would change choices, open answers |
| Thank you | `/done` | participation code for withdrawal requests |

Participants can withdraw at any point from the footer, which deletes their data.

## Run locally

```bash
cd api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env              # set STUDY_ADMIN_TOKEN, contacts, engine
.venv/bin/uvicorn app.main:app --port 8000

cd web && npm install && npm run dev      # http://localhost:3000
```

Local models (optional): `ollama pull qwen3:4b-instruct-2507-q4_K_M` for the
agent, and `ollama pull bge-m3` for search by meaning.

## Deploying

See [DEPLOY.md](DEPLOY.md) for free hosting on Vercel (website), Render (API) and
Neon (Postgres for participant data).

## Before recruiting

- Get ethics or IRB approval if your institution requires it. The consent text
  lives in `api/app/study/config.py` and is versioned (`CONSENT_VERSION`).
- Fill in `STUDY_CONTACT_AR` and `STUDY_CONTACT_EN` (shown in the consent form).
- Fix the engine with `AGENT_PROVIDER=anthropic` (plus `ANTHROPIC_API_KEY`) so
  every participant gets the same assistant. Each turn logs its engine, model
  and prompt version.
- Set a long random `STUDY_ADMIN_TOKEN`.

## Data export

Open `/admin`, enter `STUDY_ADMIN_TOKEN`, and download the CSVs:
`participants`, `surveys` (one column per question), `allocations`, `events`,
`agent_turns` and `campaigns`. All are UTF-8 with a BOM, so Excel shows Arabic
correctly.

## Code

- `api/app/study/`: protocol config (consent, surveys, wallet, limits) and the
  study API. The participant is identified by an httpOnly cookie, never by the
  request body.
- `api/app/agent/`: tools and the agent loop. The agent is instructed to stay
  neutral and never moves money itself.
- `api/app/search.py`: Arabic/English search combining keywords and meaning.
  Check it with `python -m app.search_eval`.
- `web/`: Next.js 16 participant app, Arabic (RTL) and English (LTR).
