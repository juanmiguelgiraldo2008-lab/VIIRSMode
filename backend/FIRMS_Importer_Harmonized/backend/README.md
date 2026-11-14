# FIRMS importer — daily hotspot grouping

Python 3.10+; standard library only. This package contains an importer, not the full VIIRSMode application.

## Install and run

Merge the package's backend/ and public/ folders into your repository root. Preserve unrelated files; merge existing .gitignore rules. Never commit raw CSVs or .env files.

Keep ALL years' original CSV files in backend/data/ (subfolders such as MODIS/ and VIIRS/ are supported). Then run from the repository root:

```sh
python backend/import_firms.py
```

On Windows, `py` can replace `python`. Each run rebuilds the outputs; it does not append. Do not keep overlapping copies of exports: repeated rows contribute to detection_count, even though nearby identical points collapse visually.

## What is compared?

1. Normalize and validate latitude, longitude, acquisition date, instrument, satellite and FRP from every input CSV.
2. Sort by UTC date and decreasing FRP, with stable coordinate and source tie-breakers.
3. For each detection, find existing groups from the SAME UTC calendar day whose fixed representative is within 1 km on the Earth.
4. Accept a group only if its full FRP range, including the new point, satisfies `maximum <= 2 * minimum` OR `maximum - minimum <= 2 MW`.
5. If several groups qualify, choose the nearest representative, with a deterministic tie-breaker.
6. Otherwise create a new group. Its representative is the strongest detection, with that detection's original coordinates, sensor, satellite and FRP. FRP is NOT summed or averaged.

All members are within the specified radius of their fixed representative. Members on opposite sides may be up to twice that distance apart. Nearby chains cannot extend a group's radius. A 3D spatial index handles longitude wraparound and the poles; full-file order does not change results. All detections count, including same-sensor observations and identical repeated records.

These are adjustable display heuristics, NOT scientifically calibrated event matching, unique wildfire counts, fire severity levels, or a correction for MODIS/VIIRS sensitivity differences. FRP is radiative power in MW, not a danger rating. Sensor resolution, observation time and fire evolution can cause different FRP values for the same fire; conversely, distinct fires nearby can be grouped. The importer uses calendar date, not acquisition time; observations on either side of UTC midnight remain separate. Confidence and type filters are not applied.

NASA reference: https://forum.earthdata.nasa.gov/viewtopic.php?t=5189
MODIS/VIIRS FRP comparison: https://repository.library.noaa.gov/view/noaa/49896/noaa_49896_DS1.pdf

## Adjust the grouping

```sh
python backend/import_firms.py --radius-km 0.5 --frp-ratio 1.5 --frp-absolute 1
```

The default radius is 1 km, ratio is 2, and absolute tolerance is 2 MW. These are application starting choices, not NASA standards. Smaller tolerances generally produce more points. Radius must be greater than zero and at most 20,000 km; ratio must be at least 1; absolute tolerance must be nonnegative. Finite values only.

To recover the original individual-detection output:

```sh
python backend/import_firms.py --no-merge
```

Custom input directory:

```sh
python backend/import_firms.py --input /path/to/NASA_Data
```

## Outputs and GitHub placement

| Path | Purpose |
|---|---|
| backend/import_firms.py | Import and merge code |
| backend/test_import_firms.py, backend/test_merge.py | Tests |
| backend/.gitignore | Excludes local raw data and environment files |
| backend/README.md | This guide |
| public/viirsmode/hotspots.csv | Six-column app data: lat,lon,date,sensor,satellite,frp |
| backend/hotspots.json | Compact JSON array with the same six fields and group metadata |
| backend/import_report.json | Input file counts, raw counts per sensor/satellite/year, totals before/after by year, parameters |

JSON metadata: `detection_count`, `frp_min`, `frp_max`, `sensors`, `satellites`. The singular sensor and satellite identify ONLY the representative measurement. Arrays identify all contributors. A mixed group is not exclusively assigned to any one sensor. In --no-merge mode JSON has only the original six fields.

The CSV has exactly the original header. Its rows now represent groups, so the calendar should label counts as "daily hotspot groups". Sensor filtering on the CSV selects representative sensors, not every contributing sensor. The backend JSON is not automatically a publicly served URL. No src/ files are included or changed; globe runtime compatibility still needs checking in the full application repository.

Uploading the importer to GitHub does not automatically run it. Run it locally and commit the generated outputs. GitHub Actions would additionally need an accessible raw-data source; ignored files on your computer are not available to Actions.

## Included sample result

The three available 2018 Portugal CSVs contain 8,809 detections (1,310 MODIS and 7,499 VIIRS). Default grouping produces 3,724 daily hotspot groups; 5,085 rows are folded into other representative points. JSON detection counts sum back to 8,809. Raw CSVs are not included in this package.

## Tests

```sh
python -m unittest discover -s backend -p "test_*.py"
```
