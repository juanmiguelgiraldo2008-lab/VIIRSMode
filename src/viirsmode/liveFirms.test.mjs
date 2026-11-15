import assert from 'node:assert/strict';
import { test } from 'node:test';
import { fetchLiveFires } from './liveFirms.js';

test('fetchLiveFires maps the server FIRMS response for the globe', async () => {
  let request;
  const result = await fetchLiveFires(async (...args) => {
    request = args;
    return new Response(
      JSON.stringify({
        count: 1,
        fires: [
          {
            lat: 45.5,
            lon: -73.6,
            acqDate: '2026-11-15',
            instrument: 'VIIRS',
            satellite: 'N20',
            frp: 7.2,
          },
        ],
      }),
    );
  });

  assert.equal(request[0], '/api/firms');
  assert.deepEqual(request[1], { cache: 'no-store' });
  assert.equal(result.fires[0].date, '2026-11-15');
  assert.equal(result.fires[0].sensor, 'VIIRS');
  assert.equal(result.fires[0].weight, 1);
});

test('fetchLiveFires distinguishes a missing MAP_KEY from other failures', async () => {
  const noKey = await fetchLiveFires(
    async () =>
      new Response(JSON.stringify({ error: 'no_key' }), { status: 503 }),
  );
  assert.deepEqual(noKey, { keyRequired: true });

  await assert.rejects(
    fetchLiveFires(
      async () =>
        new Response(JSON.stringify({ error: 'upstream unavailable' }), {
          status: 500,
        }),
    ),
    /upstream unavailable/,
  );
});
