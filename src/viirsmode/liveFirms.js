const LIVE_ENDPOINT = "/.netlify/functions/firms-live";

export function liveResponseToHotspots(payload) {
  if (
    !payload ||
    typeof payload !== "object" ||
    typeof payload.source !== "string" ||
    typeof payload.fetched_at !== "string" ||
    !Number.isFinite(Date.parse(payload.fetched_at)) ||
    !Number.isInteger(payload.total) ||
    payload.total < 0 ||
    !Number.isInteger(payload.shown) ||
    payload.shown < 0 ||
    payload.shown > payload.total ||
    !Array.isArray(payload.points)
  ) {
    throw new Error("NASA FIRMS returned an invalid fire snapshot");
  }

  const fires = payload.points.map((point) => {
    if (
      !Array.isArray(point) ||
      point.length < 3 ||
      !Number.isFinite(point[0]) ||
      point[0] < -90 ||
      point[0] > 90 ||
      !Number.isFinite(point[1]) ||
      point[1] < -180 ||
      point[1] > 180 ||
      !Number.isFinite(point[2])
    ) {
      throw new Error("NASA FIRMS returned an invalid fire point");
    }
    return {
      lat: point[0],
      lon: point[1],
      frp: point[2],
      sensor: "VIIRS",
      satellite: "NOAA-20",
      weight: 1,
    };
  });

  if (fires.length !== payload.shown) {
    throw new Error("NASA FIRMS returned an inconsistent fire snapshot");
  }

  return {
    source: payload.source,
    fetchedAt: payload.fetched_at,
    total: payload.total,
    shown: payload.shown,
    fires,
  };
}

export async function fetchLiveFires(
  fetchImpl = (...args) => globalThis.fetch(...args),
) {
  const response = await fetchImpl(LIVE_ENDPOINT, {
    cache: "no-store",
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      payload.error || `NASA FIRMS request failed (${response.status})`,
    );
  }
  return liveResponseToHotspots(payload);
}
