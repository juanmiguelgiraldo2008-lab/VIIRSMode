<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  monthKeys: { type: Array, default: () => [] },
  currentMonth: { type: String, default: "" },
});
const emit = defineEmits(["select", "start", "stop"]);

const speed = ref(1);
const playing = ref(false);
let timer = null;
let playbackIndex = 0;

const currentIndex = computed(() => {
  const index = props.monthKeys.indexOf(props.currentMonth);
  return index < 0 ? 0 : index;
});
const monthLabel = computed(() => {
  if (!props.currentMonth) return "No data";
  const date = new Date(`${props.currentMonth}-01T00:00:00Z`);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
});
const noteHighlighted = computed(
  () => Number(props.currentMonth.slice(0, 4)) >= 2012,
);

function clearTimer() {
  if (timer !== null) clearInterval(timer);
  timer = null;
}

function stopPlayback() {
  clearTimer();
  playing.value = false;
  emit("stop");
}

function advanceMonth() {
  const nextIndex = playbackIndex + 1;
  if (nextIndex >= props.monthKeys.length) {
    stopPlayback();
    return;
  }
  playbackIndex = nextIndex;
  emit("select", props.monthKeys[nextIndex]);
  if (nextIndex === props.monthKeys.length - 1) stopPlayback();
}

function startPlayback() {
  if (!props.monthKeys.length) return;
  playbackIndex = currentIndex.value;
  if (playbackIndex >= props.monthKeys.length - 1) {
    playbackIndex = 0;
    emit("select", props.monthKeys[playbackIndex]);
  }
  playing.value = true;
  emit("start");
  clearTimer();
  timer = setInterval(advanceMonth, 400 / speed.value);
}

function togglePlayback() {
  if (playing.value) {
    stopPlayback();
    return;
  }
  startPlayback();
}

function selectMonth(event) {
  playbackIndex = Number(event.target.value);
  const key = props.monthKeys[playbackIndex];
  if (key) emit("select", key);
}

watch(speed, () => {
  if (!playing.value) return;
  clearTimer();
  timer = setInterval(advanceMonth, 400 / speed.value);
});

onBeforeUnmount(clearTimer);
</script>

<template>
  <section class="timeline-bar" aria-label="Historical fire timeline">
    <div class="timeline-controls">
      <button
        class="timeline-play"
        type="button"
        :disabled="monthKeys.length < 2"
        :aria-label="playing ? 'Pause time-lapse' : 'Play time-lapse'"
        @click="togglePlayback"
      >
        <span aria-hidden="true">{{ playing ? "Ⅱ" : "▶" }}</span>
      </button>
      <input
        class="timeline-slider"
        type="range"
        min="0"
        :max="Math.max(monthKeys.length - 1, 0)"
        :value="currentIndex"
        :disabled="monthKeys.length < 2"
        aria-label="Timeline month"
        @input="selectMonth"
      />
      <output class="timeline-month">{{ monthLabel }}</output>
      <div class="timeline-speeds" aria-label="Playback speed">
        <button
          v-for="rate in [0.5, 1, 2]"
          :key="rate"
          type="button"
          :class="{ selected: speed === rate }"
          :aria-pressed="speed === rate"
          @click="speed = rate"
        >
          {{ rate }}x
        </button>
      </div>
    </div>
    <p class="timeline-note" :class="{ highlighted: noteHighlighted }">
      VIIRS (S-NPP) joins in 2012 and NOAA-20 in 2018. Raw counts are not
      comparable across these dates; the calendar uses harmonized counts.
    </p>
  </section>
</template>
