<script setup>
import { computed, onMounted, reactive, shallowRef, ref } from 'vue';
import CalendarHeatmap from './CalendarHeatmap.vue';
import GlobeView from './GlobeView.vue';
import AreaControls from './AreaControls.vue';
import ComparisonCard from './ComparisonCard.vue';
import { makeFakeHotspots } from './fakeData.js';
import {
  parseHotspotsCsv, filterHotspots, monthlyCounts, hotspotsToCsv, downloadText,
} from './hotspots.js';

const hotspots = shallowRef(makeFakeHotspots());
const usingFake = ref(true);
const area = reactive({ lat: 39.5, lon: -8, radiusKm: 150 });
const range = reactive({ from: 2000, to: 2025 })
const globe = ref(null);

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

function onSelect({ lat, lon }) {
  area.lat = Number(lat.toFixed(3));
  area.lon = Number(lon.toFixed(3));
}

function download() {
  downloadText(
    `viirsmode_hotspots_${range.from}-${range.to}.csv`,
    hotspotsToCsv(filtered.value),
  );
}
</script>

<template>
  <main class="vm">
    <h1>ViirsMode</h1>
    <p class="vm-sub">Burning activity calendar: harmonized MODIS + VIIRS hotspots</p>
    <p v-if="usingFake" class="vm-warn">Showing fake demo data</p>

    <GlobeView ref="globe" :area="area" :hotspots="filtered" @select="onSelect" />
    <AreaControls
      :area="area"
      :range="range"
      :count="filtered.length"
      @download="download"
      @goto="globe?.flyToArea()"
    />
    <ComparisonCard :months="months" />
    <CalendarHeatmap :months="months" />
  </main>
</template>