# Esports Trajectory Dashboard

Static HTML dashboard for displaying analysis results from the Esports Career Trajectory project.

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

Simply open `index.html` in a web browser, or use a local server:

```bash
# Python
python -m http.server 8000

# Node.js
npx serve .
```

Then visit `http://localhost:8000`

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

Create `app.yaml` in website folder:

```yaml
runtime: python39
handlers:
- url: /
  static_files: index.html
  upload: index.html
- url: /(.*)
  static_files: \1
  upload: .*
```

Then deploy:
```bash
gcloud app deploy
```

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
