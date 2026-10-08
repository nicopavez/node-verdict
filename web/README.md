# Node Verdict web demo

A static Next.js page that renders `src/data/node-verdict-data.json`. The page decides nothing. Every verdict, action, policy result and robustness band in that file comes from the tested Python engine in `../src/node_verdict`.

## Regenerate the data

From the repo root, after any change to the engine, policy, simulator or data:

```bash
python scripts/export_json.py
```

`tests/test_export.py` fails if the committed JSON drifts from a fresh export, and the Pages deploy runs that test first.

## Run it

```bash
cd web
npm ci
npm run dev        # http://localhost:3000
npm run build      # static site in web/out
```

## Deploy

`.github/workflows/pages.yml` builds the static export with `PAGES_BASE_PATH=/node-verdict` and publishes it to GitHub Pages on every push to `main`. No server, no API key, no cost. The `out/` folder also works on any static host.

## Design notes

- Verdict colors use the first four slots of a colorblind-validated categorical palette. Every cell also carries a text label, so color never carries meaning alone.
- Slowness uses a single-hue sequential ramp, lightest for normal.
- Light and dark modes are each chosen, not inverted.
- System fonts only, so the build needs no network.
