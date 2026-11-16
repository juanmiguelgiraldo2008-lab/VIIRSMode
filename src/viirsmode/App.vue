<script setup>
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  shallowRef,
  ref,
} from "vue";
import GlobeView from "./GlobeView.vue";
import IntroGlobe from "./IntroGlobe.vue";
import SearchBar from "./SearchBar.vue";
import InfoPanel from "./InfoPanel.vue";
import TimelineBar from "./TimelineBar.vue";
import {
  buildMonthlyIndex,
  parseHotspotsCsv,
  filterHotspots,
  filterByYears,
  monthlyCounts,
  hotspotsToCsv,
  downloadText,
} from "./hotspots.js";
import { fetchLiveFires } from "./liveFirms.js";

const hotspots = shallowRef([]);
const monthlyIndex = shallowRef(new Map());
const monthKeys = ref([]);
const hotspotError = ref("");
const area = reactive({ lat: 39.5, lon: -8, radiusKm: 150 });
const range = reactive({ from: 2025, to: 2025 });
const globe = ref(null);
const panelOpen = ref(false);
const selection = ref(null);
const liveMode = ref(false);
const liveHotspots = shallowRef([]);
const liveLoading = ref(false);
const liveError = ref("");
const liveStatus = ref("");
const currentMonth = ref("");
const timeLapseActive = ref(false);
const introProgress = ref(0);
const introReady = ref(false);
const started = ref(false);
const starting = ref(false);
const LIVE_REFRESH_MS = 10 * 60 * 1000;
let liveRefreshTimer = null;
let introTimer = null;
let liveRequestVersion = 0;

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
const monthHotspots = computed(
  () => monthlyIndex.value.get(currentMonth.value) ?? [],
);
const displayedHotspots = computed(() => {
  if (!started.value) return [];
  if (liveMode.value) return liveHotspots.value;
  return timeLapseActive.value ? monthHotspots.value : visible.value;
});

onMounted(async () => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    introProgress.value = 100;
    introReady.value = true;
  } else {
    introTimer = setInterval(() => {
      introProgress.value = Math.min(introProgress.value + 2, 100);
      if (introProgress.value === 100) {
        clearInterval(introTimer);
        introReady.value = true;
      }
    }, 30);
  }

  try {
    const res = await fetch("/viirsmode/hotspots.csv");
    if (!res.ok) throw new Error(`Hotspot CSV request failed (${res.status})`);
    const parsed = parseHotspotsCsv(await res.text());
    if (!parsed.length)
      throw new Error("Hotspot CSV contains no valid detections");
    hotspots.value = parsed;
    monthlyIndex.value = buildMonthlyIndex(parsed);
    monthKeys.value = [...monthlyIndex.value.keys()];
    currentMonth.value = monthKeys.value[0] ?? "";
    range.from = yearBounds.value.max;
    range.to = yearBounds.value.max;
  } catch (error) {
    hotspotError.value = error instanceof Error ? error.message : String(error);
  }
});

onBeforeUnmount(() => {
  liveRequestVersion++;
  if (liveRefreshTimer) clearInterval(liveRefreshTimer);
  if (introTimer) clearInterval(introTimer);
});

// Map: every hotspot of the selected years, anywhere
const visible = computed(() =>
  filterByYears(hotspots.value, range.from, range.to),
);
// Calendar: the selected area across the full history
const areaAllYears = computed(() =>
  filterHotspots(
    hotspots.value,
    area,
    yearBounds.value.min,
    yearBounds.value.max,
  ),
);
const months = computed(() =>
  monthlyCounts(areaAllYears.value, yearBounds.value.min, yearBounds.value.max),
);
// CSV: selected area and selected years
const exportRows = computed(() =>
  filterByYears(areaAllYears.value, range.from, range.to),
);
const harmonizedCount = computed(() =>
  Math.round(
    exportRows.value.reduce((sum, hotspot) => sum + (hotspot.weight ?? 1), 0),
  ),
);

function setArea(lat, lon) {
  area.lat = Number(lat.toFixed(3));
  area.lon = Number(lon.toFixed(3));
}

