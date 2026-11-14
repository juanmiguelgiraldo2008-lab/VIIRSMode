import unittest
from import_firms import normalize, read_files
from pathlib import Path
from tempfile import TemporaryDirectory


class ImportTests(unittest.TestCase):
    def row(self, **changes):
        return dict(latitude="37.1", longitude="-8.2", acq_date="2024-02-29",
                    acq_time="0256", instrument="VIIRS", satellite="N",
                    frp="0", **changes)

    def test_numeric_coordinates_and_zero_frp(self):
        self.assertEqual(normalize(self.row()), dict(
            lat=37.1, lon=-8.2, date="2024-02-29",
            sensor="VIIRS", satellite="N", frp=0.0))

    def test_bad_values_rejected(self):
        for field, value in [("latitude", "91"), ("longitude", "nan"),
                             ("frp", ""), ("frp", "-1"),
                             ("acq_date", "2023-02-29"),
                             ("satellite", "unknown"), ("instrument", "MODIS")]:
            row = self.row()
            row[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                normalize(row)

    def test_all_satellites(self):
        for satellite, sensor in [("Terra", "MODIS"), ("Aqua", "MODIS"),
                                  ("N", "VIIRS"), ("N20", "VIIRS"), ("N21", "VIIRS")]:
            row = self.row()
            row.update(satellite=satellite, instrument=sensor)
            self.assertEqual(normalize(row)["satellite"], satellite)

    def test_multiple_years_and_repeated_detections_preserved(self):
        with TemporaryDirectory() as directory:
            paths = []
            for year in (2018, 2025):
                p = Path(directory) / f"{year}.csv"
                p.write_text("latitude,longitude,acq_date,instrument,satellite,frp\n"
                             + f"40,-8,{year}-01-01,MODIS,Terra,3\n" * 2)
                paths.append(p)
            rows, report = read_files(paths)
            self.assertEqual(len(rows), 4)
            self.assertEqual([r["date"] for r in rows],
                             ["2018-01-01"] * 2 + ["2025-01-01"] * 2)
            self.assertEqual(sum(r["after"] for r in report["counts"]), 4)


if __name__ == "__main__":
    unittest.main()
