# Deploying the dashboard

## Fix: `DENIED: Permission 'artifactregistry.repositories.downloadArtifacts'`

If the log shows **Step #1 pre-buildpack** or **Step #2 build** failing on:

`GET https://us.gcr.io/v2/token?... DENIED: Permission 'artifactregistry.repositories.downloadArtifacts'`

and/or **failed to create image cache** for `.../app-engine-tmp/build-cache/...`, this is **IAM**, not Python.

### 1) Enable APIs

```cmd
gcloud services enable artifactregistry.googleapis.com containerregistry.googleapis.com cloudbuild.googleapis.com --project=esport-trajectories
```

### 2) Grant Cloud Build’s service account access to Artifact Registry

Get your **project number** (not the same as project id):

```cmd
gcloud projects describe esport-trajectories --format="value(projectNumber)"
```

Use that number in place of `PROJECT_NUMBER` below (example: `743593551906`):

```cmd
gcloud projects add-iam-policy-binding esport-trajectories --member="serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com" --role="roles/artifactregistry.writer"
```

`roles/artifactregistry.writer` includes pull + push so the buildpack can use the **App Engine build cache**.

The **buildpack cache** step often authenticates as the **Cloud Build Service Agent**, not `@cloudbuild.gserviceaccount.com`. If you still see `DENIED: ... downloadArtifacts` after granting the Cloud Build SA, add **the same role** for the service agent:

```cmd
gcloud projects add-iam-policy-binding esport-trajectories --member="serviceAccount:service-PROJECT_NUMBER@gcp-sa-cloudbuild.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"
```

(Replace `PROJECT_NUMBER` with your number, e.g. `743593551906`.)

Also confirm **Cloud Build → Settings → Service account** matches the principal you granted. If builds use a **custom** service account, that account needs `roles/artifactregistry.writer` too.

### Try deploy without reusing cache (sometimes unblocks)

```cmd
gcloud app deploy --project=esport-trajectories --no-cache
```

If it **still** fails with the same `app-engine-tmp/build-cache` DENIED line, the fix is IAM on the agent above or an **org policy** blocking Artifact Registry (needs admin).

### 3) Redeploy

```cmd
git clone https://github.com/Brandonlee-2002/Esports-Trajectory.git
cd Esports-Trajectory\website
gcloud app deploy --project=esport-trajectories
```

**Org / school accounts:** an admin may block Artifact Registry or IAM changes; you’ll need them to allow these roles.

---

## Other Cloud Build errors (step 2, `python_*_lightweight`)

If the error is **not** the DENIED line above, get more context:

```cmd
gcloud builds log BUILD_ID --region=us-west2 --project=esport-trajectories
```

Search for: `ERROR`, `pip`, `externally-managed`, `Permission`, `denied`.

---

## Option A — Firebase Hosting (static site, no Python build)

Works well when App Engine’s Python buildpack keeps failing.

1. Install [Firebase CLI](https://firebase.google.com/docs/cli) and run `firebase login`.
2. In Google Cloud Console, add Firebase to the same project (or create a Firebase project linked to GCP).
3. From **this folder** (`website/`):

   ```cmd
   firebase init hosting
   ```

   - Choose existing project `esport-trajectories` (or your Firebase project).
   - **Public directory:** `.` (current directory)
   - Single-page app: **No** (you have real paths like `/pages/eda.html`).
   - Overwrite `firebase.json`: **No** if asked (this repo already has one).

4. Deploy:

   ```cmd
   firebase deploy --only hosting
   ```

You’ll get a `https://YOUR_PROJECT.web.app` URL.

---

## Option B — App Engine (retry after config tweaks)

From `website/`:

```cmd
git clone https://github.com/Brandonlee-2002/Esports-Trajectory.git
cd Esports-Trajectory\website
gcloud app deploy --project=esport-trajectories --no-cache
```

`--no-cache` forces a clean build (sometimes fixes flaky builders).

---

## Option C — Google Cloud Storage static website

Upload the folder to a bucket configured for website hosting (no App Engine). See [Host a static website](https://cloud.google.com/storage/docs/hosting-static-website).
