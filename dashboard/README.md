# TechJam Visualization Dashboard

A separate, static React reporting layer for the conversational-shopping project. It does not import or alter the agent, evaluator, configurations, benchmark logic, or model artifacts.

## Run locally

From this directory:

```powershell
npm.cmd install
npm.cmd run data
npm.cmd run dev
```

Open the Vite URL (normally `http://localhost:5173`). For the production check use `npm.cmd run build`.

## Data normalization

`scripts/build-dashboard-data.mjs` reads `C:/Users/ian/Documents/Projects/techjam-conversational-search-private/experiments/summary.csv`, `notes/**/*.md`, and `diagnostics/**/*.json` when that archive is available. It also reads this repository's `experiments/**/*.md`, and writes the portable static snapshot `public/dashboard-data.json`.

Set `TECHJAM_EXPERIMENTS` to point to a different archive. If it is unavailable, the script succeeds with local notes and manually curated historical milestone records clearly marked `source: "curated historical milestone"`.

The application loads only this static JSON in the browser; there is no backend. Rerun `npm.cmd run data` after adding experiment artifacts.
