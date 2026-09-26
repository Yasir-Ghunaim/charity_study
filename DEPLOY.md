# Deploying the study for free: Vercel + Render + Neon

```
participant ─► Vercel (website, web/) ─► Render (API, api/) ─► Neon (Postgres: participant data)
                                                      └────► OpenAI API (ChatGPT, the assistant)
```

Everything here is on a free plan except the OpenAI API, which is billed per
use. Only studies with the assistant use it. Cost depends on the model you
choose, so check OpenAI's pricing page and set a monthly limit.

You need accounts on GitHub (the repo), Neon, Render, Vercel and the OpenAI
platform (platform.openai.com). A ChatGPT Plus subscription does not include
API access. The steps take about 20 minutes.

---

## 1. Database: Neon

1. Sign up at https://neon.tech and create a project (any name). Pick the
   region closest to Render's; Frankfurt pairs well with Render's Frankfurt.
2. On the project dashboard, click **Connect** and copy the connection string.
   It looks like `postgresql://user:password@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`.

You don't need to create any tables; the API creates them on first start.

## 2. API: Render

1. Push this repo to GitHub (already at `Yasir-Ghunaim/charity_study`).
2. Go to https://dashboard.render.com, then **New → Blueprint**. Pick the repo;
   Render reads `render.yaml`.
3. Fill in the values it asks for:
   - `DATABASE_URL`: the Neon string from step 1
   - `OPENAI_API_KEY`: from https://platform.openai.com/api-keys. Create a key for this project only,
     and set a monthly usage limit under Settings → Limits.
   - `OPENAI_MODEL`: the model name as shown in your OpenAI dashboard.
   - `STUDY_CONTACT_AR` and `STUDY_CONTACT_EN`: your name, institution and email, as participants should see them
4. Deploy. When it finishes, note the service URL, e.g.
   `https://giving-study-api.onrender.com`.
5. Check it: open `https://<your-service>.onrender.com/api/health`. It should show `"ok": true`.
6. Copy **`STUDY_ADMIN_TOKEN`**: service → Environment → reveal. You need it for `/admin`.

## 3. Website: Vercel

1. Go to https://vercel.com/new, import the same GitHub repo, and set:
   - **Root Directory**: `web`
   - **Environment Variable**: `API_URL` = your Render URL from step 2.4 (no trailing slash)
2. Deploy. Your study link is the Vercel URL, e.g. `https://giving-study.vercel.app`.

## 4. Design your studies

1. Open `<vercel-url>/admin` and sign in with the admin token.
2. Click **New study**. Choose an ID (it appears in the link), the interface
   (assistant only, assistant + browse, or browse only), the wallet, the AI
   message limit, and which surveys to include. New studies start as **draft**.
3. Set a study to **open** when you're ready, and send participants its link
   (**copy link**): `<vercel-url>/s/<study-id>`.
4. Once a study has participants, its design is locked so everyone saw the same
   protocol. To change it, create a new study. Close a study to stop recruiting.

## 5. Test before recruiting

1. Open each study's link in a private window and go through the whole study:
   consent, pre-survey, a few questions to the assistant, allocations, finish,
   post-survey.
2. In `/admin`, confirm your test participant appears under that study.
   Download the CSVs and check they open correctly.
3. Delete the test data so the dataset starts clean. In Neon's SQL editor, run
   this. Your study designs are kept; only participant data is removed.
   ```sql
   TRUNCATE survey_responses, allocations, study_events, agent_turns, participants;
   ```

## 6. Keep it awake (recommended)

Render's free service sleeps after 15 minutes without traffic, and the next
visitor waits about a minute while it wakes. To avoid that during the study,
create a free monitor at https://uptimerobot.com (or https://cron-job.org)
that requests `https://<your-service>.onrender.com/api/health` every 5–10
minutes. The free plan's 750 hours a month cover one service running all month.

## 7. During the study

- **Back up regularly.** Download the CSVs from `/admin` (for example daily).
  Neon's free plan keeps only a short history for recovery.
- **Deletion requests.** Participants quote their code. In Neon's SQL editor,
  replace `CODE` with their code and run:
  ```sql
  DELETE FROM survey_responses WHERE participant_id = (SELECT id FROM participants WHERE code = 'CODE');
  DELETE FROM allocations      WHERE participant_id = (SELECT id FROM participants WHERE code = 'CODE');
  DELETE FROM study_events     WHERE participant_id = (SELECT id FROM participants WHERE code = 'CODE');
  DELETE FROM agent_turns      WHERE participant_id = (SELECT id FROM participants WHERE code = 'CODE');
  DELETE FROM participants     WHERE code = 'CODE';
  ```
- **Don't change the consent text, surveys or assistant mid-study.** Each record
  stores the consent version and the assistant's prompt version. If you must
  change one, bump `CONSENT_VERSION` / `SURVEY_VERSION` in
  `api/app/study/config.py` so the data shows who saw what.

## Limits of the free setup

- **Search runs on keywords only on Render** (no local embedding model): 90% on
  the relevance test, versus 100% with the model locally. Claude usually
  compensates by rephrasing searches.
- **Cold starts** apply if you skip step 5.
- **Neon's free plan has 0.5 GB of storage**, enough for thousands of participants.
