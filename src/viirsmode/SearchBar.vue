<script setup>
import { ref } from "vue";

defineProps({ range: Object });
const emit = defineEmits(["found"]);

const query = ref("");
const busy = ref(false);
const error = ref("");

function parseCoords(text) {
  const m = text.match(/^(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)$/);
  if (!m) return null;
  const lat = parseFloat(m[1]);
  const lon = parseFloat(m[2]);
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { lat, lon };
}

async function search() {
  error.value = "";
  const text = query.value.trim();
  if (!text) return;
  const coords = parseCoords(text);
  if (coords) {
    emit("found", { ...coords, name: null });
    return;
  }
  busy.value = true;
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(text)}`,
    );
    const list = await res.json();
    if (!list.length) {
      error.value = "Place not found";
      return;
    }
    const [south, north, west, east] = list[0].boundingbox.map(Number);
    const midLat = (south + north) / 2;
    const halfLat = ((north - south) / 2) * 111;
    const halfLon =
      ((east - west) / 2) * 111 * Math.cos((midLat * Math.PI) / 180);
    const radiusKm = Math.min(
      400,
      Math.max(10, Math.round(Math.max(halfLat, halfLon))),
    );
    emit("found", {
      lat: parseFloat(list[0].lat),
      lon: parseFloat(list[0].lon),
      name: list[0].display_name,
      radiusKm,
    });
  } catch {
    error.value = "Search failed. Try coordinates, like 40.4, -3.7";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="search">
    <div class="search-row">
      <input
        v-model="query"
        type="text"
        placeholder="Search location: place name or lat, lon"
        @keyup.enter="search"
      />
      <button type="button" :disabled="busy" @click="search">Go</button>
    </div>
    <div class="search-opts">
      <label
        >From year
        <input
          type="number"
          min="2000"
          max="2026"
          v-model.number="range.from"
        />
      </label>
      <label
        >To year
        <input type="number" min="2000" max="2026" v-model.number="range.to" />
      </label>
    </div>
    <span v-if="error" class="search-err">{{ error }}</span>
  </div>
</template>
