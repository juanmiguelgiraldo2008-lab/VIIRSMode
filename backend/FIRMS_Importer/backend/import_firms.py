"""Convert FIRMS archive CSV files to the globe's six-field format."""
import argparse
import hashlib
import csv
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

FIELDS = ["lat", "lon", "date", "sensor", "satellite", "frp"]
REQUIRED = {"latitude", "longitude", "acq_date", "instrument", "satellite", "frp"}
SATELLITES = {"TERRA": ("Terra", "MODIS"), "AQUA": ("Aqua", "MODIS"),
              "N": ("N", "VIIRS"), "S-NPP": ("N", "VIIRS"),
              "SNPP": ("N", "VIIRS"), "SUOMI NPP": ("N", "VIIRS"),
              "N20": ("N20", "VIIRS"), "NOAA-20": ("N20", "VIIRS"),
              "JPSS-1": ("N20", "VIIRS"),
              "N21": ("N21", "VIIRS"), "NOAA-21": ("N21", "VIIRS"),
              "JPSS-2": ("N21", "VIIRS")}
BACKEND = Path(__file__).resolve().parent

# "" = rows without a type (near-real-time data). Add "2" to keep static land sources.
KEEP_TYPES = {"", "0"}


def unique_files(paths):
    """Skip files whose content is identical to one already seen (duplicate copies)."""
    seen, unique = set(), []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            print(f"Skipping duplicate file: {path}")
            continue
        seen.add(digest)
        unique.append(path)
    return unique

def normalize(row):
    """Map one CSV record to one hotspot; fail on invalid required values."""
    lat, lon, frp = (float(row[key]) for key in ("latitude", "longitude", "frp"))
    if not all(math.isfinite(n) for n in (lat, lon, frp)):
        raise ValueError("coordinates and FRP must be finite numbers")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or frp < 0:
        raise ValueError("coordinates out of range or negative FRP")
    day = row["acq_date"].strip()
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("acq_date must be YYYY-MM-DD")
    satellite_key = row["satellite"].strip().upper()
    if satellite_key not in SATELLITES:
        raise ValueError(f"unknown satellite: {satellite_key}")
    satellite, expected_sensor = SATELLITES[satellite_key]
    sensor = row["instrument"].strip().upper()
    if sensor != expected_sensor:
        raise ValueError(f"instrument {sensor!r} does not match satellite {satellite}")
    return dict(lat=lat, lon=lon, date=day, sensor=sensor, satellite=satellite, frp=frp)


def read_files(paths):
    """Read all files; keep only detections whose type is in KEEP_TYPES."""
    hotspots, files = [], []
    before, after = Counter(), Counter()
    for path in sorted(paths):
        types = Counter()
        count = kept = 0
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)) or not REQUIRED.issubset(headers):
                raise ValueError(f"{path}: duplicate headers or missing columns: "
                                 f"{sorted(REQUIRED - set(headers))}")
            for row in reader:
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("row has a different number of fields than the header")
                    # DictReader keeps acq_time as text (including leading zeros).
                    hotspot = normalize(row)
                except (ValueError, TypeError, KeyError) as error:
                    raise ValueError(f"{path}, CSV line {reader.line_num}: {error}") from error
                key = (hotspot["date"][:4], hotspot["sensor"], hotspot["satellite"])
                kind = row.get("type", "").strip()
                types[kind or "missing"] += 1
                count += 1
                before[key] += 1
                if kind not in KEEP_TYPES:
                    continue
                hotspots.append(hotspot)
                after[key] += 1
                kept += 1
        files.append(dict(file=path.name, rows=count, kept=kept,
                          type_counts=dict(sorted(types.items()))))
    hotspots.sort(key=lambda r: (r["date"], r["sensor"], r["satellite"], r["lat"], r["lon"]))
    report = dict(
        mode=f"schema normalization + type filter (kept types: {sorted(KEEP_TYPES)}); "
             "no deduplication of detections",
        total=len(hotspots), files=files,
        counts=[dict(year=int(year), sensor=sensor, satellite=satellite,
                     before=before[(year, sensor, satellite)],
                     after=after[(year, sensor, satellite)])
                for (year, sensor, satellite) in sorted(before)])
    return hotspots, report


def build_hotspots(input_dir=BACKEND / "data"):
    """Rebuild both app outputs from all CSV files in input_dir and its subfolders."""
    input_dir = Path(input_dir)
    paths = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".csv")
    if not paths:
        raise ValueError(f"No CSV files found in {input_dir}")

    paths = unique_files(paths)
    # Finish validating all input before replacing any existing output.
    hotspots, report = read_files(paths)
    csv_path = BACKEND.parents[2] / "public" / "viirsmode" / "hotspots.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = BACKEND / "hotspots.json"
    json_path.write_text(json.dumps(hotspots, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(hotspots)
    (BACKEND / "import_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=BACKEND / "data")
    args = parser.parse_args()
    try:
        result = build_hotspots(args.input)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Import failed: {error}\n")
    print(f"Wrote {result['total']:,} hotspots to backend/hotspots.json and public/viirsmode/hotspots.csv")
