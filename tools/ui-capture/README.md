# ui-capture

Prerequisite: `desktop/node_modules` installed and the app built (`cd desktop && npm run build`), plus Python Playwright available to the `python` on PATH.
Re-run with `python tools/ui-capture/capture.py` (works from any cwd; paths resolve relative to the script).
It launches Electron with `--remote-debugging-port` plus an empty temp `--user-data-dir`, never signs in, and writes screenshots + `measurements.json` to `C:/work/baseline` (override with `COOL_BASELINE_DIR`); repo runtime files the app creates while running (`urls.txt`, `colors.json`) are deleted again at the end.
