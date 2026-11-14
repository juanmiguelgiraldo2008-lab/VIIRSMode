import unittest
from import_firms import merge_hotspots


def point(lat=0, lon=0, frp=10, **extra):
    return dict(lat=lat, lon=lon, frp=frp, date='2018-01-01', sensor='MODIS', satellite='Terra', **extra)


class MergeTests(unittest.TestCase):
    def test_nearby_cross_sensor_and_provenance(self):
        b = point(lon=.004, frp=12)
        b.update(sensor='VIIRS', satellite='N')
        result = merge_hotspots([point(), b])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['frp'], 12)
        self.assertEqual(result[0]['detection_count'], 2)
        self.assertEqual(result[0]['sensors'], ['MODIS', 'VIIRS'])

    def test_date_distance_and_intensity_separate(self):
        next_day = point(); next_day['date'] = '2018-01-02'
        self.assertEqual(len(merge_hotspots([point(), point(lon=.02), point(frp=100), next_day])), 4)

    def test_no_unbounded_spatial_or_intensity_chain(self):
        self.assertEqual(len(merge_hotspots([point(lon=x, frp=f) for x,f in [(0,20),(.008,18),(.016,16)]])), 2)
        self.assertEqual(len(merge_hotspots([point(frp=f) for f in [10,20,40]])), 2)

    def test_global_coordinates(self):
        self.assertEqual(len(merge_hotspots([point(lon=179.999), point(lon=-179.999)])), 1)
        self.assertEqual(len(merge_hotspots([point(lat=89.999,lon=0), point(lat=89.999,lon=180)])), 1)

    def test_order_independence_and_counts(self):
        rows = [point(), point(), point(lon=.001,frp=11)]
        self.assertEqual(merge_hotspots(rows), merge_hotspots(rows[::-1]))
        self.assertEqual(sum(r['detection_count'] for r in merge_hotspots(rows)), 3)

    def test_low_frp_and_invalid_settings(self):
        self.assertEqual(len(merge_hotspots([point(frp=0), point(frp=1)])), 1)
        for options in [dict(radius_km=0), dict(radius_km=float('nan')), dict(frp_ratio=.5), dict(frp_absolute=-1)]:
            with self.assertRaises(ValueError): merge_hotspots([], **options)

if __name__ == '__main__': unittest.main()

class BuildTests(unittest.TestCase):
    def test_recursive_input_csv_json_and_report_agree(self):
        import csv
        import json
        import import_firms
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as directory:
            backend = Path(directory) / 'backend'
            data = backend / 'data' / 'VIIRS'
            data.mkdir(parents=True)
            (data / 'sample.csv').write_text(
                'latitude,longitude,acq_date,instrument,satellite,frp\n'
                '0,0,2018-01-01,VIIRS,N,10\n'
                '0,0.001,2018-01-01,VIIRS,N20,12\n'
                '0,0,2019-01-01,VIIRS,N,10\n')
            with patch.object(import_firms, 'BACKEND', backend):
                report = import_firms.build_hotspots(backend / 'data')
                rows = json.loads((backend / 'hotspots.json').read_text())
                with (backend.parent / 'public/viirsmode/hotspots.csv').open() as f:
                    reader = csv.DictReader(f)
                    csv_rows = list(reader)
                    self.assertEqual(reader.fieldnames, import_firms.FIELDS)
                self.assertEqual(len(rows), 2)
                self.assertEqual(len(csv_rows), len(rows))
                self.assertEqual(sum(r['detection_count'] for r in rows), 3)
                self.assertEqual(report['input_detections'], 3)
                self.assertEqual(report['counts_by_year'][0]['after'], 1)
                first = (backend / 'hotspots.json').read_bytes()
                import_firms.build_hotspots(backend / 'data')
                self.assertEqual(first, (backend / 'hotspots.json').read_bytes())
                import_firms.build_hotspots(backend / 'data', merge=False)
                self.assertEqual(len(json.loads((backend / 'hotspots.json').read_text())), 3)