function onGlobeSelect({ lat, lon, hotspot }) {
  if (!hotspot) return;
  setArea(lat, lon);
  area.radiusKm = 50;
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

function selectTimelineMonth(month) {
  currentMonth.value = month;
  timeLapseActive.value = true;
}

function selectReferenceYear(year) {
  range.from = year;
  range.to = year;
}

async function startExperience() {
  if (starting.value || started.value) return;
  starting.value = true;
  await globe.value?.startIntro();
  started.value = true;
  starting.value = false;
}

async function fetchLiveHotspots(requestVersion) {
  const payload = await fetchLiveFires();
  if (requestVersion !== liveRequestVersion) return false;
  liveError.value = "";
  liveHotspots.value = payload.fires;
  liveMode.value = true;
  const updatedAt = new Date(payload.fetchedAt).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
  liveStatus.value = `Live: ${payload.shown} of ${payload.total} detections, NOAA-20 VIIRS, last 24 h · Updated at ${updatedAt}`;
  globe.value?.flyToWorld();
  return true;
}

async function activateLive() {
  if (liveMode.value) {
    liveRequestVersion++;
    liveMode.value = false;
    liveHotspots.value = [];
    liveStatus.value = "";
    liveError.value = "";
    if (liveRefreshTimer) clearInterval(liveRefreshTimer);
    liveRefreshTimer = null;
    return;
  }
  if (liveLoading.value) return;
  liveLoading.value = true;
  liveError.value = "";
  const requestVersion = ++liveRequestVersion;
  try {
    const activated = await fetchLiveHotspots(requestVersion);
    if (activated) {
      timeLapseActive.value = false;
      liveRefreshTimer = setInterval(() => {
        fetchLiveHotspots(requestVersion).catch(() => {
          if (requestVersion === liveRequestVersion) {
            liveError.value = "Live data is unavailable right now";
          }
        });
      }, LIVE_REFRESH_MS);
    }
  } catch {
    if (requestVersion === liveRequestVersion) {
      liveError.value = "Live data is unavailable right now";
    }
  } finally {
    liveLoading.value = false;
  }
}
</script>

<template>
  <div class="vm-root">
    <GlobeView
      ref="globe"
      :area="area"
      :hotspots="displayedHotspots"
      :live="liveMode"
      :intro="!started"
      :intro-transitioning="starting"
      @select="onGlobeSelect"
    />

    <Transition name="app-ui">
      <header v-if="started" class="vm-brand">
        <h1>ViirsMode</h1>
        <p>Burning activity calendar · harmonized MODIS + VIIRS</p>
        <p v-if="hotspotError" class="vm-warn">
          Hotspot data unavailable: {{ hotspotError }}
        </p>
      </header>
    </Transition>

    <Transition name="app-ui">
      <div v-if="started" class="vm-controls">
        <section class="live-control" :class="{ active: liveMode }">
          <button
            type="button"
            class="live-button"
            :disabled="liveLoading"
            @click="activateLive"
          >
            <span class="live-indicator" :class="{ pulsing: liveMode }"></span>
            {{
              liveLoading
                ? "Loading live detections…"
                : liveMode
                  ? "EXIT LIVE"
                  : "GO LIVE"
            }}
          </button>
          <span v-if="liveStatus" class="live-status">{{ liveStatus }}</span>
          <span v-if="liveError" class="live-error">{{ liveError }}</span>
        </section>
        <SearchBar :range="range" @found="onFound" />
      </div>
    </Transition>

    <TimelineBar
      v-if="started && !liveMode && monthKeys.length"
      :month-keys="monthKeys"
      :current-month="currentMonth"
      @select="selectTimelineMonth"
      @start="timeLapseActive = true"
      @stop="timeLapseActive = false"
    />

    <Transition name="intro">
      <main v-if="!started" class="intro-screen" :class="{ ready: introReady }">
        <div class="intro-stars" aria-hidden="true"></div>
        <IntroGlobe :transitioning="starting" />
        <div class="intro-frame">
          <header class="intro-header">
            <a class="intro-wordmark" href="#" @click.prevent>
              <span class="intro-mark" aria-hidden="true">V</span>
              <span>VIIRSMODE</span>
            </a>
            <span class="intro-header-note">EARTH OBSERVATION · 01</span>
          </header>

          <section class="intro-copy">
            <p class="intro-eyebrow">A PLANETARY FIRE ATLAS</p>
            <h1>
              See the patterns<br />
              behind the <span>flames.</span>
            </h1>
            <p class="intro-description">
              Explore a harmonized view of active fire detections from NASA’s
              MODIS and VIIRS satellites.
            </p>
          </section>

          <footer class="intro-footer">
            <div class="intro-progress">
              <span class="intro-progress-label">INITIALIZING EARTH VIEW</span>
              <span class="intro-progress-track">
                <span
                  class="intro-progress-value"
                  :style="{ width: `${introProgress}%` }"
                ></span>
              </span>
              <span class="intro-progress-percent">{{ introProgress }}%</span>
            </div>
            <p>NASA FIRMS DATA · MODIS + VIIRS</p>
          </footer>

          <section class="intro-launch-card">
            <div class="intro-card-heading">
              <span class="intro-live-mark"></span>
              <div>
                <p class="intro-eyebrow">LIVE · NOAA-20 VIIRS</p>
                <h2>Current fire detections</h2>
              </div>
            </div>
            <p class="intro-card-copy">
              Use Go Live inside the globe to display active fire detections
              from the last 24 hours.
            </p>
            <div class="intro-card-divider"></div>
            <button
              type="button"
              class="intro-start"
              :disabled="!introReady || starting"
              @click="startExperience"
            >
              <span>{{
                starting ? "HARMONIZING MODIS + VIIRS…" : "START EXPLORING"
              }}</span>
              <span class="intro-start-arrow" aria-hidden="true">↗</span>
            </button>
            <p class="intro-start-note">
              Historical calendar · defaults to 2025
            </p>
          </section>

          <Transition name="harmonizing">
            <div v-if="starting" class="harmonizing-message" aria-live="polite">
              <span class="harmonizing-line"></span>
              <p>Harmonizing MODIS + VIIRS</p>
              <span>PREPARING GLOBAL VIEW</span>
            </div>
          </Transition>
        </div>
      </main>
    </Transition>

    <InfoPanel
      v-if="panelOpen"
      :selection="selection"
      :months="months"
      :count="exportRows.length"
      :harmonized-count="harmonizedCount"
      :range="range"
      :current-month="currentMonth"
      :area="area"
      @close="panelOpen = false"
      @download="download"
      @select-year="selectReferenceYear"
    />
  </div>
</template>
