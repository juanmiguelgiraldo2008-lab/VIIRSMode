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

These are adjustable display heuristics, NOT scientifically calibrated event matching, unique wildfire counts, fire severity levels, or a correction for MODIS/VIIRS sensitivity differences. FRP is radiative power in MW, not a danger rating. Sensor resolution, observation time and fire evolution can cause different FRP values for the same fire; conversely, distinct fires nearby can be grouped. The importer uses calendar date, not acquisition time; observations on either side of UTC midnight remain separate. Confidence is not filtered. Rows whose FIRMS `type` is `0` (presumed vegetation fire) or missing are retained; types `1`, `2`, and `3` are excluded from the vegetation-burning analysis. The report records both source rows and exclusions.

## Harmonization weights

The app compares annual activity with the MODIS record as its reference. After
daily grouping, each year with VIIRS receives:

```text
weight = groups containing MODIS / all groups that year
weighted annual groups = all groups that year * weight
```

This makes each year's weighted group total approximately equal to its
MODIS-containing group count; weights are rounded to four decimal places.
Pre-VIIRS years retain weight `1.0`. If VIIRS groups exist in a year with no
MODIS reference groups, the importer stops rather than inventing a weight.
The `harmonization` report section retains pooled epoch summaries for
2000–2011, 2012–2017, and 2018 onward; `yearly_harmonization` lists each
applied annual weight and its comparison with MODIS. Epoch weights are
diagnostic averages, not the weights assigned to every record in that epoch.

This is a transparent MODIS-reference normalization, not a NASA-provided
cross-sensor calibration. Annual equality to MODIS is a property of the
chosen formula, not independent evidence that the grouped observations are
scientifically equivalent. Review annual and monthly coverage before using
the results for operational decisions.

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
| backend/FIRMS_Importer_Harmonized/public/viirsmode/hotspots.csv | Package's generated CSV copy |
| public/viirsmode/hotspots.csv | App-served data: lat,lon,date,sensor,satellite,frp,weight |
| backend/hotspots.json | Compact JSON array with the seven fields plus group metadata |
| backend/import_report.json | Source/type counts, exclusions, grouping parameters, and epoch/year harmonization diagnostics |

JSON metadata: `detection_count`, `frp_min`, `frp_max`, `sensors`, `satellites`. The singular sensor and satellite identify ONLY the representative measurement. Arrays identify all contributors. A mixed group is not exclusively assigned to any one sensor. In --no-merge mode JSON has the seven normalized fields.

The CSV header is `lat,lon,date,sensor,satellite,frp,weight`. Its rows represent groups, so counts should distinguish daily groups from MODIS-equivalent weighted groups. Sensor filtering on the CSV selects representative sensors, not every contributing sensor. The backend JSON is not automatically a publicly served URL.

Uploading the importer to GitHub does not automatically run it. Run it locally and commit the generated outputs. GitHub Actions would additionally need an accessible raw-data source; ignored files on your computer are not available to Actions.

## Data availability

The output totals depend on the raw FIRMS files supplied under `backend/data/`,
which are not included in this package. The report records the number of source
rows, retained detections, type exclusions, and grouped records for each run.

## Tests

```sh
python -m unittest discover -s backend -p "test_*.py"
```
