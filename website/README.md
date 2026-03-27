# Esports Trajectory Dashboard

Static HTML dashboard for displaying analysis results from the Esports Career Trajectory project.

## Production URL

**Hosted on Google App Engine:** [https://esport-trajectories.wl.r.appspot.com](https://esport-trajectories.wl.r.appspot.com)

Update this link in the root [`README.md`](../README.md) if the deployment URL changes.

## Structure

```
website/
├── index.html              # Homepage with project overview
├── css/
│   └── styles.css          # Main stylesheet (blue & gold theme)
├── js/
│   ├── data.js             # Sample data for development
│   ├── charts.js           # Chart utility functions
│   └── main.js             # Main JavaScript
├── pages/
│   ├── hypothesis1.html    # Career Length Analysis
│   ├── hypothesis2.html    # Tier Transition Analysis
│   └── hypothesis3.html    # Regional Differences Analysis
└── assets/                 # Images and other assets
```

## Running Locally

Use a local server (recommended so `fetch()` for JSON works). Production stays on App Engine, not localhost.

```bash
# Python
python -m http.server 8000

# Node.js
npx serve .
```

Then visit `http://localhost:8000` (or the port your tool prints).

## Deployment

This is a static site that can be deployed to:
- GitHub Pages
- Google App Engine (as shown in example)
- Netlify
- Vercel
- Any static file hosting

### GitHub Pages

1. Push to GitHub
2. Go to Settings > Pages
3. Select source branch (main) and folder (/website or /docs)

### Google App Engine

`app.yaml`, **`main.py`**, and **`requirements.txt`** are in this folder. Deploy from **`website/`** (recommended), or from the repo root:

```bash
gcloud app deploy website/app.yaml --project=YOUR_PROJECT_ID
```

If Cloud Build keeps failing with only “step 2 … non-zero status: 1”, see **`DEPLOY.md`** (how to pull the real log) and **Firebase Hosting** as a static alternative.

**Windows (project path has spaces — always quote it):**

```powershell
cd "C:\Users\pixls\cs163 - senior cap\Esports-Trajectory\website"
gcloud app deploy
```

If you see **“The system cannot find the path specified”**:

1. **Wrong folder** — `cd` failed. Use the full quoted path above (or your actual user folder).
2. **`gcloud` not found** — Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install), then **close and reopen** the terminal (PATH updates only in new sessions). Or run `gcloud` from its install folder, e.g.  
   `& "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" app deploy`
3. **First time** — Run `gcloud init`, pick your project, then enable App Engine if prompted.

After deploy, open the URL shown (e.g. `https://YOUR-PROJECT-ID.uc.r.appspot.com`).

**Cloud Build fails (e.g. step 2, `python_*_lightweight` builder):** App Engine still needs a small Python process when you use static handlers. This folder uses **`runtime: python310`**, an explicit **`entrypoint`** (`gunicorn … main:app`), **`main.py`** as a tiny stdlib WSGI app, and **`requirements.txt`** with only **`gunicorn`**. If deploy still fails, open the Cloud Build log link and search for the first `ERROR` line (often `pip` or permissions).

#### Auto-deploy on git push (GitHub Actions)

On pushes to `main` that change files under `website/`, [.github/workflows/deploy-appspot.yml](../.github/workflows/deploy-appspot.yml) deploys to App Engine.

**Repository admin:** add **`GCP_PROJECT_ID`** and **`GCP_SA_KEY`** under **Settings → Secrets and variables → Actions** (see workflow file comments for IAM). Without these, the workflow will not authenticate.

Optional: manually run **Actions → Deploy website to App Engine → Run workflow**.

## Theme

The dashboard uses a pastel blue and gold color scheme inspired by League of Legends:

- Primary Blue: `#5b8bd4`
- Primary Gold: `#d4a74a`
- Dark Blue: `#3d6cb3`
- Dark Gold: `#c9a227`

## Updating Data

To update with real analysis data:

1. Edit the data values in `js/data.js`
2. Update the metric values in each HTML file's `<script>` section
3. Update the table data in the HTML

## PDF Export

To generate PDF for the assignment:

1. Open each hypothesis page in browser
2. Print (Ctrl+P / Cmd+P) > Save as PDF
3. Combine PDFs using a PDF merger

Or use browser screenshot tools to capture visualizations.
