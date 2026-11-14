"""Convert FIRMS archive CSV files to the globe's six-field format."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from itertools import product
from datetime import date
from pathlib import Path

FIELDS = ["lat", "lon", "date", "sensor", "satellite", "frp", "weight"]
REQUIRED = {"latitude", "longitude", "acq_date", "instrument", "satellite", "frp"}
SATELLITES = {"TERRA": ("Terra", "MODIS"), "AQUA": ("Aqua", "MODIS"),
              "N": ("N", "VIIRS"), "S-NPP": ("N", "VIIRS"),
              "SNPP": ("N", "VIIRS"), "SUOMI NPP": ("N", "VIIRS"),
              "N20": ("N20", "VIIRS"), "NOAA-20": ("N20", "VIIRS"),
              "JPSS-1": ("N20", "VIIRS"),
              "N21": ("N21", "VIIRS"), "NOAA-21": ("N21", "VIIRS"),
              "JPSS-2": ("N21", "VIIRS")}
BACKEND = Path(__file__).resolve().parent


def unique_files(paths):
    """Skip files whose name was already seen (duplicate copies in other folders)."""
    seen, unique = set(), []
    for path in paths:
        if path.name in seen:
            print(f"Skipping duplicate file: {path}")
            continue
        seen.add(path.name)
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
    """Read all files and years; retain every valid detection, including repeats."""
    hotspots, files = [], []
    counts = Counter()
    for path in sorted(paths):
        types = Counter()
        count = 0
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
                kind = row.get("type", "").strip()
                types[kind or "missing"] += 1
                count += 1
                if kind not in ("", "0"):
                    continue
                hotspots.append(hotspot)
                counts[(hotspot["date"][:4], hotspot["sensor"], hotspot["satellite"])] += 1
        files.append(dict(file=path.name, rows=count, type_counts=dict(sorted(types.items()))))
    hotspots.sort(key=lambda r: (r["date"], r["sensor"], r["satellite"], r["lat"], r["lon"]))
    report = dict(mode="schema normalization only; no filtering or deduplication",
                  total=len(hotspots), files=files,
                  counts=[dict(year=int(year), sensor=sensor, satellite=satellite,
                               before=n, after=n)
                          for (year, sensor, satellite), n in sorted(counts.items())])
    return hotspots, report


def merge_hotspots(rows, radius_km=1.0, frp_ratio=2.0, frp_absolute=2.0):
    """Group a UTC day around fixed strongest detections; never chain locations.

    FRP min/max must satisfy the ratio OR absolute tolerance. A 3D spatial
    hash finds nearby anchors even across the date line and near the poles.
    This is a display heuristic, not event identification or sensor calibration.
    """
    if (not all(math.isfinite(v) for v in (radius_km, frp_ratio, frp_absolute))
            or not 0 < radius_km <= 20000 or frp_ratio < 1 or frp_absolute < 0):
        raise ValueError("radius must be (0, 20000] km, FRP ratio >= 1, absolute tolerance >= 0")
    earth_radius = 6371.0088
    chord_limit = 2 * earth_radius * math.sin(radius_km / (2 * earth_radius))
    buckets = defaultdict(list)
    groups = []
    # Stable order makes the strongest point the anchor, independent of file order.
    ordered = sorted(rows, key=lambda r: (r['date'], -r['frp'], r['lat'],
                                         r['lon'], r['sensor'], r['satellite']))
    for row in ordered:
        lat, lon = math.radians(row['lat']), math.radians(row['lon'])
        xyz = (earth_radius * math.cos(lat) * math.cos(lon),
               earth_radius * math.cos(lat) * math.sin(lon), earth_radius * math.sin(lat))
        cell = tuple(math.floor(v / chord_limit) for v in xyz)
        candidates = []
        for offset in product((-1, 0, 1), repeat=3):
            key = (row['date'], *(c + d for c, d in zip(cell, offset)))
            for index in buckets.get(key, ()):
                group, anchor = groups[index]
                low, high = min(group['frp_min'], row['frp']), max(group['frp_max'], row['frp'])
                distance = math.dist(xyz, anchor)
                if distance <= chord_limit and (high <= low * frp_ratio or high - low <= frp_absolute):
                    candidates.append((distance, index))
        if candidates:
            group, _ = groups[min(candidates)[1]]
            group['detection_count'] += 1
            group['frp_min'] = min(group['frp_min'], row['frp'])
            group['frp_max'] = max(group['frp_max'], row['frp'])
            group['sensors'] = sorted(set(group['sensors']) | {row['sensor']})
            group['satellites'] = sorted(set(group['satellites']) | {row['satellite']})
        else:
            group = dict(row, detection_count=1, frp_min=row['frp'], frp_max=row['frp'],
                         sensors=[row['sensor']], satellites=[row['satellite']])
            buckets[(row['date'], *cell)].append(len(groups))
            groups.append((group, xyz))
    return [group for group, _ in groups]


def harmonization_weights(groups):
    """Weight per year so counts are comparable to the MODIS-only record.

    Years are grouped by era (same set of VIIRS satellites). In an era with VIIRS,
    weight = groups containing MODIS / all groups, so the era total matches what
    MODIS alone would have shown. Years before VIIRS keep weight 1.
    """
    years = defaultdict(lambda: dict(total=0, modis=0, sats=set()))
    for g in groups:
        year = g["date"][:4]
        sensors = g.get("sensors", [g["sensor"]])
        years[year]["total"] += 1
        years[year]["modis"] += "MODIS" in sensors
        years[year]["sats"].update(g.get("satellites", [g["satellite"]]))
    eras = defaultdict(list)
    for year, data in years.items():
        viirs = frozenset(s for s in data["sats"] if s not in ("Terra", "Aqua"))
        eras[viirs].append(year)
    weights, report = {}, []
    for viirs, era_years in sorted(eras.items(), key=lambda kv: min(kv[1])):
        total = sum(years[y]["total"] for y in era_years)
        modis = sum(years[y]["modis"] for y in era_years)
        weight = modis / total if viirs and total and modis else 1.0
        for year in era_years:
            weights[year] = round(weight, 4)
        report.append(dict(viirs_satellites=sorted(viirs), years=sorted(era_years),
                           groups=total, modis_groups=modis, weight=round(weight, 4)))
    return weights, report


def build_hotspots(input_dir=BACKEND / "data", *, merge=True, radius_km=1.0,
                   frp_ratio=2.0, frp_absolute=2.0):
    """Rebuild both app outputs from all CSV files in input_dir and its subfolders."""
    input_dir = Path(input_dir)
    paths = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".csv")
    if not paths:
        raise ValueError(f"No CSV files found in {input_dir}")
    # Finish validating all input before replacing any existing output.
    hotspots, report = read_files(paths)
    original = hotspots
    if merge:
        hotspots = merge_hotspots(original, radius_km, frp_ratio, frp_absolute)

    weights, harmonization = harmonization_weights(hotspots)
    for row in hotspots:
        row["weight"] = weights[row["date"][:4]]
    before = Counter(r['date'][:4] for r in original)
    after = Counter(r['date'][:4] for r in hotspots)
    # Original sensor counts remain raw counts: mixed groups cannot be assigned
    # exclusively to one sensor without misrepresenting their membership.
    report['raw_counts'] = [dict(year=c['year'], sensor=c['sensor'],
                                 satellite=c['satellite'], detections=c['before'])
                            for c in report.pop('counts')]
    report.update(mode='daily proximity and FRP grouping' if merge else 'unmerged',
                  input_detections=len(original), total=len(hotspots),
                  merged_detections=len(original)-len(hotspots),
                  parameters=dict(radius_km=radius_km, frp_ratio=frp_ratio,
                                  frp_absolute_mw=frp_absolute) if merge else None,
                  counts_by_year=[dict(year=int(y), before=before[y], after=after[y])
                                  for y in sorted(before)])

    report["harmonization"] = harmonization
    csv_path = BACKEND.parents[2] / "public" / "viirsmode" / "hotspots.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = BACKEND / "hotspots.json"
    json_path.write_text(json.dumps(hotspots, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(hotspots)
    (BACKEND / "import_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=BACKEND / "data")
    parser.add_argument('--radius-km', type=float, default=1.0)
    parser.add_argument('--frp-ratio', type=float, default=2.0)
    parser.add_argument('--frp-absolute', type=float, default=2.0, help='FRP tolerance in MW')
    parser.add_argument('--no-merge', action='store_true', help='Preserve individual detections')
    args = parser.parse_args()
    try:
        result = build_hotspots(args.input, merge=not args.no_merge, radius_km=args.radius_km,
                                frp_ratio=args.frp_ratio, frp_absolute=args.frp_absolute)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Import failed: {error}\n")
    print(f"Wrote {result['total']:,} hotspots to backend/hotspots.json and public/viirsmode/hotspots.csv")
