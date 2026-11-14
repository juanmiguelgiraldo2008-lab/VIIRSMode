# FIRMS importer

This package converts the three supplied Portugal 2018 FIRMS archive files into
one JSON array and one CSV with identical records. Python 3.9+ is required.
No pip packages are needed. No frontend source files are included or modified.

## Install and run

1. In your actual repository, run git pull before copying these files.
2. Copy this package's backend files into backend/ and the generated
   public/viirsmode/hotspots.csv into that same path in your repository.
   If backend/.gitignore already exists, merge its rules rather than replace it.
3. Create backend/data/ and place the raw FIRMS CSVs there.
   Subfolders by country or year are allowed. Raw CSVs are not included here.
4. From the repository root, run:

    python backend/import_firms.py

On systems where Python is called python3, use python3 instead.
To read a different folder:

    python backend/import_firms.py --input /path/to/NASA_Data

Each run reads ALL CSV files in the input folder recursively, validates them,
sorts detections by date, sensor, satellite and coordinates, and replaces:

- backend/hotspots.json: JSON array for the requested JSON integration.
- public/viirsmode/hotspots.csv: exact existing CSV contract.
- backend/import_report.json: per-file counts, raw type distributions, and
  counts by year, sensor and satellite before and after normalization.

Keep previous years' raw files in the input folder when adding new data.
The importer rebuilds, rather than appends, so rerunning with the same inputs
does not accumulate records. Overlapping or duplicated source exports WILL
count repeated rows: no detection deduplication is attempted. Do not place
generated CSVs inside the raw input folder.

This is a callable backend function, not an upload server or folder watcher:

    from backend.import_firms import build_hotspots
    report = build_hotspots("backend/data")

An existing upload handler can save CSVs there and then call this function.
The CLI workflow is sufficient for manually downloaded files.

## Exact output schema

| Raw CSV field | Output field | JSON type |
| --- | --- | --- |
| latitude | lat | number |
| longitude | lon | number |
| acq_date | date | string, YYYY-MM-DD |
| instrument | sensor | string: MODIS or VIIRS |
| satellite | satellite | string: Terra, Aqua, N, N20 or N21 |
| frp | frp | number, MW |

The JSON is a top-level array: it has the same shape as the list returned by
makeFakeHotspots(), with no wrapper object and no function declaration.
Dates remain strings. No year or country is hardcoded. Coordinates are not
rounded. Zero FRP is retained. Missing/invalid FRP, invalid coordinates, dates,
unknown satellites, inconsistent sensors, or malformed rows stop the import
with a filename and line number. Validation completes before outputs change.

CSV values, including acq_time, are read as text; leading zeros are preserved
during parsing. Time is intentionally omitted from the six-field output.
Brightness, confidence, type, scan, track, and other extra columns do not
affect this first version. Unknown header schemas require a mapping update.

## Frontend integration

The existing CSV loader can continue reading /viirsmode/hotspots.csv.
It should convert lat, lon and frp from CSV strings to numbers.

For JSON, your teammate can import the generated array if the bundler permits
imports from backend/, or serve it from a JSON endpoint:

    const response = await fetch(YOUR_HOTSPOTS_JSON_URL);
    if (!response.ok) throw new Error("Could not load hotspots");
    const hotspots = await response.json();

Here hotspots replaces the value previously returned by makeFakeHotspots().
Loading a file is asynchronous, so await it before drawing points.
backend/hotspots.json is NOT automatically a public URL. Publishing JSON at
/viirsmode/hotspots.json would require adding that public file to the team's
allowed outputs. This package only writes the CSV under public/.

Use the date string directly for calendar grouping, e.g. date.slice(0, 7)
for a month. Avoid local-time conversion that can shift a date.

## Supplied data validation

| Year | Sensor | Satellite | Before | After |
| --- | --- | --- | ---: | ---: |
| 2018 | MODIS | Terra | 613 | 613 |
| 2018 | MODIS | Aqua | 697 | 697 |
| 2018 | VIIRS | N | 3827 | 3827 |
| 2018 | VIIRS | N20 | 3672 | 3672 |
| Total | | | 8809 | 8809 |

The supplied N20 file starts April 2, 2018; the other files begin in January.
Do not treat their different coverage periods as identical.
No non-vegetation filtering, confidence normalization, spatial aggregation,
or MODIS/VIIRS calibration has been applied. Before/after totals are therefore
identical. One output record represents one source detection, not one unique
wildfire. The type distribution is recorded for later analysis; agree on
filtering rules using the FIRMS documentation before implementing phase two.
Do not deduplicate using these six fields alone: acquisition time was removed.

## Tests and practical limits

    python -m unittest discover -s backend

Tests cover numeric types, zero FRP, all five satellite codes, invalid values,
multiple years, and retention of repeated detections. The supplied files were
also converted and JSON/CSV contents reconciled against every source row.
The actual globe was not available for an integration test.

This implementation loads all records into memory for sorting. It is suitable
for the supplied country files; benchmark and consider year/month partitions
before loading a multi-year global archive into either Python or a browser.

## Git

No repository URL or checkout was provided, so no pull, commit or push was run.
After testing in your repository, stage only the intended code/generated files:

    git add backend/import_firms.py backend/test_import_firms.py backend/README.md backend/.gitignore backend/hotspots.json backend/import_report.json public/viirsmode/hotspots.csv
    git diff --cached --stat
    git commit -m "Add FIRMS importer and Portugal 2018 hotspots"
    git push

Never stage raw data or .env files. The included backend/.gitignore protects
backend/data/, backend/.env and backend/.env.*; preserve your repo's existing
root-level secret exclusions.
