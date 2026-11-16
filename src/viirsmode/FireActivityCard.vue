<script setup>
import { computed } from "vue";
import { activityVsMedian } from "./hotspots.js";

const props = defineProps({
  months: { type: Array, required: true },
  referenceYear: { type: Number, required: true },
  area: { type: Object, required: true },
  range: { type: Object, required: true },
});
const emit = defineEmits(["select-year"]);

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const STOPS = ["#440154", "#3b528b", "#21908d", "#5dc863", "#fde725"];

const result = computed(() =>
  activityVsMedian(props.months, props.referenceYear),
);
const maxTotal = computed(() =>
  Math.max(1, ...result.value.totals.map(({ total }) => total)),
);
const monthPeriod = computed(() =>
  result.value.upToMonth === 1
    ? MONTH_NAMES[0]
    : `January–${MONTH_NAMES[result.value.upToMonth - 1]}`,
);
const chartTitle = computed(
  () =>
    `Annual harmonized fire activity through ${MONTH_NAMES[result.value.upToMonth - 1]} ${props.referenceYear}`,
);
const chartSummary = computed(
  () =>
    `Annual totals through ${MONTH_NAMES[result.value.upToMonth - 1]}. The selected year is highlighted; 2012 marks VIIRS S-NPP and 2018 marks NOAA-20.`,
);
const chartEntries = computed(() => {
  const entries = [];
  for (const entry of result.value.totals) {
    const marker = [
      [2012, "VIIRS S-NPP"],
      [2018, "NOAA-20"],
    ].find(([year]) => year === entry.year);
    if (marker) {
      entries.push({ year: entry.year, label: marker[1], kind: "marker" });
    }
    entries.push({ ...entry, kind: "year" });
  }
  return entries;
});
const ratioLabel = computed(() =>
  result.value.ratio === null
    ? "no baseline"
    : `${result.value.ratio.toFixed(1)}×`,
);

function colorFor(total) {
  const position = Math.sqrt(total / maxTotal.value) * (STOPS.length - 1) || 0;
  const index = Math.min(Math.floor(position), STOPS.length - 2);
  const fraction = position - index;
  const from = Number.parseInt(STOPS[index].slice(1), 16);
  const to = Number.parseInt(STOPS[index + 1].slice(1), 16);
  const channels = [16, 8, 0].map((shift) => {
    const start = (from >> shift) & 255;
    const end = (to >> shift) & 255;
    return Math.round(start + (end - start) * fraction);
  });
  return `rgb(${channels.join(", ")})`;
}

function selectYear(year) {
  emit("select-year", year);
}
</script>

<template>
  <section class="fire-activity-card">
    <header class="fire-activity-header">
      <div>
        <h3>Fire activity</h3>
        <p>
          {{ area.lat.toFixed(3) }}, {{ area.lon.toFixed(3) }} ·
          {{ area.radiusKm }} km · {{ range.from }}–{{ range.to }}
        </p>
      </div>
      <span class="fire-activity-period"
        >Through {{ MONTH_NAMES[result.upToMonth - 1] }}</span
      >
    </header>

    <div class="fire-activity-ratio">
      <strong>{{ ratioLabel }}</strong>
      <span>
        the median of the same months in {{ result.yearsCompared }} other
        {{ result.yearsCompared === 1 ? "year" : "years" }}
      </span>
    </div>
    <p class="fire-activity-rank">
      {{ result.position }} of {{ result.yearsCompared + 1 }} years, highest
      first
    </p>

    <div class="fire-activity-totals">
      <div class="fire-activity-total">
        <span>{{ monthPeriod }} {{ referenceYear }}</span>
        <strong
          >{{ result.total.toLocaleString("en-US") }}
          <small>harmonized groups</small></strong
        >
      </div>
      <div class="fire-activity-total">
        <span>Baseline median</span>
        <strong
          >{{ result.median.toLocaleString("en-US") }}
          <small>harmonized groups</small></strong
        >
      </div>
    </div>

    <div class="fire-activity-chart" role="group" :aria-label="chartTitle">
      <p class="fire-activity-chart-alt">
        {{ chartSummary }} Click a year to select it.
      </p>
      <template
        v-for="entry in chartEntries"
        :key="`${entry.kind}-${entry.year}`"
      >
        <div v-if="entry.kind === 'marker'" class="fire-activity-era-marker">
          <span class="fire-activity-era-line"></span>
          <span>{{ entry.year }} · {{ entry.label }}</span>
        </div>
        <button
          v-else
          type="button"
          class="fire-activity-year"
          :class="{ reference: entry.year === referenceYear }"
          :aria-label="`Select ${entry.year}: ${entry.total.toLocaleString('en-US')} harmonized groups`"
          :title="`Select ${entry.year}`"
          @click="selectYear(entry.year)"
        >
          <span class="fire-activity-year-label">{{ entry.year }}</span>
          <span class="fire-activity-track">
            <span
              class="fire-activity-bar"
              :style="{
                width: `${(entry.total / maxTotal) * 100}%`,
                background: colorFor(entry.total),
              }"
            ></span>
          </span>
          <span class="fire-activity-value">{{
            entry.total.toLocaleString("en-US")
          }}</span>
        </button>
      </template>
    </div>

    <p class="fire-activity-note">
      From 2012, VIIRS counts are scaled to MODIS-equivalent units with one
      constant weight per period (about 12.2% average difference from MODIS in
      the Portugal data). This is an approximation, not a calibration.
    </p>
  </section>
</template>
