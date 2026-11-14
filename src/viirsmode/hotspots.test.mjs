import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseHotspotsCsv } from './hotspots.js';

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
