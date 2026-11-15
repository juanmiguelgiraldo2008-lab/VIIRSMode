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
import {
  parseHotspotsCsv,
  filterHotspots,
  filterByYears,
  monthlyCounts,
  hotspotsToCsv,
  downloadText,
} from './hotspots.js';
import { fetchLiveFires } from './liveFirms.js';

const hotspots = shallowRef([]);
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
const keyDialogOpen = ref(false);
const mapKey = ref('');
const savingKey = ref(false);
const LIVE_REFRESH_MS = 10 * 60 * 1000;
const ACTIVATE_LIVE_AFTER_RESTART = 'viirsmode-live-after-key-setup';
let liveRefreshTimer = null;

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

onMounted(async () => {
  try {
    const res = await fetch('/viirsmode/hotspots.csv');
    if (!res.ok) throw new Error(`Hotspot CSV request failed (${res.status})`);
    const parsed = parseHotspotsCsv(await res.text());
    if (!parsed.length)
      throw new Error('Hotspot CSV contains no valid detections');
    hotspots.value = parsed;
    range.from = yearBounds.value.max;
    range.to = yearBounds.value.max;
  } catch (error) {
    hotspotError.value = error instanceof Error ? error.message : String(error);
  }

  if (sessionStorage.getItem(ACTIVATE_LIVE_AFTER_RESTART) === '1') {
    sessionStorage.removeItem(ACTIVATE_LIVE_AFTER_RESTART);
    await activateLive();
  }
});

onBeforeUnmount(() => {
  if (liveRefreshTimer) clearInterval(liveRefreshTimer);
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
    sessionStorage.setItem(ACTIVATE_LIVE_AFTER_RESTART, '1');
    keyDialogOpen.value = false;
    mapKey.value = '';
    liveStatus.value =
      'Key saved securely. The app is restarting to enable LIVE…';
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
      :hotspots="liveMode ? liveHotspots : visible"
      :live="liveMode"
      @select="onGlobeSelect"
    />

    <header class="vm-brand">
      <h1>ViirsMode</h1>
      <p>Burning activity calendar · harmonized MODIS + VIIRS</p>
      <p v-if="hotspotError" class="vm-warn"
        >Hotspot data unavailable: {{ hotspotError }}</p
      >
    </header>

    <div class="vm-controls">
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
      @close="panelOpen = false"
      @download="download"
    />
  </div>
</template>
