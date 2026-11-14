# Deploying Cut Off

Two pieces, hosted separately:

| Piece | Where | What it does |
|---|---|---|
| Website (`web/`) | Cloudflare Pages | The map app. A static site: it can show everything on its own from the data files it ships with. |
| API (`api/`) | Azure App Service (Linux, Python) | A small read-only service that serves the same data files. Optional: if it is down or asleep the website falls back to its own copy of the files. |

Nothing here needs a secret in the repository. Each service is configured in its own dashboard. Turn on two-factor sign-in on both accounts.

**Order:** push the repository, then create the API, then the website, then tell the API the website's address.

## Before you start
1. The data in `web/public/data/` must be real results, not mock data. A real processing run writes `"mock": false` into `event.json` and `stats.json`. The API packaging script and the website build (when asked) both stop if they still see mock data.
2. The tests pass: `cd pipeline && pytest -q`, `cd api && pytest -q`, `cd web && npm test && npm run build`.
3. Push the repository to GitHub (public).

## 1. API on Azure App Service

> These commands were written for the Azure CLI (`az`) but have **not been run**: it was not installed where this was prepared. Read the output of each command; if one is rejected, the portal offers the same settings (App Services, then Create, then Web App).

Choose a unique app name (it becomes `https://<app-name>.azurewebsites.net`) and a region near you.

```bash
az login
az group create --name cut-off-rg --location <region>
az appservice plan create --name cut-off-plan --resource-group cut-off-rg --sku F1 --is-linux
az webapp create --name <app-name> --resource-group cut-off-rg --plan cut-off-plan --runtime "PYTHON:3.11"
```

The free tier (`F1`) has a daily compute limit and no "always on", so the first request after a quiet spell is slow. That is fine here because the website falls back to its own files. If the free tier is not offered for your subscription or region, use `B1`.

Settings (replace the two addresses once you know them; `CORS_ORIGINS` must be the website's exact origin, with no path and no `*`):

```bash
az webapp config set --name <app-name> --resource-group cut-off-rg --startup-file "python -m uvicorn main:app --host 0.0.0.0 --port 8000"
az webapp config appsettings set --name <app-name> --resource-group cut-off-rg --settings \
  DATA_DIR=data WEBSITES_PORT=8000 SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  CORS_ORIGINS=https://<your-site>.pages.dev PUBLIC_URL=https://<app-name>.azurewebsites.net
az webapp update --name <app-name> --resource-group cut-off-rg --https-only true
az webapp config set --name <app-name> --resource-group cut-off-rg --min-tls-version 1.2 --ftps-state Disabled
```

Do not switch on App Service's own CORS feature: the API applies its own allowlist.

Package and deploy (from the repository folder). The packaging script puts the API code, its runtime requirements and the data files into one zip, and refuses mock data:

```bash
python scripts/package_api.py
az webapp deploy --name <app-name> --resource-group cut-off-rg --src-path build/api-package.zip --type zip
```

Check it:

```bash
curl https://<app-name>.azurewebsites.net/api/health
```

It should answer `{"status":"ok","version":"0.1.0"}`. Open `https://<app-name>.azurewebsites.net/docs` to see every endpoint. If something fails, `az webapp log tail --name <app-name> --resource-group cut-off-rg` shows the server log.

To publish new data later, repeat the two deploy commands.

## 2. Website on Cloudflare Pages

In the Cloudflare dashboard: **Workers & Pages, Create, Pages, Connect to Git**, pick the repository, then:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Framework preset | None |
| Root directory | `web` |
| Build command | `npm ci && npm run build` |
| Build output directory | `dist` |

Environment variables (Settings, Variables and secrets). None of them is a secret: every `VITE_*` value ends up in the public page.

| Variable | Value | Why |
|---|---|---|
| `NODE_VERSION` | `24` | the Node version the build expects |
| `REQUIRE_REAL_DATA` | `1` | the build fails if the data files still say `mock: true` |
| `VITE_API_URL` | `https://<app-name>.azurewebsites.net` | read the data through the API. Leave it out to use only the files shipped with the site |
| `VITE_REPO_URL` | the public address of the GitHub repository | shows the code, method and AI-use links in the About window |

When `VITE_API_URL` is set, the build adds that address to the site's content security policy automatically (see `web/public/_headers`). Any other value is rejected.

Save and deploy. The site is live at `https://<project>.pages.dev`.

## 3. Connect the two
1. Put the site's address into the API's `CORS_ORIGINS` setting (the command above), then restart the web app: `az webapp restart --name <app-name> --resource-group cut-off-rg`.
2. Open the site in a private window, on a phone using mobile data. The map, the swipe, the tabs and the radar images should all load. In the browser's network view the data files should come from `azurewebsites.net`.
3. Stop the API (`az webapp stop ...`) and reload: the site should still work from its own files. Start it again afterwards.

## 4. Before submitting
- Replace the two `{url}` placeholders at the top of `README.md` with the live site and the video.
- Refill the results block with real numbers: `python -m cutoff report --readme README.md` (run from `pipeline/`).
- Add the sources actually used to `docs/citations.md` and finish `docs/si-log.md`.
- Keep every link live and unchanged through judging: do not force-push or delete anything after submitting.

## Costs and cleanup
Check the prices for your region before choosing a tier. To remove everything on Azure: `az group delete --name cut-off-rg`.
