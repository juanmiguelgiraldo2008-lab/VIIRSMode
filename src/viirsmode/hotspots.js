// Parse hotspots.csv (columns: lat, lon, date, sensor, satellite, frp, ...)
export function parseHotspotsCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(',').map((h) => h.trim());
  const idx = Object.fromEntries(header.map((h, i) => [h, i]));
  if (idx.lat === undefined || idx.lon === undefined || idx.date === undefined) {
    return [];
  }
  const out = [];
  for (let i = 1; i < lines.length; i++) {
    const p = lines[i].split(',');
    out.push({
      lat: parseFloat(p[idx.lat]),
      lon: parseFloat(p[idx.lon]),
      date: p[idx.date],
      sensor: p[idx.sensor],
      satellite: p[idx.satellite],
      frp: parseFloat(p[idx.frp]),
    });
  }
  return out;
}

// Square area around a point (radius in km)
export function areaBbox({ lat, lon, radiusKm }) {
  const dLat = radiusKm / 111;
  const dLon = radiusKm / (111 * Math.max(0.1, Math.cos((lat * Math.PI) / 180)));
  return { west: lon - dLon, east: lon + dLon, south: lat - dLat, north: lat + dLat };
}

export function filterHotspots(hotspots, area, fromYear, toYear) {
  const b = areaBbox(area);
  return hotspots.filter((h) => {
    const y = Number(h.date.slice(0, 4));
    return (
      y >= fromYear && y <= toYear &&
      h.lat >= b.south && h.lat <= b.north &&
      h.lon >= b.west && h.lon <= b.east
    );
  });
}

export function monthlyCounts(hotspots, fromYear, toYear) {
  const map = new Map();
  for (const h of hotspots) {
    const key = `${Number(h.date.slice(0, 4))}-${Number(h.date.slice(5, 7))}`;
    map.set(key, (map.get(key) || 0) + 1);
  }
  const months = [];
  for (let year = fromYear; year <= toYear; year++) {
    for (let month = 1; month <= 12; month++) {
      months.push({ year, month, count: map.get(`${year}-${month}`) || 0 });
    }
  }
  return months;
}

export function median(values) {
  if (!values.length) return 0;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// Reference month vs median of the same calendar month in the other years
export function compareMonth(months, year, month) {
  const current = months.find((m) => m.year === year && m.month === month);
  const others = months
    .filter((m) => m.month === month && m.year !== year)
    .map((m) => m.count);
  const med = median(others);
  const count = current ? current.count : 0;
  return { count, median: med, ratio: med > 0 ? count / med : null };
}

export function hotspotsToCsv(hotspots) {
  const header = 'lat,lon,date,sensor,satellite,frp';
  const rows = hotspots.map(
    (h) => `${h.lat},${h.lon},${h.date},${h.sensor ?? ''},${h.satellite ?? ''},${h.frp ?? ''}`,
  );
  return [header, ...rows].join('\n');
}

export function downloadText(filename, text) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}