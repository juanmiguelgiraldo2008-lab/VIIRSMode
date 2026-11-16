import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildMonthlyIndex,
  activityVsMedian,
  hotspotsInView,
  monthlyCounts,
  parseHotspotsCsv,
  referenceMonth,
  yearTotals,
} from "./hotspots.js";

test("parseHotspotsCsv maps normalized FIRMS values to numeric coordinates and FRP", () => {
  const [hotspot] = parseHotspotsCsv(
    "\uFEFFlat,lon,date,sensor,satellite,frp\r\n39.4605,-8.557,2000-11-06,MODIS,Terra,4.9\r\n",
  );
  assert.deepEqual(hotspot, {
    lat: 39.4605,
    lon: -8.557,
    date: "2000-11-06",
    sensor: "MODIS",
    satellite: "Terra",
    frp: 4.9,
    weight: 1,
  });
});

test("parseHotspotsCsv skips malformed and out-of-range detections", () => {
  const rows = parseHotspotsCsv(
    [
      "lat,lon,date,sensor,satellite,frp,weight",
      "91,-8,2020-01-01,MODIS,Terra,1,1",
      "39,-8,2020-01-01,MODIS,Terra,not-a-number,1",
      "39,-8,not-a-date,MODIS,Terra,1,1",
      "39,-8,2020-01-01,MODIS,Terra,1,1",
    ].join("\n"),
  );
  assert.equal(rows.length, 1);
  assert.equal(rows[0].lat, 39);
  assert.equal(rows[0].lon, -8);
});

test("hotspotsInView filters to the camera bounds and caps dense views", () => {
  const hotspots = Array.from({ length: 10 }, (_, index) => ({
    lat: 40,
    lon: index - 5,
  }));
  const result = hotspotsInView(
    hotspots,
    { west: -3, east: 3, south: 39, north: 41 },
    2,
  );
  assert.deepEqual(result, [
    { lat: 40, lon: -3 },
    { lat: 40, lon: 1 },
  ]);
});

test("hotspotsInView supports camera bounds crossing the antimeridian", () => {
  const hotspots = [
    { lat: 0, lon: 179 },
    { lat: 0, lon: -179 },
    { lat: 0, lon: 0 },
  ];
  assert.deepEqual(
    hotspotsInView(
      hotspots,
      { west: 170, east: -170, south: -5, north: 5 },
      10,
    ),
    hotspots.slice(0, 2),
  );
});

test("monthlyCounts aggregates the per-record harmonization weights", () => {
  const months = monthlyCounts(
    [
      { date: "2025-01-02", weight: 0.4 },
      { date: "2025-01-08", weight: 0.4 },
      { date: "2025-02-01", weight: 1 },
    ],
    2025,
    2025,
  );
  assert.equal(months[0].count, 1);
  assert.equal(months[1].count, 1);
});

test("buildMonthlyIndex spans months in order and groups each month once", () => {
  const january = { date: "2024-01-20", lat: 1 };
  const march = { date: "2024-03-02", lat: 3 };
  const index = buildMonthlyIndex([march, january]);

  assert.deepEqual([...index.keys()], ["2024-01", "2024-02", "2024-03"]);
  assert.deepEqual(index.get("2024-01"), [january]);
  assert.deepEqual(index.get("2024-02"), []);
  assert.deepEqual(index.get("2024-03"), [march]);
  assert.deepEqual([...buildMonthlyIndex([])], []);
});

test("yearTotals sums harmonized monthly counts through the requested month", () => {
  const months = [
    { year: 2020, month: 1, count: 10 },
    { year: 2020, month: 2, count: 20 },
    { year: 2020, month: 3, count: 30 },
    { year: 2021, month: 1, count: 5 },
    { year: 2021, month: 2, count: 5 },
  ];
  assert.deepEqual(yearTotals(months, 2), [
    { year: 2020, total: 30 },
    { year: 2021, total: 10 },
  ]);
});

test("referenceMonth returns the last positive month or December without activity", () => {
  const months = [
    { year: 2020, month: 1, count: 0 },
    { year: 2020, month: 4, count: 12 },
    { year: 2020, month: 7, count: 0 },
  ];
  assert.equal(referenceMonth(months, 2020), 4);
  assert.equal(referenceMonth(months, 2021), 12);
});

test("activityVsMedian ranks the year against other years through its reference month", () => {
  const months = [
    { year: 2019, month: 1, count: 5 },
    { year: 2019, month: 2, count: 5 },
    { year: 2020, month: 1, count: 10 },
    { year: 2020, month: 2, count: 20 },
    { year: 2020, month: 3, count: 0 },
    { year: 2021, month: 1, count: 15 },
    { year: 2021, month: 2, count: 0 },
  ];
  assert.deepEqual(activityVsMedian(months, 2020), {
    year: 2020,
    upToMonth: 2,
    total: 30,
    median: 12.5,
    ratio: 2.4,
    position: 1,
    yearsCompared: 2,
    totals: [
      { year: 2019, total: 10 },
      { year: 2020, total: 30 },
      { year: 2021, total: 15 },
    ],
  });
  assert.equal(
    activityVsMedian([{ year: 2020, month: 1, count: 0 }], 2020).ratio,
    null,
  );
});
