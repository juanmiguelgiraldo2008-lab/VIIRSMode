<script setup>
import { ref } from 'vue';
import CalendarHeatmap from './CalendarHeatmap.vue';
import ComparisonCard from './ComparisonCard.vue';

defineProps({
  selection: Object,
  months: { type: Array, required: true },
  count: Number,
  harmonizedCount: Number,
  range: Object,
});
defineEmits(['close', 'download']);

const tab = ref('overview');
const TABS = [
  ['overview', 'Overview'],
  ['calendar', 'Calendar'],
  ['why', 'Why'],
  ['news', 'News'],
];
</script>

<template>
  <aside class="info">
    <div class="info-head">
      <h2>Fire information</h2>
      <button class="info-close" type="button" @click="$emit('close')"
        >×</button
      >
    </div>

    <div class="info-tabs">
      <button
        v-for="[key, label] in TABS"
        :key="key"
        type="button"
        :class="{ on: tab === key }"
        @click="tab = key"
        >{{ label }}</button
      >
    </div>

    <template v-if="tab === 'overview'">
      <div class="info-block">
        <h3>Location</h3>
        <p v-if="selection?.name">{{ selection.name }}</p>
        <p>{{ selection?.lat.toFixed(3) }}, {{ selection?.lon.toFixed(3) }}</p>
        <p
          >{{ count }} hotspot groups · {{ harmonizedCount }} MODIS-equivalent
          groups, {{ range.from }}–{{ range.to }}</p
        >
      </div>

      <div v-if="selection?.hotspot" class="info-block">
        <h3>Selected hotspot</h3>
        <p>Date: {{ selection.hotspot.date }}</p>
        <p
          >Sensor: {{ selection.hotspot.sensor }} ({{
            selection.hotspot.satellite
          }})</p
        >
        <p>Fire radiative power: {{ selection.hotspot.frp }} MW</p>
      </div>

      <ComparisonCard :months="months" />

      <div class="info-block">
        <h3>Cause and response</h3>
        <p>Coming soon: causes and response for the selected fire.</p>
      </div>

      <button class="info-btn" type="button" @click="$emit('download')">
        Download CSV ({{ count }} groups)
      </button>
    </template>

    <template v-else-if="tab === 'calendar'">
      <div class="info-block">
        <h3>Burning activity calendar</h3>
        <p>MODIS-equivalent groups per month in the selected area.</p>
        <CalendarHeatmap :months="months" />
      </div>
    </template>

    <template v-else-if="tab === 'why'">
      <div class="info-block">
        <h3>Why do fires happen?</h3>
        <p>
          Many ecosystems need periodic fire, but changes in its intensity,
          extent and frequency can harm climate, people and biodiversity. Fires
          on our planet are increasingly human-related: agriculture, land
          clearing, waste burning and industry add to natural wildfires.
        </p>
      </div>
      <div class="info-block">
        <h3>Why harmonize MODIS and VIIRS?</h3>
        <p>
          MODIS has watched fires since 2000 with roughly 1 km pixels. VIIRS
          sees roughly 375 m pixels, so it finds smaller fires and splits big
          ones into more points. Counting both as if they were equal makes
          activity look higher only because better sensors arrived.
        </p>
        <p>
          ViirsMode first groups detections from the same UTC day that fall
          within 1 km and have similar fire power, so one fire seen by several
          satellites counts once. Then, for each period with the same set of
          VIIRS satellites, it scales the counts so their total matches what
          MODIS alone recorded in that period. The result is one continuous
          series in MODIS-equivalent units from 2000 to today. It is an
          approximation, not a sensor calibration.
        </p>
      </div>
    </template>

    <template v-else>
      <div class="info-block">
        <h3>News</h3>
        <p>Coming soon: recent news and videos about fires in this area.</p>
      </div>
    </template>
  </aside>
</template>
