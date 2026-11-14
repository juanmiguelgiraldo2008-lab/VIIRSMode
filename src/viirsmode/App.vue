<script setup>
import { onMounted, ref } from 'vue';
import CalendarHeatmap from './CalendarHeatmap.vue';
import GlobeView from './GlobeView.vue';
import { makeFakeCalendar } from './fakeData.js';

const data = ref(makeFakeCalendar());
const usingFake = ref(true);
const selected = ref(null);

// Later, the real file goes in public/viirsmode/calendar.json
onMounted(async () => {
  try {
    const res = await fetch('/viirsmode/calendar.json');
    const json = await res.json();
    if (Array.isArray(json.months) && json.months.length) {
      data.value = json;
      usingFake.value = false;
    }
  } catch {
    // no real file yet: keep the fake data
  }
});
</script>

<template>
  <main class="vm">
    <h1>ViirsMode</h1>
    <p class="vm-sub">
      Burning activity calendar: harmonized MODIS + VIIRS hotspots
    </p>
    <GlobeView @select="selected = $event" />
    <p v-if="selected" class="vm-sub">
      Selected point: {{ selected.lat.toFixed(3) }}, {{ selected.lon.toFixed(3) }}
    </p>
    <p v-else class="vm-sub">Click the globe to select a location</p>
    <h2>{{ data.area?.name }}</h2>
    <p v-if="usingFake" class="vm-warn">Showing fake demo data</p>
    <CalendarHeatmap :months="data.months" />
  </main>
</template>