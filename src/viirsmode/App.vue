<script setup>
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  shallowRef,
  ref,
} from 'vue';
import GlobeView from './GlobeView.vue';
import SearchBar from './SearchBar.vue';
import InfoPanel from './InfoPanel.vue';
import TimelineBar from './TimelineBar.vue';
import {
  buildMonthlyIndex,
  parseHotspotsCsv,
  filterHotspots,
  filterByYears,
  monthlyCounts,
  hotspotsToCsv,
  downloadText,
} from './hotspots.js';
import { fetchLiveFires } from './liveFirms.js';

const hotspots = shallowRef([]);
const monthlyIndex = shallowRef(new Map());
const monthKeys = ref([]);
const hotspotError = ref('');
const area = reactive({ lat: 39.5, lon: -8, radiusKm: 150 });
const range = reactive({ from: 2025, to: 2025 });
const globe = ref(null);
const panelOpen = ref(false);
const selection = ref(null);
const liveMode = ref(false);
const liveHotspots = shallowRef([]);
const liveLoading = ref(false);
const liveError = ref('');
const liveStatus = ref('');
const currentMonth = ref('');
const timeLapseActive = ref(false);
const keyDialogOpen = ref(false);
const mapKey = ref('');
const savingKey = ref(false);
const mapKeyConfigured = ref(false);
const mapKeyManaged = ref(null);
const editingMapKey = ref(false);
const mapKeyStatus = ref('');
const introProgress = ref(0);
const introReady = ref(false);
const started = ref(false);
const starting = ref(false);
const LIVE_REFRESH_MS = 10 * 60 * 1000;
const ACTIVATE_LIVE_AFTER_RESTART = 'viirsmode-live-after-key-setup';
const KEY_SAVED_BEFORE_RESTART = 'viirsmode-key-saved';
let liveRefreshTimer = null;
let introTimer = null;

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
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
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
    const res = await fetch('/viirsmode/hotspots.csv');
    if (!res.ok) throw new Error(`Hotspot CSV request failed (${res.status})`);
    const parsed = parseHotspotsCsv(await res.text());
    if (!parsed.length)
      throw new Error('Hotspot CSV contains no valid detections');
    hotspots.value = parsed;
    monthlyIndex.value = buildMonthlyIndex(parsed);
    monthKeys.value = [...monthlyIndex.value.keys()];
    currentMonth.value = monthKeys.value[0] ?? '';
    range.from = yearBounds.value.max;
    range.to = yearBounds.value.max;
  } catch (error) {
    hotspotError.value = error instanceof Error ? error.message : String(error);
  }

  try {
    const response = await fetch('/api/setup/status', { cache: 'no-store' });
    if (response.ok) {
      const status = await response.json();
      const firmsKey = status.keys?.find((key) => key.id === 'firms');
      mapKeyConfigured.value = Boolean(firmsKey?.set);
      mapKeyManaged.value = firmsKey?.managed ?? null;
    }
  } catch {
    // Historical mode remains available when the local key-setup endpoint is absent.
  }

  if (sessionStorage.getItem(KEY_SAVED_BEFORE_RESTART) === '1') {
    sessionStorage.removeItem(KEY_SAVED_BEFORE_RESTART);
    mapKeyStatus.value = 'NASA FIRMS key saved in local settings.';
  }
  if (sessionStorage.getItem(ACTIVATE_LIVE_AFTER_RESTART) === '1') {
    sessionStorage.removeItem(ACTIVATE_LIVE_AFTER_RESTART);
    await activateLive();
  }
});

