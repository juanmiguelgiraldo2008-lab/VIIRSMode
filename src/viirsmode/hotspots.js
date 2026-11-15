// Parse hotspots.csv (columns: lat, lon, date, sensor, satellite, frp, ...)
export function parseHotspotsCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  if (!lines[0]) return [];
  const header = lines[0]
    .replace(/^\uFEFF/, '')
    .split(',')
    .map((h) => h.trim());
  const idx = Object.fromEntries(header.map((h, i) => [h, i]));
  if (
    idx.lat === undefined ||
    idx.lon === undefined ||
    idx.date === undefined
  ) {
    return [];
  }
  const out = [];
  for (let i = 1; i < lines.length; i++) {
    const p = lines[i].split(',').map((value) => value.trim());
    if (
      p.length !== header.length ||
      !/^\d{4}-\d{2}-\d{2}$/.test(p[idx.date] ?? '')
    ) {
      continue;
    }
    if (
      p[idx.lat] === '' ||
      p[idx.lon] === '' ||
      (idx.frp !== undefined && p[idx.frp] === '')
    ) {
      continue;
    }
    const lat = Number(p[idx.lat]);
    const lon = Number(p[idx.lon]);
    const frp = idx.frp === undefined ? undefined : Number(p[idx.frp]);
    const weightRaw = idx.weight === undefined ? NaN : Number(p[idx.weight]);
    const weight = Number.isFinite(weightRaw) && weightRaw > 0 ? weightRaw : 1;
    if (
      !Number.isFinite(lat) ||
      lat < -90 ||
      lat > 90 ||
      !Number.isFinite(lon) ||
      lon < -180 ||
      lon > 180 ||
      (frp !== undefined && (!Number.isFinite(frp) || frp < 0))
    ) {
      continue;
    }
    out.push({
      lat,
      lon,
      date: p[idx.date],
      sensor: idx.sensor === undefined ? undefined : p[idx.sensor],
      satellite: idx.satellite === undefined ? undefined : p[idx.satellite],
      frp,
      weight,
    });
  }
  return out;
}

// Square area around a point (radius in km)
export function areaBbox({ lat, lon, radiusKm }) {
  const dLat = radiusKm / 111;
  const dLon =
    radiusKm / (111 * Math.max(0.1, Math.cos((lat * Math.PI) / 180)));
  return {
    west: lon - dLon,
    east: lon + dLon,
    south: lat - dLat,
    north: lat + dLat,
  };
}

export function filterByYears(hotspots, fromYear, toYear) {
  return hotspots.filter((h) => {
    const y = Number(h.date.slice(0, 4));
    return y >= fromYear && y <= toYear;
  });
}

export function buildMonthlyIndex(hotspots) {
  const grouped = new Map();
  for (const hotspot of hotspots) {
    const match = /^(\d{4})-(0[1-9]|1[0-2])-\d{2}$/.exec(hotspot.date);
    if (!match) continue;
    const key = `${match[1]}-${match[2]}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(hotspot);
  }

  const keys = [...grouped.keys()].sort();
  if (!keys.length) return new Map();

  const firstMonth =
    Number(keys[0].slice(0, 4)) * 12 + Number(keys[0].slice(5)) - 1;
  const lastKey = keys[keys.length - 1];
  const lastMonth =
    Number(lastKey.slice(0, 4)) * 12 + Number(lastKey.slice(5)) - 1;
  const index = new Map();
  for (let monthIndex = firstMonth; monthIndex <= lastMonth; monthIndex++) {
    const year = Math.floor(monthIndex / 12);
    const month = String((monthIndex % 12) + 1).padStart(2, '0');
    const key = `${year}-${month}`;
    index.set(key, grouped.get(key) ?? []);
  }
  return index;
}

export function hotspotsInView(hotspots, bounds, maxPoints) {
  const { west, east, south, north } = bounds;
  const inView = hotspots.filter((hotspot) => {
    const longitudeVisible =
      west <= east
        ? hotspot.lon >= west && hotspot.lon <= east
        : hotspot.lon >= west || hotspot.lon <= east;
    return (
      Number.isFinite(hotspot.lat) &&
      Number.isFinite(hotspot.lon) &&
      hotspot.lat >= south &&
      hotspot.lat <= north &&
      longitudeVisible
    );
  });
  const step = Math.max(1, Math.ceil(inView.length / maxPoints));
  return inView.filter((_, index) => index % step === 0);
}

export function filterHotspots(hotspots, area, fromYear, toYear) {
  const b = areaBbox(area);
  return hotspots.filter((h) => {
    const y = Number(h.date.slice(0, 4));
    return (
      y >= fromYear &&
      y <= toYear &&
      h.lat >= b.south &&
      h.lat <= b.north &&
      h.lon >= b.west &&
      h.lon <= b.east
    );
  });
}

export function monthlyCounts(hotspots, fromYear, toYear) {
  const map = new Map();
  for (const h of hotspots) {
    const key = `${Number(h.date.slice(0, 4))}-${Number(h.date.slice(5, 7))}`;
    map.set(key, (map.get(key) || 0) + (h.weight ?? 1));
  }
  const months = [];
  for (let year = fromYear; year <= toYear; year++) {
    for (let month = 1; month <= 12; month++) {
      months.push({
        year,
        month,
        count: Math.round(map.get(`${year}-${month}`) || 0),
      });
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

export function yearTotals(months, upToMonth) {
  const endMonth = Math.min(12, Math.max(0, Number(upToMonth) || 0));
  const totals = new Map();
  for (const entry of months) {
    const year = Number(entry.year);
    const month = Number(entry.month);
    const count = Number(entry.count);
    if (!Number.isFinite(year)) continue;
    if (!totals.has(year)) totals.set(year, 0);
    if (month >= 1 && month <= endMonth) {
      totals.set(year, totals.get(year) + (Number.isFinite(count) ? count : 0));
    }
  }
  return [...totals]
    .map(([year, total]) => ({ year, total }))
    .sort((a, b) => a.year - b.year);
}

export function referenceMonth(months, year) {
  return (
    Math.max(
      0,
      ...months
        .filter(
          (entry) =>
            Number(entry.year) === Number(year) &&
            Number(entry.month) >= 1 &&
            Number(entry.month) <= 12 &&
            Number(entry.count) > 0,
        )
        .map((entry) => Number(entry.month)),
    ) || 12
  );
}

export function activityVsMedian(months, year) {
  const targetYear = Number(year);
  const upToMonth = referenceMonth(months, targetYear);
  const totals = yearTotals(months, upToMonth);
  if (!totals.some((entry) => entry.year === targetYear)) {
    totals.push({ year: targetYear, total: 0 });
    totals.sort((a, b) => a.year - b.year);
  }

  const current = totals.find((entry) => entry.year === targetYear);
  const otherTotals = totals
    .filter((entry) => entry.year !== targetYear)
    .map((entry) => entry.total);
  const baselineMedian = median(otherTotals);
  const ranked = [...totals].sort(
    (a, b) => b.total - a.total || a.year - b.year,
  );
  return {
    year: targetYear,
    upToMonth,
    total: current.total,
    median: baselineMedian,
    ratio: baselineMedian > 0 ? current.total / baselineMedian : null,
    position: ranked.findIndex((entry) => entry.year === targetYear) + 1,
    yearsCompared: otherTotals.length,
    totals,
  };
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
  const header = 'lat,lon,date,sensor,satellite,frp,weight';
  const rows = hotspots.map(
    (h) =>
      `${h.lat},${h.lon},${h.date},${h.sensor ?? ''},${h.satellite ?? ''},${h.frp ?? ''},${h.weight ?? ''}`,
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
