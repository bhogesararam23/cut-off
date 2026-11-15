# Deploying Cut Off

Two pieces, hosted separately and deployed by GitHub Actions (`.github/workflows/deploy.yml`):

| Piece | Where | How |
|---|---|---|
| API (`api/`) | Azure App Service for Containers (Linux) | A Docker image built from `api/Dockerfile`, pushed to Azure Container Registry, tagged with the commit hash |
| Website (`web/`) | Cloudflare | Either built by Cloudflare from this repository, or by the Website job here (`npm run build`, then `wrangler pages deploy web/dist`) when `CF_PAGES_PROJECT` is set |

The website works on its own from the data files it ships with. The API is optional: if it is down or asleep the site falls back to its own copy.

## How a deploy runs
1. A push to `main` runs CI (`ci.yml`). When CI succeeds, `deploy.yml` starts for that exact commit. It can also be started by hand from `main` (Actions, Deploy, Run workflow). It never runs for pull requests, so forks cannot reach any secret.
2. Job **api**: log in to Azure without a stored password (OIDC), build the image, push `cutoff-api:<commit hash>` to the registry, point the web app at that image, set its app settings, restart, then call `/api/health` for up to 3 minutes and fail if it does not answer `ok`.
3. Job **web**: `npm ci`, `npm test`, `npm run build` (fails on mock data), deploy to Cloudflare Pages, then check the site answers 200 and `/data/panama-2026/stats.json` says `"mock": false`.

The two jobs do not depend on each other: if the API deploy fails, the website still deploys, and the failed job is shown in the run.

## The image
`docker build -f api/Dockerfile -t cutoff-api .` (run from the repository root). It uses a pinned `python:3.11-slim`, installs only `api/requirements.txt`, and copies only `api/*.py` and the data in `web/public/data`. It runs as a non-root user (uid 10001) on port 8000, has a health check, and the build fails if `event.json` or `stats.json` says `"mock": true`. `.dockerignore` keeps raw radar files, work files, pipeline code, environment files and local tooling out of the build.

## Secrets and variables
All credentials live only in the repository's GitHub settings (Settings, Secrets and variables, Actions). None is stored in the code, the image or the logs.

Secrets:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Variables (not secret):
- `AZURE_RESOURCE_GROUP`
- `AZURE_WEBAPP_NAME`
- `ACR_NAME` (registry name, without `.azurecr.io`)
- `CF_PAGES_PROJECT` (optional: when it is not set the Website job is skipped, for example because Cloudflare builds the site from Git itself)
- `SITE_ORIGIN` (the website's origin, for example `https://<project>.pages.dev`; no path, no trailing slash). It becomes the API's allowed CORS origin and is used for the site check.
- `API_URL` (the API's `https://<app>.azurewebsites.net` address; the site build adds it to its content security policy. Leave it unset to build a site that only uses its own files.)

The Azure login has no client secret: GitHub proves its identity with a short-lived token, and Azure trusts only this repository's `main` branch (a federated credential). The identity has Contributor on the one resource group and AcrPush on the registry. The web app pulls the image from the registry with its own managed identity (AcrPull).

## One-time setup
The numbered steps are in the project hand-off notes; in short: create the resource group, registry, App Service plan and Web App for Containers; create the Entra app registration with a federated credential for `main` and give it the two roles; create the Cloudflare Pages project and a token limited to Pages edit on that account; add the secrets and variables above; run the workflow.

Do not switch on App Service's own CORS feature: the API applies its own allowlist from `CORS_ORIGINS`.

## Checking by hand
```bash
curl https://<app-name>.azurewebsites.net/api/health
curl -I https://<your-site>.pages.dev/
```
The first should answer `{"status":"ok","version":"0.1.0"}`. If the API fails, `az webapp log tail --name <app-name> --resource-group <resource-group>` shows the server log.

## Live addresses
- Website: https://cut-off.bhogesara-ram23.workers.dev
- API: https://cutoff-api-26-ram26.azurewebsites.net (`/api/health`, interactive docs at `/docs`). Its allowed CORS origin is the website's address above.
- For the website to read its data through the API, set `VITE_API_URL=https://cutoff-api-26-ram26.azurewebsites.net` as a build variable where the site is built. Without it the website uses the files it ships with, which are the same files.

## Before submitting
- Check that the live website shows the same numbers as `stats.json` in this repository (the key facts at the top of the page).
- Add the sources actually used to `docs/citations.md` and finish `docs/si-log.md`.
- Keep every link live and unchanged through judging: do not force-push or delete anything after submitting.

## Costs and cleanup
Check the prices for your region before choosing a plan. To remove everything on Azure: `az group delete --name <resource-group>`.