onBeforeUnmount(() => {
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

async function fetchLiveHotspots() {
  const payload = await fetchLiveFires();
  if (payload.keyRequired) {
    keyDialogOpen.value = true;
    liveMode.value = false;
    liveHotspots.value = [];
    if (liveRefreshTimer) clearInterval(liveRefreshTimer);
    liveRefreshTimer = null;
    return false;
  }
  liveHotspots.value = payload.fires;
  liveMode.value = true;
  const updatedAt = payload.fetchedAt
    ? new Date(payload.fetchedAt).toLocaleTimeString()
    : 'unknown';
  liveStatus.value = `${payload.count} detections · last 24h · updated ${updatedAt}${payload.stale ? ' · cached data' : ''}`;
  globe.value?.flyToWorld();
  return true;
}

async function activateLive() {
  if (liveMode.value) {
    liveMode.value = false;
    liveHotspots.value = [];
    liveStatus.value = '';
    liveError.value = '';
    if (liveRefreshTimer) clearInterval(liveRefreshTimer);
    liveRefreshTimer = null;
    return;
  }
  if (liveLoading.value) return;
  liveLoading.value = true;
  liveError.value = '';
  try {
    const activated = await fetchLiveHotspots();
    if (activated) {
      timeLapseActive.value = false;
      liveRefreshTimer = setInterval(() => {
        fetchLiveHotspots().catch((error) => {
          liveError.value =
            error instanceof Error ? error.message : String(error);
        });
      }, LIVE_REFRESH_MS);
    }
  } catch (error) {
    liveError.value = error instanceof Error ? error.message : String(error);
  } finally {
    liveLoading.value = false;
  }
}

async function saveMapKey() {
  const value = mapKey.value.trim();
  if (!value || savingKey.value) return;
  savingKey.value = true;
  liveError.value = '';
  try {
    const response = await fetch('/api/setup/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ FIRMS_MAP_KEY: value }),
      cache: 'no-store',
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(
        payload.error || `Could not save NASA FIRMS key (${response.status})`,
      );
    }
    if (started.value) {
      sessionStorage.setItem(ACTIVATE_LIVE_AFTER_RESTART, '1');
    } else {
      sessionStorage.setItem(KEY_SAVED_BEFORE_RESTART, '1');
    }
    keyDialogOpen.value = false;
    mapKey.value = '';
    mapKeyStatus.value = 'Key saved securely. Restarting the app…';
  } catch (error) {
    liveError.value = error instanceof Error ? error.message : String(error);
  } finally {
    savingKey.value = false;
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
      @select="onGlobeSelect"
    />

    <Transition name="app-ui">
      <header v-if="started" class="vm-brand">
        <h1>ViirsMode</h1>
        <p>Burning activity calendar · harmonized MODIS + VIIRS</p>
        <p v-if="hotspotError" class="vm-warn"
          >Hotspot data unavailable: {{ hotspotError }}</p
        >
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
              liveLoading ? 'LOADING LIVE…' : liveMode ? 'EXIT LIVE' : 'GO LIVE'
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
                <p class="intro-eyebrow">OPTIONAL · FOR LIVE DETECTIONS</p>
                <h2>Connect NASA FIRMS</h2>
              </div>
            </div>
            <p class="intro-card-copy">
              Add a free MAP_KEY to explore current global fire activity. You
              can also start with the historical calendar.
            </p>
            <div
              v-if="mapKeyConfigured && !editingMapKey"
              class="intro-key-configured"
            >
              <span>NASA FIRMS key configured</span>
              <span v-if="mapKeyManaged === 'external'"
                >· managed externally</span
              >
              <button
                v-else
                type="button"
                class="intro-key-edit"
                @click="editingMapKey = true"
              >
                UPDATE KEY
              </button>
            </div>
            <div v-else class="intro-key-row">
              <input
                v-model="mapKey"
                type="password"
                autocomplete="off"
                spellcheck="false"
                aria-label="NASA FIRMS MAP_KEY"
                placeholder="Paste your NASA FIRMS MAP_KEY"
                @keyup.enter="saveMapKey"
              />
              <button
                type="button"
                class="intro-key-save"
                :disabled="savingKey || !mapKey.trim()"
                @click="saveMapKey"
              >
                {{ savingKey ? 'SAVING…' : 'ADD KEY' }}
              </button>
            </div>
            <p v-if="mapKeyStatus" class="intro-key-status" role="status">
              {{ mapKeyStatus }}
            </p>
            <p v-if="liveError" class="intro-key-error" role="alert">
              {{ liveError }}
            </p>
            <a
              class="intro-key-link"
              href="https://firms.modaps.eosdis.nasa.gov/api/map_key/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Get a free MAP_KEY from NASA <span aria-hidden="true">↗</span>
            </a>
            <div class="intro-card-divider"></div>
            <button
              type="button"
              class="intro-start"
              :disabled="!introReady || starting || savingKey"
              @click="startExperience"
            >
              <span>{{
                starting ? 'HARMONIZING MODIS + VIIRS…' : 'START EXPLORING'
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

    <div
      v-if="keyDialogOpen"
      class="live-key-backdrop"
      @click.self="keyDialogOpen = false"
    >
      <form
        class="live-key-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="live-key-title"
        @submit.prevent="saveMapKey"
      >
        <button
          type="button"
          class="live-key-close"
          aria-label="Close"
          @click="keyDialogOpen = false"
        >
          ×
        </button>
        <p class="live-kicker">NASA FIRMS · LIVE</p>
        <h2 id="live-key-title">Enter your FIRMS MAP_KEY</h2>
        <p>
          Get a free key from
          <a
            href="https://firms.modaps.eosdis.nasa.gov/api/map_key/"
            target="_blank"
            rel="noopener noreferrer"
            >NASA FIRMS</a
          >. It is saved in this app’s local server configuration and is never
          sent directly to the browser’s NASA requests.
        </p>
        <input
          v-model="mapKey"
          type="password"
          autocomplete="off"
          spellcheck="false"
          required
          autofocus
          aria-label="NASA FIRMS MAP_KEY"
          placeholder="Paste your MAP_KEY"
        />
        <p v-if="liveError" class="live-dialog-error" role="alert">
          {{ liveError }}
        </p>
        <button
          type="submit"
          class="live-key-save"
          :disabled="savingKey || !mapKey.trim()"
        >
          {{ savingKey ? 'SAVING…' : 'SAVE KEY & ENABLE LIVE' }}
        </button>
      </form>
    </div>

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
