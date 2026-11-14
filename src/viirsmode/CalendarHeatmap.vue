<script setup>
import { computed } from 'vue';

const props = defineProps({
  months: { type: Array, required: true },
});

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
// Viridis-like ramp (readable for most color-blind users)
const STOPS = ['#440154', '#3b528b', '#21908d', '#5dc863', '#fde725'];

const byKey = computed(
  () => new Map(props.months.map((m) => [`${m.year}-${m.month}`, m.count])),
);
const years = computed(() =>
  [...new Set(props.months.map((m) => m.year))].sort((a, b) => a - b),
);
const maxCount = computed(() =>
  Math.max(1, ...props.months.map((m) => m.count)),
);

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function colorFor(count) {
  if (count == null) return '#2a2a33';
  const t = Math.sqrt(count / maxCount.value);
  const pos = t * (STOPS.length - 1);
  const i = Math.min(Math.floor(pos), STOPS.length - 2);
  const f = pos - i;
  const a = hexToRgb(STOPS[i]);
  const b = hexToRgb(STOPS[i + 1]);
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

function countFor(year, month) {
  return byKey.value.get(`${year}-${month}`);
}
</script>

<template>
  <div class="cal">
    <div class="cal-row cal-head">
      <span class="cal-year"></span>
      <span v-for="name in MONTH_NAMES" :key="name" class="cal-month">{{ name }}</span>
    </div>
    <div v-for="year in years" :key="year" class="cal-row">
      <span class="cal-year">{{ year }}</span>
      <span
        v-for="month in 12"
        :key="month"
        class="cal-cell"
        :style="{ background: colorFor(countFor(year, month)) }"
        :title="`${MONTH_NAMES[month - 1]} ${year}: ${countFor(year, month) ?? 'no data'} hotspots`"
      ></span>
    </div>
    <div class="cal-legend">
      <span>Fewer hotspots</span>
      <span
        class="cal-legend-bar"
        :style="{ background: `linear-gradient(to right, ${STOPS.join(', ')})` }"
      ></span>
      <span>More ({{ maxCount }})</span>
    </div>
  </div>
</template>