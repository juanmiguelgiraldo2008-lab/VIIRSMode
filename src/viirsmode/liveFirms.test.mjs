import assert from "node:assert/strict";
import { test } from "node:test";
import { fetchLiveFires, liveResponseToHotspots } from "./liveFirms.js";

test("fetchLiveFires maps the Netlify FIRMS response for the globe", async () => {
  let request;
  const result = await fetchLiveFires(async (...args) => {
    request = args;
    return new Response(
      JSON.stringify({
        source: "VIIRS_NOAA20_NRT",
        fetched_at: "2026-03-06T12:00:00.000Z",
        total: 3,
        shown: 1,
        points: [[45.5, -73.6, 7.2]],
      }),
    );
  });

  assert.equal(request[0], "/.netlify/functions/firms-live");
  assert.deepEqual(request[1], { cache: "no-store" });
  assert.equal(result.fetchedAt, "2026-03-06T12:00:00.000Z");
  assert.equal(result.total, 3);
  assert.equal(result.shown, 1);
  assert.equal(result.fires[0].lat, 45.5);
  assert.equal(result.fires[0].lon, -73.6);
  assert.equal(result.fires[0].frp, 7.2);
  assert.equal(result.fires[0].sensor, "VIIRS");
  assert.equal(result.fires[0].satellite, "NOAA-20");
  assert.equal(result.fires[0].weight, 1);
});

test("fetchLiveFires rejects unavailable service responses", async () => {
  await assert.rejects(
    fetchLiveFires(
      async () =>
        new Response(JSON.stringify({ error: "upstream unavailable" }), {
          status: 500,
        }),
    ),
    /upstream unavailable/,
  );
});

test("liveResponseToHotspots rejects malformed point data", () => {
  assert.throws(
    () =>
      liveResponseToHotspots({
        source: "VIIRS_NOAA20_NRT",
        fetched_at: "2026-03-06T12:00:00.000Z",
        total: 1,
        shown: 1,
        points: [[91, 20, 2]],
      }),
    /invalid fire point/,
  );
});
