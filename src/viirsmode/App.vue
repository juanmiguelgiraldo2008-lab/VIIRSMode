<script setup>
import { computed, onMounted, reactive, shallowRef, ref } from 'vue';
import GlobeView from './GlobeView.vue';
import SearchBar from './SearchBar.vue';
import InfoPanel from './InfoPanel.vue';
import {
  parseHotspotsCsv,
  filterHotspots,
  filterByYears,
  monthlyCounts,
  hotspotsToCsv,
  downloadText,
} from './hotspots.js';

const hotspots = shallowRef([]);
const hotspotError = ref('');
const area = reactive({ lat: 39.5, lon: -8, radiusKm: 150 });
const range = reactive({ from: 2025, to: 2025 });
const globe = ref(null);
const panelOpen = ref(false);
const selection = ref(null);

const yearBounds = computed(() => {
  let min = Infinity;
  let max = -Infinity;
  for (const h of hotspots.value) {
    const y = Number(h.date.slice(0, 4));
    if (y < min) min = y;
    if (y > max) max = y;
  }
  return Number.isFinite(min) ? { min, max } : { min: 2000, max: 2025 };
});

onMounted(async () => {
  try {
    const res = await fetch('/viirsmode/hotspots.csv');
    if (!res.ok) throw new Error(`Hotspot CSV request failed (${res.status})`);
    const parsed = parseHotspotsCsv(await res.text());
    if (!parsed.length) throw new Error('Hotspot CSV contains no valid detections');
    hotspots.value = parsed;
    range.from = yearBounds.value.max;
    range.to = yearBounds.value.max;
  } catch (error) {
    hotspotError.value = error instanceof Error ? error.message : String(error);
  }
});

// Map: every hotspot of the selected years, anywhere
const visible = computed(() => filterByYears(hotspots.value, range.from, range.to));
// Calendar: the selected area across the full history
const areaAllYears = computed(() =>
  filterHotspots(hotspots.value, area, yearBounds.value.min, yearBounds.value.max),
);
const months = computed(() =>
  monthlyCounts(areaAllYears.value, yearBounds.value.min, yearBounds.value.max),
);
// CSV: selected area and selected years
const exportRows = computed(() =>
  filterByYears(areaAllYears.value, range.from, range.to),
);

function setArea(lat, lon) {
  area.lat = Number(lat.toFixed(3));
  area.lon = Number(lon.toFixed(3));
}

function onGlobeSelect({ lat, lon, hotspot }) {
  setArea(lat, lon);
  if (hotspot) area.radiusKm = 50;
  selection.value = { lat, lon, name: null, hotspot };
  panelOpen.value = true;
}

function onFound({ lat, lon, name, radiusKm }) {
  setArea(lat, lon);
  if (radiusKm) area.radiusKm = radiusKm;
  selection.value = { lat, lon, name, hotspot: null };
  panelOpen.value = true;
  globe.value?.flyToArea();
}

function download() {
  downloadText(
    `viirsmode_hotspots_${range.from}-${range.to}.csv`,
    hotspotsToCsv(exportRows.value),
  );
}
</script>

<template>
  <div class="vm-root">
    <GlobeView ref="globe" :area="area" :hotspots="visible" @select="onGlobeSelect" />

    <header class="vm-brand">
      <h1>ViirsMode</h1>
      <p>Burning activity calendar · harmonized MODIS + VIIRS</p>
      <p v-if="hotspotError" class="vm-warn">Hotspot data unavailable: {{ hotspotError }}</p>
    </header>

    <SearchBar :area="area" :range="range" @found="onFound" />

    <InfoPanel
      v-if="panelOpen"
      :selection="selection"
      :months="months"
      :count="exportRows.length"
      :range="range"
      @close="panelOpen = false"
      @download="download"
    />
  </div>
</template>
