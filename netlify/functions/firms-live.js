// Server-side proxy: keeps the FIRMS MAP_KEY private and returns a small JSON.
const SOURCE = 'VIIRS_NOAA20_NRT';
const DAYS = 2; // today (UTC) + yesterday, then trimmed to the last 24 h
const MAX_POINTS = 15000;
const TTL_MS = 10 * 60 * 1000;
let cache = { bbox: '', at: 0, body: null };

const reply = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
      'cache-control': 'public, max-age=600',
    },
  });

export default async (req) => {
  const mapKey = process.env.FIRMS_MAP_KEY;
  if (!mapKey) return reply({ error: 'Live data is not configured' }, 500);

  const bbox = new URL(req.url).searchParams.get('bbox') || 'world';
  if (
    bbox !== 'world' &&
    !/^-?\d+(\.\d+)?(,-?\d+(\.\d+)?){3}$/.test(bbox)
  ) {
    return reply({ error: 'Invalid bbox' }, 400);
  }

  if (cache.body && cache.bbox === bbox && Date.now() - cache.at < TTL_MS) {
    return reply(cache.body);
  }

  let text;
  try {
    const res = await fetch(
      `https://firms.modaps.eosdis.nasa.gov/api/area/csv/${mapKey}/${SOURCE}/${bbox}/${DAYS}`,
    );
    if (!res.ok) return reply({ error: `FIRMS returned ${res.status}` }, 502);
    text = await res.text();
  } catch {
    return reply({ error: 'Could not reach FIRMS' }, 502);
  }

  const lines = text.split(/\r?\n/);
  const header = (lines[0] || '').split(',');
  const idx = Object.fromEntries(header.map((h, i) => [h.trim(), i]));
  if (idx.latitude === undefined || idx.longitude === undefined) {
    return reply({ error: 'Unexpected response from FIRMS' }, 502);
  }

  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i]) continue;
    const p = lines[i].split(',');
    if (idx.confidence !== undefined && p[idx.confidence] === 'l') continue;
    if (idx.acq_date !== undefined && idx.acq_time !== undefined) {
      // acq_time is HHMM and may have lost its leading zeros
      const t = String(p[idx.acq_time]).padStart(4, '0');
      const when = Date.parse(`${p[idx.acq_date]}T${t.slice(0, 2)}:${t.slice(2)}:00Z`);
      if (Number.isFinite(when) && when < cutoff) continue;
    }
    const lat = Number(p[idx.latitude]);
    const lon = Number(p[idx.longitude]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    rows.push([
      Math.round(lat * 1000) / 1000,
      Math.round(lon * 1000) / 1000,
      idx.frp === undefined ? 0 : Number(p[idx.frp]) || 0,
    ]);
  }

  const step = Math.max(1, Math.ceil(rows.length / MAX_POINTS));
  const points = rows.filter((_, i) => i % step === 0);
  const body = {
    source: SOURCE,
    fetched_at: new Date().toISOString(),
    total: rows.length,
    shown: points.length,
    points, // [lat, lon, frp]
  };
  // Do not keep empty answers in the cache
  if (rows.length > 0) cache = { bbox, at: Date.now(), body };
  return reply(body);
};