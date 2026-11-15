import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hotspotsInView, monthlyCounts, parseHotspotsCsv } from './hotspots.js';

test('parseHotspotsCsv maps normalized FIRMS values to numeric coordinates and FRP', () => {
  const [hotspot] = parseHotspotsCsv(
    '\uFEFFlat,lon,date,sensor,satellite,frp\r\n39.4605,-8.557,2000-11-06,MODIS,Terra,4.9\r\n',
  );
  assert.deepEqual(hotspot, {
    lat: 39.4605,
    lon: -8.557,
    date: '2000-11-06',
    sensor: 'MODIS',
    satellite: 'Terra',
    frp: 4.9,
    weight: 1,
  });
});

test('parseHotspotsCsv skips malformed and out-of-range detections', () => {
  const rows = parseHotspotsCsv(
    [
      'lat,lon,date,sensor,satellite,frp,weight',
      '91,-8,2020-01-01,MODIS,Terra,1,1',
      '39,-8,2020-01-01,MODIS,Terra,not-a-number,1',
      '39,-8,not-a-date,MODIS,Terra,1,1',
      '39,-8,2020-01-01,MODIS,Terra,1,1',
    ].join('\n'),
  );
  assert.equal(rows.length, 1);
  assert.equal(rows[0].lat, 39);
  assert.equal(rows[0].lon, -8);
});

test('hotspotsInView filters to the camera bounds and caps dense views', () => {
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

test('hotspotsInView supports camera bounds crossing the antimeridian', () => {
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

test('monthlyCounts aggregates the per-record harmonization weights', () => {
  const months = monthlyCounts(
    [
      { date: '2025-01-02', weight: 0.4 },
      { date: '2025-01-08', weight: 0.4 },
      { date: '2025-02-01', weight: 1 },
    ],
    2025,
    2025,
  );
  assert.equal(months[0].count, 1);
  assert.equal(months[1].count, 1);
});
