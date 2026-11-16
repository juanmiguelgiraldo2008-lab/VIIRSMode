<script setup>
import { computed, ref, watch } from "vue";
import { compareMonth } from "./hotspots.js";

const props = defineProps({ months: { type: Array, required: true } });
const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const refYear = ref(null);
const refMonth = ref(null);

// Default: the latest month that has data
const last = computed(() => {
  const withData = props.months.filter((m) => m.count > 0);
  return withData.at(-1) ?? props.months.at(-1) ?? { year: null, month: null };
});
watch(
  last,
  (l) => {
    refYear.value = l.year;
    refMonth.value = l.month;
  },
  { immediate: true },
);

const years = computed(() => [...new Set(props.months.map((m) => m.year))]);
const result = computed(() =>
  compareMonth(props.months, refYear.value, refMonth.value),
);

const verdict = computed(() => {
  const r = result.value.ratio;
  if (r === null) return "No historical baseline";
  if (r > 1.25) return "Above normal";
  if (r < 0.75) return "Below normal";
  return "Near normal";
});
const barMax = computed(() =>
  Math.max(1, result.value.count, result.value.median),
);
</script>

<template>
  <section class="cmp">
    <h3>Compared with the historical median</h3>
    <div class="cmp-pick">
      <select v-model.number="refMonth">
        <option v-for="m in 12" :key="m" :value="m">
          {{ MONTH_NAMES[m - 1] }}
        </option>
      </select>
      <select v-model.number="refYear">
        <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
      </select>
    </div>
    <div class="cmp-row">
      <span>Weighted groups</span>
      <span
        class="cmp-bar"
        :style="{
          width: (result.count / barMax) * 100 + '%',
          background: '#fde725',
        }"
      ></span>
      <b>{{ result.count }}</b>
    </div>
    <div class="cmp-row">
      <span>Weighted median</span>
      <span
        class="cmp-bar"
        :style="{
          width: (result.median / barMax) * 100 + '%',
          background: '#21908d',
        }"
      ></span>
      <b>{{ result.median }}</b>
    </div>
    <p class="cmp-verdict">
      {{ verdict }}
      <template v-if="result.ratio !== null"
        >({{ Math.round(result.ratio * 100) }}% of the median)</template
      >
    </p>
  </section>
</template>
