// Fake hotspots around Portugal to build the UI. Replaced by the real hotspots.csv later.
export function makeFakeHotspots() {
  const seasonal = [0.2, 0.2, 0.3, 0.4, 0.5, 0.8, 1.6, 2.0, 1.4, 0.7, 0.3, 0.2];
  const clusters = [
    { lat: 41.0, lon: -8.0 },
    { lat: 39.7, lon: -7.9 },
    { lat: 37.3, lon: -8.1 },
    { lat: 40.3, lon: -7.4 },
    { lat: 38.5, lon: -8.7 },
  ];
  let seed = 11;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const pad = (n) => String(n).padStart(2, '0');
  const list = [];
  for (let year = 2000; year <= 2025; year++) {
    const yearFactor = 0.4 + rand() * 1.6;
    for (let month = 1; month <= 12; month++) {
      const n = Math.round(40 * seasonal[month - 1] * yearFactor * (0.6 + rand() * 0.8));
      for (let i = 0; i < n; i++) {
        const c = clusters[Math.floor(rand() * clusters.length)];
        const viirs = year >= 2012 && rand() < 0.7;
        list.push({
          lat: +(c.lat + (rand() - 0.5) * 1.2).toFixed(4),
          lon: +(c.lon + (rand() - 0.5) * 1.2).toFixed(4),
          date: `${year}-${pad(month)}-${pad(1 + Math.floor(rand() * 28))}`,
          sensor: viirs ? 'VIIRS' : 'MODIS',
          satellite: viirs ? 'N20' : 'Terra',
          frp: +(1 + rand() * 15).toFixed(1),
        });
      }
    }
  }
  return list;
}