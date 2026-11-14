<script setup>
import { onMounted, ref } from 'vue';
import CalendarHeatmap from './CalendarHeatmap.vue';
import { makeFakeCalendar } from './fakeData.js';

const data = ref(makeFakeCalendar());
const usingFake = ref(true);

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
    <h2>{{ data.area?.name }}</h2>
    <p v-if="usingFake" class="vm-warn">Showing fake demo data</p>
    <CalendarHeatmap :months="data.months" />
  </main>
</template>