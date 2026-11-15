# Lunar Horizon
### An independent 3D lunar landing-site navigator

An English, self-hostable website for exploring the real Moon and comparing lunar south-pole sites and dates. Uses NASA LRO LOLA terrain and NASA/JPL Horizons. No ChatGPT account, API key, Node.js installation, CDN or pip package is required to run it.

## Run in PyCharm — quickest start
1. Extract the complete ZIP. Keep `app.py` beside the `frontend` folder.
2. Open the extracted `lunar-horizon-standalone` folder in PyCharm.
3. Select a **Python 3.10 or newer** interpreter. A virtual environment is optional; there are no runtime packages to install.
4. Open `app.py`, right-click, choose **Run 'app'**.
5. The browser opens at **http://127.0.0.1:8000**. If it does not, copy that address from the Run console.
6. Stop the server with PyCharm's Stop button or Ctrl+C.

From a terminal:
```bash
python app.py
```
macOS / Linux can use `python3 app.py`. On Windows you can also double-click `run_windows.bat` if Python is installed.

If port 8000 is occupied:
```bash
python app.py --port 8001
```

**Do not open `frontend/index.html` by double-clicking it.** JavaScript modules, workers and the NASA proxy need the local web server. `app.py` starts it for you.

## What is inside
- A real-coordinate, full 3D Moon. Radius = **1,737,400 meters + LOLA measured elevation**. No invented mountains or craters, no decorative external Moon model.
- NASA LOLA-derived topographic surface relief, not a generated image or optical photograph. The global geometry uses no vertical exaggeration.
- Local 16 × 16 km detail at a 50 m analysis grid and regional 320 × 320 km context at a 1 km analysis grid.
- Several exploratory south-pole coordinate presets and picking within the analysis coverage.
- UTC start/end date, sample interval and height above ground.
- Actual Sun/Earth azimuth and elevation queried from **JPL Horizons** for that lunar location.
- Accelerated **3D ray–triangle intersections** with lunar curvature retained. Green: no modeled terrain hit. Red: terrain hit; first-hit distance is reported.
- Scrubbable / playable timeline, sampled access percentages, longest joint clear run, elevation chart, and up to four saved site/date comparisons.
- CSV results, JSON source/query export, PNG screenshots and data provenance.
- All assets bundled. A saved, clearly labeled actual Horizons response works without internet for the default central site, 2 m observer, Nov 14–21 2026 UTC, hourly samples.

## Using it
1. The first view shows the global Moon and loads the verified example.
2. Drag the Moon to rotate; scroll/pinch to zoom. **Focus on selected site** turns toward the point.
3. Choose **Local detail** for the landing-area mesh, or **Regional context** for farther terrain.
4. Change the point, observer height or dates and click **Analyze mission window**. New sky data requires an internet connection to NASA/JPL.
5. Move the timeline; the Sun/Earth directions, obstruction status, angles and chart update together.
6. Click **Save for comparison +**, change the site/date range and analyze again.
7. Read **How it works** and **Data & sources** for the numerical scope and limitations.

### Global view versus analysis coverage
The globe covers the entire Moon for orientation. Terrain-aware analysis is available inside the bundled south-polar DEM extent, not everywhere on the globe. Coordinates outside that area are rejected clearly. The low-resolution global shape must not be used for landing-scale obstacle analysis.

## Put it on GitHub
### Website method
1. Sign in to GitHub and create a new repository, for example `lunar-horizon`.
2. Choose public if the competition requires public source. Create the repository without adding starter files if uploading this complete project.
3. Choose **Add file → Upload files** and upload the **contents of the extracted folder**, including `app.py`, `frontend`, `data`, `tests`, and `docs`.
4. Commit the files. Do not upload the ZIP as the only repository item.
5. Never upload `.venv`, `.idea`, `.cache` or passwords. The included `.gitignore` excludes these for Git users.

### Git terminal method
Run inside the extracted project folder:
```bash
git init
git add .
git commit -m "Add independent lunar mission explorer"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```
Replace `YOUR_GITHUB_REPOSITORY_URL` with the HTTPS URL GitHub gives your new repository. Do not put passwords or tokens into source files.

### A GitHub repository is not the running backend
GitHub stores and shares the source. **GitHub Pages cannot run `app.py` or the NASA proxy.** To put the complete app on the public internet, use a Python-capable host. The included `render.yaml` and `Dockerfile` provide deployment configurations. Hosting accounts, availability and any charges are managed by the host; no hosting account is required for local use.

## Deploy independently (optional)
- On a Python-capable host, select this GitHub repository.
- Start command: `python app.py --host 0.0.0.0 --port $PORT --no-browser`.
- No build dependencies are required. Use Python 3.10+.
- Or build/run the included Docker image. Binding to `0.0.0.0` intentionally exposes the app to your network/host; local runs default to loopback only.
- The simple standard-library server is appropriate for a prototype. A production service for many users should add reverse-proxy TLS, request quotas and operational monitoring.

## Data & reproducibility
See `docs/DATA_SOURCES.md`, `data/manifest.json` and `docs/METHODOLOGY.md`.
- Raw global LOLA source and PDS label are included in `data/`.
- Prepared polar grids, global shape, relief image and the verified ephemeris are included in `frontend/assets/`.
- `tools/prepare_globe.py` recreates the global files from the raw LDEM source (optional NumPy/Pillow only for regeneration).
- `tools/prepare_polar.py` documents/downloads and recreates the polar grids (optional rasterio/NumPy only for regeneration).
- Frontend has no runtime requests to CDNs, Google Fonts or a ChatGPT service. External links only open when a user chooses to follow a source link.
- New queries go only through the Python backend to the fixed JPL Horizons endpoint; requests are sequential and responses are cached locally for 24 hours.

## Validation
```bash
python -m unittest discover -s tests -v
```
The tests validate lunar observer parameters, UTC handling, parsing of real Horizons column order, invalid-input rejection, JavaScript MIME types, anonymous local access and bundled data integrity. Optional scientific JavaScript tests are in `tests/science.test.mjs` and run with Node 22+.

## Scientific limits
- Center rays, not full disk visibility; partial solar illumination and eclipses are not modeled.
- Finite terrain coverage and downsampled meshes. Pixel spacing is not measurement accuracy.
- Sampled windows and percentages, not exact event times; brief events between samples can be missed.
- Direct Earth visibility is not a radio link budget or a ground-station access prediction.
- Globe/local lighting is illustrative; the intersection calculations carry the numerical result.
- An independent research/education prototype, not flight-certified mission planning or landing-safety software.

## Attribution & license
Application code: MIT, see `LICENSE`. Three.js: MIT, bundled locally with its original license. NASA LRO LOLA and NASA/JPL Horizons: retain source attribution and their applicable data policies. No ownership of NASA datasets or endorsement by NASA is claimed. ChatGPT assisted software and interface development; no synthetic scientific data or generated imagery are used.
