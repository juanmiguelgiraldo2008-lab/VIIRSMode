# ViirsMode

**A consistent fire history from two satellite sensors.** ViirsMode harmonizes NASA FIRMS MODIS and VIIRS active-fire detections into one continuous series from 2000 onward and turns it into a burning-activity calendar for any selected area, with a historical-median comparison and CSV export.

Built for the NASA Space Apps Challenge 2026 (Montreal) · Challenge: *Harmonization of MODIS and VIIRS Hot Spots*

- Demo video: <YouTube link> https://youtu.be/2HG0qMA6Svs
- **Live demo:** https://viirsmode.netlify.app/
- Source code: https://github.com/juanmiguelgiraldo2008-lab/VIIRSMode
<!-- Add a screenshot or GIF here: ![ViirsMode](docs/screenshot.png) -->

<img width="1875" height="877" alt="image" src="https://github.com/user-attachments/assets/3929c71e-8ec5-473c-ac9e-230f4a54d90c" />


## The problem

MODIS has observed fires since 2000, but VIIRS sees smaller fires at finer resolution (375 m vs 1 km), so it records more detections for the same fire. Counting both as if they were equal makes fire activity look higher only because a better sensor arrived. MODIS is also nearing the end of its operational life, so any long fire history needs a way to continue with VIIRS.

## What ViirsMode does

- **3D globe** with the fire detections of the selected years (CesiumJS, Esri World Imagery).
- **Place search** by name or coordinates, and click any hotspot to see its date, sensor, satellite and fire radiative power (FRP).
- **Time-lapse** that plays the record month by month while the calendar fills in.
- **Burning-activity calendar** (year by month) built from the harmonized series, with a color-blind-friendly color ramp.
- **Fire activity panel:** compares an area's activity against the historical median of the same months, with a per-year chart that marks when S-NPP (2012) and NOAA-20 (2018) join.
- **Go Live:** Live shows the last 24 h of NOAA-20 VIIRS detections through a serverless proxy that keeps the FIRMS key private; low-confidence detections are filtered and up to 15,000 points are shown.
- **CSV download** of the detections for the selected area and years, including the harmonization weights.
- **Why** tab explaining fire regimes and why the sensors must be harmonized.

## How the harmonization works

The importer (`backend/FIRMS_Importer_Harmonized/backend/import_firms.py`) rebuilds `public/viirsmode/hotspots.csv` from the raw FIRMS archive CSVs:

1. **Clean and validate.** Every row is checked (coordinates, date, instrument/satellite match). Duplicate input files are skipped, and only detections classified by FIRMS as presumed vegetation fire (`type` 0, or unclassified) are kept. Static land sources, volcanoes and offshore detections are excluded.
2. **Group.** Detections from the same UTC day within 1 km of a group's strongest detection, and with similar FRP (max ≤ 2 × min, or a difference ≤ 2 MW), form one group. One fire seen by several satellites counts once. The radius and FRP tolerances are adjustable.
3. **Weight per period.** For each period with the same set of VIIRS satellites, one constant weight = (groups containing MODIS) / (all groups) scales the counts to MODIS-equivalent units. Years before VIIRS keep weight 1.0.

| Period | Sensors | Weight (Portugal data) |
|---|---|---|
| 2000–2011 | MODIS | 1.0 |
| 2012–2017 | MODIS + S-NPP | 0.4578 |
| 2018–2025 | MODIS + S-NPP + NOAA-20 | 0.3488 |

Every run writes `import_report.json` with the counts before and after, the parameters, and a yearly validation (`error_pct`).

### Validation and limits

- In our Portugal data (2000–2025), the harmonized yearly counts differ from MODIS by about **12.2% on average** across the years that include VIIRS. Years with little fire activity show larger relative errors.
- This is an **approximation, not a sensor calibration.** It assumes a stable ratio within each period, and the weights are validated on the same years used to compute them.
- Units are *daily hotspot groups in MODIS-equivalent units*, not individual fires.
- The demo data covers **Portugal only**, with S-NPP and NOAA-20 (no NOAA-21 and no 2026 data yet). S-NPP stopped delivering data on November 2, 2026, so recent data would need a new period.
- The importer itself is not specific to Portugal: it reads FIRMS archive CSVs of any country or region.

