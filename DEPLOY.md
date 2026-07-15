# Deploying the PO → Sales Order Agent (Vercel split architecture)

This project is split into two deployables:

```
sales-order-agent-vercel/
├── frontend/   → Next.js app        → deploy to Vercel      (the public URL you share)
└── backend/    → FastAPI + agents    → deploy to Render      (always-on API the frontend calls)
```

**Why the backend goes on Render, not Vercel.** Your pipeline makes a multi-second
LLM call, streams a live agent timeline (SSE), and writes Sales Orders to disk.
Vercel's serverless functions are short-lived (10s on Hobby), don't stream well,
and have an ephemeral/read-only filesystem — so the API belongs on an always-on
host. Vercel still hosts the app your users see; Render runs the companion API.
This is the standard "frontend on Vercel + API elsewhere" pattern.

> An **all-Vercel** option is included (`backend/vercel.json` + `backend/api/index.py`)
> if you must keep everything under Vercel — see the last section for its caveats.

There are a few steps only **you** can do (they need your accounts and credentials):
creating the GitHub/Render/Vercel accounts, connecting the repo, entering your
Mistral API key, and accepting each platform's terms. Everything below is copy-paste.

---

## Step 0 — Push to GitHub

From the project root:

```bash
git init
git add .
git commit -m "PO to Sales Order agent — split architecture"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

`.gitignore` files already exclude `.env`, `node_modules/`, `.next/`, and the
local SQLite DB, so no secrets or build junk are committed.

---

## Step 1 — Deploy the backend on Render

**Option A — Blueprint (uses `backend/render.yaml`, one click):**

1. Go to <https://dashboard.render.com> → **New → Blueprint**.
2. Connect your repo. Render reads `backend/render.yaml` and proposes the service.
3. Click **Apply**. It builds and starts `uvicorn app:app`.

**Option B — Manual web service:**

1. **New → Web Service**, connect the repo.
2. Set **Root Directory** = `backend`.
3. **Build Command** = `pip install -r requirements.txt`
4. **Start Command** = `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Add a **Disk** (mount path `/var/data`, 1 GB) so orders persist across restarts.

**Environment variables** (Render dashboard → your service → Environment):

| Key | Value |
|---|---|
| `LLM_PROVIDER` | `mock` (or `mistral` for live extraction) |
| `MISTRAL_API_KEY` | *your key* (only needed for live mode) |
| `MISTRAL_MODEL` | `mistral-large-latest` |
| `ENABLE_OCR` | `false` |
| `DB_PATH` | `/var/data/sales.db` |
| `FRONTEND_ORIGIN` | *(fill in after Step 2 with your Vercel URL)* |

When it's live you'll get a URL like `https://po-sales-order-api.onrender.com`.
Verify it: opening that URL should return `{"status":"ok",...}`.

> The free tier sleeps after inactivity, so the first request after idle takes
> ~30s to wake. Fine for a demo; upgrade the plan to keep it warm.

---

## Step 2 — Deploy the frontend on Vercel

1. Go to <https://vercel.com/new> and import the same repo.
2. Set **Root Directory** = `frontend`. Vercel auto-detects Next.js (no config needed).
3. Under **Environment Variables**, add:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | your Render URL, e.g. `https://po-sales-order-api.onrender.com` |

4. **Deploy.** You'll get your public URL: `https://<your-app>.vercel.app`.

> `NEXT_PUBLIC_API_URL` is read at build time. If you change it later, redeploy
> (Vercel → Deployments → Redeploy) so the new value is baked in.

---

## Step 3 — Lock down CORS

Back on Render, set `FRONTEND_ORIGIN` to your exact Vercel URL
(e.g. `https://your-app.vercel.app`) and save — Render redeploys automatically.
This restricts the API to your frontend instead of the open `*` default.

That's it — open the Vercel URL, click a sample PO, and run the pipeline.

---

## Going live with Mistral (optional)

The app ships in **mock mode**, which extracts deterministically offline — great
for a reliable demo. For real LLM extraction, on **Render** set:

```
LLM_PROVIDER = mistral
MISTRAL_API_KEY = <your key>
```

If the key is missing the backend automatically falls back to mock rather than
erroring, so the demo can't hard-crash.

---

## Local development

Two terminals:

```bash
# terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # defaults to mock mode
uvicorn app:app --reload --port 8000

# terminal 2 — frontend
cd frontend
npm install
cp .env.local.example .env.local   # points at http://localhost:8000
npm run dev                          # http://localhost:3000
```

---

## All-Vercel option (advanced, with caveats)

If you must host the backend on Vercel too, `backend/vercel.json` and
`backend/api/index.py` are included. Import the repo a second time with
**Root Directory = `backend`**, and set `DB_PATH=/tmp/sales.db` (the only
writable path on Vercel). Caveats:

- **No persistence** — `/tmp` is wiped between invocations, so Sales Orders and
  duplicate-detection history reset constantly. Point at a hosted Postgres to fix
  this (requires swapping the SQLite layer in `database/db.py`).
- **No live timeline** — the SSE route (`/api/process/stream`) won't stream under
  serverless; the frontend automatically falls back to the non-streaming
  `/api/process` route, so you lose the animated agent timeline but still get the
  result.
- **10s limit** — long live-Mistral calls can time out on the Hobby plan.

For a smooth demo, prefer the Render backend above.
