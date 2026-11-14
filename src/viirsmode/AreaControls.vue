<script setup>
// area and range are reactive objects owned by App.vue
defineProps({ area: Object, range: Object, count: Number });
defineEmits(['download']);
</script>

<template>
  <div class="ctl">
    <label>Latitude <input type="number" step="0.01" v-model.number="area.lat" /></label>
    <label>Longitude <input type="number" step="0.01" v-model.number="area.lon" /></label>
    <label>Radius (km) <input type="number" min="10" max="1000" step="10" v-model.number="area.radiusKm" /></label>
    <label>From year <input type="number" min="2000" max="2026" v-model.number="range.from" /></label>
    <label>To year <input type="number" min="2000" max="2026" v-model.number="range.to" /></label>
    <button type="button" @click="$emit('download')">
      Download CSV ({{ count }} hotspots)
    </button>
  </div>
</template>