## Challenge requirements

| Requirement | Where in ViirsMode |
|---|---|
| Harmonize MODIS and VIIRS hotspots | `backend/FIRMS_Importer_Harmonized/`, method above |
| Calendar of burning activity from the early 2000s | Calendar and time-lapse (2000 onward) |
| Select a region and date range | Place/coordinate search, radius, year range |
| Compare the current month with the historical median | Fire activity panel |
| Accessible color ramp | Viridis-like ramp in the calendar |
| Downloadable CSV of the hotspots | CSV download button |

## Run it

Requirements: Node.js 24 or newer.

```sh
npm install
npm run dev
```

Open http://localhost:4173. The data is already included in `public/viirsmode/hotspots.csv`.

Tests:

```sh
npm test
python -m unittest discover -s backend/FIRMS_Importer_Harmonized/backend -p "test_*.py"
```

### Rebuild the data

Requires Python 3.10+ (standard library only). Download the raw yearly CSVs from [FIRMS Archive Download](https://firms.modaps.eosdis.nasa.gov/download) (MODIS C6.1 and VIIRS, same area), put them in a folder (raw data is not included in this repository), and run:

```sh
python backend/FIRMS_Importer_Harmonized/backend/import_firms.py --input <folder with the CSVs>
```

Options: `--radius-km`, `--frp-ratio`, `--frp-absolute`, `--no-merge`.

## Repository layout

| Path | Content |
|---|---|
| `src/viirsmode/` | Web app (Vue 3, CesiumJS) |
| `public/viirsmode/hotspots.csv` | Harmonized data used by the app |
| `backend/FIRMS_Importer_Harmonized/` | Importer, harmonization, tests |
| `LICENSE` | License of ViirsMode |
| `LICENSE-gods-eye-view` | Original license of the base project |


## Next steps

- **Out-of-sample validation:** fit the period weights on some years and measure the error on years held out, instead of validating on the same years used to compute them.
- **Fresh data:** add 2026 and later detections from the FIRMS area API, and a new period for NOAA-21. S-NPP stopped delivering data on November 2, 2026.
- **Robust parameters:** test how the grouping radius and FRP tolerance change the weights, and pick them with a sensitivity analysis instead of fixed defaults.
- **More regions:** run the importer on more countries and check whether the weights hold across fire regimes.
- **Live and historical together:** connect the Go Live layer to the calendar, so today's detections can be compared with the harmonized history.
- **Automatic updates:** a scheduled job that rebuilds the dataset instead of running the importer by hand.

## Credits

- **Data:** NASA FIRMS (Earthdata), MODIS Collection 6.1 and VIIRS 375 m active-fire detections. https://www.earthdata.nasa.gov/data/tools/firms
- **Base project:** built on top of the open-source [gods-eye-view](https://github.com/bilawalsidhu/gods-eye-view) by Bilawal Sidhu (MIT License, kept in `LICENSE-gods-eye-view`). We reused its project scaffolding and dependencies (Vue, Vite, CesiumJS). The ViirsMode web app, the harmonization importer and the data in this repository are new work done during the hackathon. Third-party datasets and 3D models bundled in the original repository are not included here.
- **Globe and imagery:** [CesiumJS](https://github.com/CesiumGS/cesium), Esri World Imagery.
- **Place search:** OpenStreetMap Nominatim, © OpenStreetMap contributors (https://www.openstreetmap.org/copyright).
- **Team:** Juan Miguel Giraldo P (web app) and Samuel Quiroz (data importer and harmonization).
- **AI assistance:** we used AI assistants (Claude and GitHub Copilot) to help write and debug code. The method, parameters and validation were run and reviewed by the team.

## License

ViirsMode is released under the MIT License (see `LICENSE`). Parts derived from gods-eye-view remain under its MIT License (see `LICENSE-gods-eye-view`).
