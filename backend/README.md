# Backend / Data (ViirsMode)

Goal: turn the raw FIRMS CSVs (MODIS + VIIRS, Portugal) into ONE harmonized file.

## Output (what the app reads)
File: `public/viirsmode/hotspots.csv`
Columns (exact names): lat,lon,date,sensor,satellite,frp
- date: YYYY-MM-DD
- sensor: MODIS or VIIRS
- satellite: Terra, Aqua, N20, N (S-NPP), N21
- frp: fire radiative power (MW)
One row = one hotspot to be counted in the calendar.

## Input
Raw CSVs from FIRMS Archive Download (NOT in the repo; ask for the NASA_Data folder).
Put them in `backend/data/` (ignored by Git).
Column differences: MODIS brightness/bright_t31 vs VIIRS bright_ti4/bright_ti5;
confidence is a number (MODIS) vs a letter l/n/h (VIIRS). Read acq_time as text.

## Steps
1. First version (fast, do this first): read all files, unify columns, write hotspots.csv.
2. Harmonization (decide together): remove non-vegetation-fire rows (check `type` in the FIRMS FAQ),
   unify confidence, reduce the MODIS/VIIRS count difference (for example, count by grid cell and day,
   or calibrate with the years where both sensors overlap).
3. Check: counts per year before and after harmonization (MODIS vs VIIRS).

## Rules
- Work only inside `backend/` and write the output to `public/viirsmode/hotspots.csv`.
- Do not edit files in `src/`.
- `git pull` before starting, commit + push when something works.
- Never commit raw data or the `.env` file.