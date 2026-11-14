<script setup>
import { computed, onMounted, reactive, shallowRef, ref } from 'vue';
import GlobeView from './GlobeView.vue';
import SearchBar from './SearchBar.vue';
import InfoPanel from './InfoPanel.vue';
import { makeFakeHotspots } from './fakeData.js';
import {
  parseHotspotsCsv, filterHotspots, monthlyCounts, hotspotsToCsv, downloadText,
} from './hotspots.js';

const hotspots = shallowRef(makeFakeHotspots());
const usingFake = ref(true);
const area = reactive({ lat: 39.5, lon: -8, radiusKm: 150 });
const range = reactive({ from: 2000, to: 2025 });
const globe = ref(null);
const panelOpen = ref(false);
const selection = ref(null);

// Real file goes in public/viirsmode/hotspots.csv
onMounted(async () => {
  try {
    const res = await fetch('/viirsmode/hotspots.csv');
    const parsed = parseHotspotsCsv(await res.text());
    if (parsed.length) {
      hotspots.value = parsed;
      usingFake.value = false;
    }
  } catch {
    // no real file yet: keep the fake data
  }
});

const filtered = computed(() => filterHotspots(hotspots.value, area, range.from, range.to));
const months = computed(() => monthlyCounts(filtered.value, range.from, range.to));

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
    <GlobeView ref="globe" :area="area" :hotspots="filtered" @select="onGlobeSelect" />

    <header class="vm-brand">
      <h1>ViirsMode</h1>
      <p>Burning activity calendar · harmonized MODIS + VIIRS</p>
      <p v-if="usingFake" class="vm-warn">Showing fake demo data</p>
    </header>

    <SearchBar :area="area" :range="range" @found="onFound" />

    <InfoPanel
      v-if="panelOpen"
      :selection="selection"
      :months="months"
      :count="filtered.length"
      :range="range"
      :using-fake="usingFake"
      @close="panelOpen = false"
      @download="download"
    />
  </div>
</template>