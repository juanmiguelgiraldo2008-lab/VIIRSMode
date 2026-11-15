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
PROJECT_ROOT = BACKEND.parents[2]


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
    """Retain valid type-0 or unclassified detections, including repeated rows."""
    hotspots, files = [], []
    counts = Counter()
    source_rows = 0
    excluded_rows = 0
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
                source_rows += 1
                if kind not in ("", "0"):
                    excluded_rows += 1
                    continue
                hotspots.append(hotspot)
                counts[(hotspot["date"][:4], hotspot["sensor"], hotspot["satellite"])] += 1
        files.append(dict(file=path.name, rows=count, type_counts=dict(sorted(types.items()))))
    hotspots.sort(key=lambda r: (r["date"], r["sensor"], r["satellite"], r["lat"], r["lon"]))
    report = dict(mode="schema normalization; type 0 or missing retained",
                  source_rows=source_rows, excluded_rows=excluded_rows,
                  type_filter=dict(included=["0", "missing"],
                                   excluded=["1", "2", "3"],
                                   reason="retain presumed vegetation fire detections"),
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
    """Return one MODIS-reference weight per epoch, plus yearly validation.

    Years with the same set of VIIRS satellites share one constant weight
    (MODIS-containing groups / all groups across the epoch). Each year's
    weighted total is then a real comparison against MODIS, not a circular match.
    """
    years = defaultdict(lambda: dict(total=0, modis=0, sats=set()))
    for g in groups:
        year = g["date"][:4]
        sensors = g.get("sensors", [g["sensor"]])
        years[year]["total"] += 1
        years[year]["modis"] += "MODIS" in sensors
        years[year]["sats"].update(g.get("satellites", [g["satellite"]]))

    def epoch_for(year):
        numeric_year = int(year)
        if numeric_year < 2012:
            return "2000-2011"
        if numeric_year < 2018:
            return "2012-2017"
        return "2018+"

    eras = {}
    for year, data in sorted(years.items()):
        era = eras.setdefault(
            epoch_for(year), dict(total=0, modis=0, sats=set(), years=[]))
        era["total"] += data["total"]
        era["modis"] += data["modis"]
        era["sats"].update(s for s in data["sats"] if s not in ("Terra", "Aqua"))
        era["years"].append(year)

    epoch_weights = {}
    for epoch, era in eras.items():
        if era["sats"] and not era["modis"]:
            raise ValueError(
                f"Cannot harmonize {epoch}: VIIRS groups have no MODIS reference groups")
        epoch_weights[epoch] = (
            round(era["modis"] / era["total"], 4) if era["sats"] else 1.0)

    weights, annual_report = {}, []
    for year, data in sorted(years.items()):
        epoch = epoch_for(year)
        weight = epoch_weights[epoch]
        weights[year] = weight
        weighted = data["total"] * weight
        diff = weighted - data["modis"]
        annual_report.append(dict(
            year=int(year), epoch=epoch,
            viirs_satellites=sorted(s for s in data["sats"] if s not in ("Terra", "Aqua")),
            groups=data["total"], modis_groups=data["modis"], weight=weight,
            weighted_groups=round(weighted, 4),
            difference_from_modis=round(diff, 4),
            error_pct=round(100 * diff / data["modis"], 1) if data["modis"] else None))

    epoch_report = []
    for epoch, era in eras.items():
        weighted_total = sum(
            years[y]["total"] * epoch_weights[epoch] for y in era["years"])
        epoch_report.append(dict(
            epoch=epoch, viirs_satellites=sorted(era["sats"]),
            years=sorted(era["years"]), groups=era["total"],
            modis_groups=era["modis"], weight=epoch_weights[epoch],
            weight_scope="one constant weight per epoch",
            weighted_groups=round(weighted_total, 4),
            difference_from_modis=round(weighted_total - era["modis"], 4)))
    return weights, epoch_report, annual_report

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

    weights, harmonization, yearly_harmonization = harmonization_weights(hotspots)
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
                                  for y in sorted(before)],
                  harmonization_weight_method=(
                      "per epoch: MODIS-containing groups / all groups, pooled over "
                      "the epoch; pre-VIIRS years use 1.0"),
                  source_rows=report["source_rows"],
                  excluded_rows=report["excluded_rows"],
                  type_filter=report["type_filter"])

    report["harmonization"] = harmonization
    report["yearly_harmonization"] = yearly_harmonization
    csv_paths = [PROJECT_ROOT / "public" / "viirsmode" / "hotspots.csv"]
    for csv_path in csv_paths:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = BACKEND / "hotspots.json"
    json_path.write_text(json.dumps(hotspots, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    for csv_path in csv_paths:
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
    print(f"Wrote {result['total']:,} hotspots to backend/hotspots.json and both public CSV copies")
