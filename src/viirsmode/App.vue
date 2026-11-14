<script setup>
import { computed, onMounted, reactive, shallowRef, ref } from 'vue';
import GlobeView from './GlobeView.vue';
import SearchBar from './SearchBar.vue';
import InfoPanel from './InfoPanel.vue';
import {
  parseHotspotsCsv,
  filterHotspots,
  monthlyCounts,
  hotspotsToCsv,
  downloadText,
} from './hotspots.js';

const hotspots = shallowRef([]);
const hotspotError = ref('');
const area = reactive({ lat: 39.5, lon: -8, radiusKm: 150 });
const range = reactive({ from: 2000, to: 2025 });
const globe = ref(null);
const panelOpen = ref(false);
const selection = ref(null);

onMounted(async () => {
  try {
    const res = await fetch('/viirsmode/hotspots.csv');
    if (!res.ok) throw new Error(`Hotspot CSV request failed (${res.status})`);
    const parsed = parseHotspotsCsv(await res.text());
    if (!parsed.length)
      throw new Error('Hotspot CSV contains no valid detections');
    hotspots.value = parsed;
  } catch (error) {
    hotspotError.value = error instanceof Error ? error.message : String(error);
  }
});

const filtered = computed(() =>
  filterHotspots(hotspots.value, area, range.from, range.to),
);
const months = computed(() =>
  monthlyCounts(filtered.value, range.from, range.to),
);

function setArea(lat, lon) {
  area.lat = Number(lat.toFixed(3));
  area.lon = Number(lon.toFixed(3));
}

function onGlobeSelect({ lat, lon, hotspot }) {
  setArea(lat, lon);
  selection.value = { lat, lon, name: null, hotspot };
  panelOpen.value = true;
}

function onFound({ lat, lon, name }) {
  setArea(lat, lon);
  selection.value = { lat, lon, name, hotspot: null };
  panelOpen.value = true;
  globe.value?.flyToArea();
}

function download() {
  downloadText(
    `viirsmode_hotspots_${range.from}-${range.to}.csv`,
    hotspotsToCsv(filtered.value),
  );
}
</script>

<template>
  <div class="vm-root">
    <GlobeView
      ref="globe"
      :area="area"
      :hotspots="filtered"
      @select="onGlobeSelect"
    />

    <header class="vm-brand">
      <h1>ViirsMode</h1>
      <p>Burning activity calendar · harmonized MODIS + VIIRS</p>
      <p v-if="hotspotError" class="vm-warn"
        >Hotspot data unavailable: {{ hotspotError }}</p
      >
    </header>

    <SearchBar :area="area" :range="range" @found="onFound" />

    <InfoPanel
      v-if="panelOpen"
      :selection="selection"
      :months="months"
      :count="filtered.length"
      :range="range"
      @close="panelOpen = false"
      @download="download"
    />
  </div>
</template>
