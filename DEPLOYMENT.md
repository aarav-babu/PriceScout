# PriceScout deployment

[Public site](https://pricescout-urwq.onrender.com/) · [Architecture](README.md#system-architecture)

The hosted app runs `public_app:app` on Render Free and stores accounts/products in Neon Free PostgreSQL. The research MySQL/Celery application is a separate deployment. Private dashboard identifiers and credential values are intentionally absent from this document.

## Where secrets belong

| Secret | Storage | Used by |
| --- | --- | --- |
| `RENDER_DEPLOY_HOOK` | GitHub repository → Settings → Secrets and variables → Actions | The deployment job only |
| `DATABASE_URL` | Render service → Environment | Public app → Neon pooled PostgreSQL over TLS |
| `SECRET_KEY` | Render service → Environment | Flask session signing and CSRF protection |

GitHub needs permission to trigger a deployment, not access to user data or the session-signing key. Do not duplicate database credentials in GitHub. Never put secret values in Markdown, committed `.env` files, workflow YAML, command arguments, or logs. The local `.env.example` contains names and example settings only.

A Render deploy hook is itself a secret: anyone holding it can trigger a release. Copy it from the service’s Settings into the GitHub Actions secret. The workflow fails clearly if it is missing. Rotate a compromised hook in Render and update the GitHub secret. Rotate a compromised database password in Neon and replace `DATABASE_URL` in Render; replacing `SECRET_KEY` signs existing users out.

## Merge-to-deploy workflow

1. Open a pull request against `main`.
2. GitHub Actions runs the full unit suite, a production Gunicorn startup check, and Gitleaks secret scanning. PRs never deploy.
3. Merge after checks pass. The merged commit receives the same checks.
4. The **Deploy and verify production** job calls the secret Render deploy hook with that exact commit SHA. Queued runs skip a commit if `main` has already advanced.
5. Render installs the public requirements, repeats public tests, and starts the app.
6. GitHub polls `/healthz` until its `revision` matches the tested commit. Hook acceptance alone does not count as deployment success. A failure or timeout is visible in Actions.

Workflow: `.github/workflows/ci.yml`. Deploy script: `scripts/deploy_render.py`. Pinned actions use read-only repository permissions. Deployments are serialized; the script does not print the hook URL or its response. Runtime credentials are never needed by CI.

Keep the Render service’s source branch at `main`, **Auto-Deploy off**, and the Blueprint’s **Auto Sync off**. GitHub Actions owns application releases. This avoids a second deployment path bypassing checks or racing the workflow. Infrastructure changes to `render.yaml` require a deliberate Blueprint sync after checks pass; routine application changes require only a merge. The deploy hook works without installing Render’s GitHub app.

## Runtime settings

| Setting | Value |
| --- | --- |
| Runtime / plan | Python 3 / Free |
| Python | `3.11.16` |
| Build | `pip install -r requirements-public.txt && python -m unittest discover -s tests -p 'test_public*.py' -v` |
| Start | `gunicorn public_app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 60 --access-logfile - --error-logfile -` |
| Health check | `/healthz` |
| `TRUST_PROXY` | `1` behind Render’s proxy |
| Database | Neon pooled PostgreSQL connection string with TLS |

Use one worker/instance until caching, throttling, and fetch coordination move to a shared store. Render’s disk is temporary and must not hold production accounts. The app fails account operations safely if the hosted database configuration is absent; public search remains available.

## Storage and account limits

The account store initially creates the namespaced `public_users` and `public_products` tables. It does not migrate legacy accounts or alter existing columns. Future schema changes need explicit migrations. Passwords are hashed, state-changing forms require CSRF tokens, and production session cookies use Secure, HttpOnly, and SameSite. Product queries are scoped to the signed-in account.

Registration, sign-in, and sign-out are available. Email verification, password recovery, and account/product deletion are not implemented yet. Phones and laptops save details but do not produce price estimates.

## Verification and rollback

After changes, verify public pages, registration/sign-in, saving both categories, private collection access, the deployed revision, and a real car search. Local tests use temporary SQLite databases and mocked source HTML; they do not validate Neon connectivity or current source availability. Production account persistence and live car search were separately verified for the initial account release.

A failed Render build leaves the previous release running. For a bad application release, roll back to a known successful deployment in Render, then revert the change through a PR. A web rollback does not undo database writes or migrations. Avoid merging another release while investigating a rollback.

Gitleaks scans changes in CI. For a local history audit:

```bash
gitleaks git . --log-opts='--all' --redact=100
```

If a credential is committed, rotate it first, then remove it from branch/tag history. History rewriting cannot retract existing clones, forks, or GitHub’s retained pull-request views; GitHub Support may be needed for server-side cleanup. Never post an exposed secret in the cleanup report.

## Free-tier behavior

Render can sleep after inactivity, so the first request may take around a minute. Neon can also suspend and resume idle database compute. Both services impose quotas; free plans do not provide an always-on production guarantee. See [Render Free](https://render.com/docs/free) and [Neon plans](https://neon.com/pricing).

Car results are a first-page sample, cached for five minutes with the original check time. The source may include nearby locations; the app shows asking prices, not completed sales. Upstream layout changes or outages produce an explicit unavailable state.

## Local development

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-public.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python public_app.py
```

Open `http://127.0.0.1:5002`. Local accounts use the ignored `instance/accounts.db` unless `DATABASE_URL` is set. Use the research Docker Compose stack only when working on the separate pipeline.
