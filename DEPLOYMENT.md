# PriceScout deployment and CI/CD

**Public site:** https://pricescout-urwq.onrender.com

The Render Free service runs `public_app:app` from **main**. Neon Free PostgreSQL
stores accounts and saved phones/laptops. The MySQL/Celery research application
remains separate and is not loaded by the public web process.

## Production resources

- [Render service](https://dashboard.render.com/web/REDACTED_RENDER_SERVICE):
  `pricescout`, Python, Free, Oregon.
- [Render Blueprint](https://dashboard.render.com/blueprint/REDACTED_RENDER_BLUEPRINT):
  `PriceScout public beta`, following `main` and `render.yaml`.
- [Neon project](https://console.neon.tech/app/projects/REDACTED_NEON_PROJECT):
  `PriceScout`, Free, AWS Oregon, `production` branch, `neondb` database.

The first account release was verified on the hosted site: registration, secure
session cookies, saving both product categories, signing out and back in with a
fresh session, retrieving the saved collection, and a live car search all passed.
These checks confirm the Render-to-Neon connection; local SQLite tests alone do
not validate production database connectivity.

Accounts currently support registration, sign-in, and sign-out. Email verification
and password recovery are not implemented yet. Existing research-app accounts
must register separately on the public site.

## Everyday workflow

1. Create a feature branch from the latest `main`.
2. Make changes and open a pull request against `main`.
3. Wait for **Tests and production startup** to pass. This runs the entire test
   suite, including the existing market-model tests, and starts Gunicorn to check
   the home page and `/healthz`.
4. Merge the pull request. The workflow runs again on the merged commit.
5. Render's **After CI Checks Pass** setting automatically builds and deploys that
   `main` commit. Failed CI does not deploy.
6. Check the Render deploy status and `/healthz`; its `revision` field identifies
   the running commit. A successful GitHub test run is not itself deployment success.

The workflow is `.github/workflows/ci.yml`. It uses read-only repository
permissions, pinned action commits, no production secrets, and cancels superseded
checks for the same branch/PR. PR checks never deploy the PR to production.

`render.yaml` keeps `branch: main` and `autoDeployTrigger: checksPass`. The Render
service and its Blueprint must both follow `main`, with a connected GitHub
provider. The Blueprint must not remain linked to the old launch branch or a
later sync could restore the old configuration.

## Runtime configuration

| Setting | Value |
| --- | --- |
| Runtime / plan | Python 3 / Free |
| Build command | `pip install -r requirements-public.txt && python -m unittest discover -s tests -p 'test_public*.py' -v` |
| Start command | `gunicorn public_app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 60 --access-logfile - --error-logfile -` |
| Health check | `/healthz` |
| `PYTHON_VERSION` | `3.11.16` |
| `TRUST_PROXY` | `1` behind Render's proxy |
| `SECRET_KEY` | Persistent random secret stored only in Render |
| `DATABASE_URL` | Neon pooled PostgreSQL URL with TLS, stored only in Render |

No deploy hook or Render API token is needed in GitHub. Render watches successful
GitHub checks. The build repeats public tests as a second gate, including for a
manual deploy. A failed build leaves the existing deployment running.

Use one worker/instance for the beta. Search caching and throttling are
process-local; multiple workers require a shared cache/rate limiter first.

## Accounts and products

On first use, the account store creates `public_users` and `public_products` if
missing. It does not modify the legacy MySQL schema. Users register with an email
and password; passwords are hashed with Werkzeug, forms require CSRF tokens,
and HTTPS sessions use secure/HttpOnly/SameSite cookies. Product reads are scoped
to the signed-in account. Legacy MySQL accounts are not migrated automatically.

Phone and laptop forms save specifications and notes; their result pages clearly
say **Pricing unavailable**. No placeholder valuation is generated. The existing
authorized market-data pipeline can be integrated later with its required
provider credentials, market settings, and worker infrastructure.

Do not rotate `SECRET_KEY` during ordinary deploys: rotation signs everyone out.
Do not commit database credentials or copy them into GitHub Actions. Render's
ephemeral disk is used for neither accounts nor saved products. If database
configuration is missing, account operations return a friendly 503 and public
car search remains available. Schema changes beyond these initial tables require
an explicit migration; `create_all()` does not alter existing columns.

## Price behavior and free-tier limits

Car searches read a first-page sample of current Cars24 asking prices. Current
prices are distinguished from EMI and old prices. Results are cached for five
minutes with the original timestamp; failures never return sample/fake prices.
The source can include nearby/out-of-city listings. Check each seller location.

Render Free sleeps after 15 minutes without traffic, so the next visit can take
about a minute. Neon can also suspend idle database compute and wake on demand.
Both have free-tier quotas; neither free plan is an always-on production SLA.
See [Render limits](https://render.com/docs/free) and [Neon pricing](https://neon.com/pricing).

## Verification and rollback

After a deployment, check home, About, registration/sign-in, saving both product
categories, private collection access, `/healthz`, and one live car search from
Render's network. Do not treat an upstream source outage as fabricated inventory.

If a release fails, use Render's previous successful deploy to roll back the web
service, then revert the problematic change through a PR to `main`. A rollback
does not undo database writes or schema changes. Confirm auto-deploy remains
**After CI Checks Pass** before resuming normal merges.

## Local development

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-public.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python public_app.py
```

Open `http://127.0.0.1:5002`. Local accounts use `instance/accounts.db` unless
`DATABASE_URL` is set. The test suite uses temporary isolated databases; it does
not need Neon credentials. The hosted app requires both `DATABASE_URL` and
`SECRET_KEY`. Use the old Docker Compose stack only for research-pipeline work.
