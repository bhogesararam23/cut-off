# Deploying Cut Off

Two pieces, hosted separately:

| Piece | Where | How |
|---|---|---|
| Website (`web/`) | Cloudflare Workers Builds (static assets) | Cloudflare builds the site from this repository on every push to `main`: root directory `web`, build `npm ci && npm run build`, deploy command `npx wrangler deploy --assets=dist`, build variable `NODE_VERSION=24` |
| API (`api/`) | Azure App Service for Containers (Linux, region eastasia) | GitHub Actions (`.github/workflows/deploy.yml`) builds a Docker image from `api/Dockerfile`, pushes it to Azure Container Registry tagged with the commit hash, and points the web app at it |

The website works on its own from the data files it ships with. The API is optional: if it is down or asleep the site falls back to its own copy.

## Live addresses
- Website: https://cut-off.bhogesara-ram23.workers.dev
- API: https://cutoff-api-26-ram26.azurewebsites.net (`/api/health`, interactive docs at `/docs`). Its allowed CORS origin is the website's address above.

## The website on Cloudflare
- The Cloudflare GitHub app needs access to this repository.
- The build variable `VITE_API_URL` (the API address above, not secret) makes the site read its data through the API and adds that address to the site's content security policy (`web/scripts/finish-build.ts`). Without it the site uses the files it ships with, which are the same files.
- The security headers (content security policy, `X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors`) are in `web/public/_headers`.

## The API on Azure
1. A push to `main` runs CI (`ci.yml`). When CI succeeds, `deploy.yml` starts for that exact commit. It can also be started by hand from `main`. It never runs for pull requests, so forks cannot reach any secret.
2. Job **api**: log in to Azure without a stored password (OIDC), build the image, push `cutoff-api:<commit hash>` to the registry, point the web app at that image, set its app settings (`WEBSITES_PORT`, `DATA_DIR`, `CORS_ORIGINS`, `PUBLIC_URL`), restart, then call `/api/health` for up to 3 minutes and fail if it does not answer `ok`.
3. Job **web** (optional): only runs when the repository variable `CF_PAGES_PROJECT` is set; it then builds the site and deploys it with `wrangler pages deploy`. It is skipped otherwise, because Cloudflare builds the site itself.

### The image
`docker build -f api/Dockerfile -t cutoff-api .` (run from the repository root). It uses a pinned `python:3.11-slim`, installs only `api/requirements.txt`, and copies only `api/*.py` and the data in `web/public/data`. It runs as a non-root user (uid 10001) on port 8000, has a health check, and the build fails if `event.json` or `stats.json` says `"mock": true`. `.dockerignore` is an allowlist, so raw radar files, work files, pipeline code and environment files never enter the build.

### Secrets and variables
All credentials live only in the repository's GitHub settings (Settings, Secrets and variables, Actions). None is stored in the code, the image or the logs. Only names are listed here.

Secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`. The optional web job also needs `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.

Variables (not secret): `AZURE_RESOURCE_GROUP`, `AZURE_WEBAPP_NAME`, `ACR_NAME` (registry name, without `.azurecr.io`), `SITE_ORIGIN` (the website's origin, no path and no trailing slash; it becomes the API's allowed CORS origin). Optional for the web job: `CF_PAGES_PROJECT`, `API_URL`.

The Azure login has no client secret: GitHub proves its identity with a short-lived token, and Azure trusts only this repository's `main` branch (a federated credential). The identity has Contributor on the one resource group and AcrPush on the registry. The web app pulls the image from the registry with its own managed identity (AcrPull). Do not switch on App Service's own CORS feature: the API applies its own allowlist from `CORS_ORIGINS`.

### One-time setup (Azure CLI, placeholders only)
```bash
az group create --name <resource-group> --location eastasia
az acr create --resource-group <resource-group> --name <registry> --sku Basic
az appservice plan create --resource-group <resource-group> --name <plan> --is-linux --sku B1
az webapp create --resource-group <resource-group> --plan <plan> --name <app-name> --container-image-name <registry>.azurecr.io/cutoff-api:bootstrap --container-registry-url https://<registry>.azurecr.io
az webapp identity assign --resource-group <resource-group> --name <app-name>
```
Then give the app's managed identity `AcrPull` on the registry, create an Entra app registration with a federated credential for this repository's `main` branch, give it `Contributor` on the resource group and `AcrPush` on the registry, and add the secrets and variables above.

## Checking by hand
```bash
curl https://<app-name>.azurewebsites.net/api/health
curl -I https://<your-site>/
```
The first should answer `{"status":"ok","version":"0.1.0"}`. The live website should show the same numbers as `web/public/data/panama-2026/stats.json`.

## Costs and cleanup
Check the prices for your region before choosing a plan. To remove everything on Azure after judging: `az group delete --name <resource-group>`, then delete the Entra app registration and the `AZURE_*` secrets. The website does not depend on the API.
