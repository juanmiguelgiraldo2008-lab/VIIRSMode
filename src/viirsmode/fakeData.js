// Fake data to build the UI. Replaced by the real calendar.json later.
export function makeFakeCalendar(startYear = 2000, endYear = 2025) {
  const seasonal = [0.2, 0.2, 0.3, 0.4, 0.5, 0.8, 1.6, 2.0, 1.4, 0.7, 0.3, 0.2];
  let seed = 7;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const months = [];
  for (let year = startYear; year <= endYear; year++) {
    const yearFactor = 0.5 + rand() * 1.5;
    for (let month = 1; month <= 12; month++) {
      const count = Math.round(
        250 * seasonal[month - 1] * yearFactor * (0.7 + rand() * 0.6),
      );
      months.push({ year, month, count });
    }
  }
  return { area: { name: 'Demo area (fake data)' }, months };
}