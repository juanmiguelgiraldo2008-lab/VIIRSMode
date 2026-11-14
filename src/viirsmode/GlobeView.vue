<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import * as Cesium from 'cesium';
import { areaBbox } from './hotspots.js';

const props = defineProps({
  area: { type: Object, required: true },
  hotspots: { type: Array, default: () => [] },
});
const emit = defineEmits(['select']);

const MAX_POINTS = 8000;
const container = ref(null);
const shown = ref(0);
let viewer = null;
let handler = null;
let points = null;

function drawArea() {
  if (!viewer) return;
  const { lat, lon, radiusKm } = props.area;
  if (![lat, lon, radiusKm].every(Number.isFinite)) return;
  const b = areaBbox(props.area);
  viewer.entities.removeAll();
  viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lon, lat),
    point: {
      pixelSize: 10,
      color: Cesium.Color.CYAN,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
    },
  });
  viewer.entities.add({
    rectangle: {
      coordinates: Cesium.Rectangle.fromDegrees(b.west, b.south, b.east, b.north),
      material: Cesium.Color.CYAN.withAlpha(0.15),
      outline: true,
      outlineColor: Cesium.Color.CYAN,
      height: 0,
    },
  });
}

function drawHotspots() {
  if (!viewer || !points) return;
  points.removeAll();
  const list = props.hotspots;
  const step = Math.max(1, Math.ceil(list.length / MAX_POINTS));
  let count = 0;
  for (let i = 0; i < list.length; i += step) {
    const h = list[i];
    if (!Number.isFinite(h.lat) || !Number.isFinite(h.lon)) continue;
    points.add({
      position: Cesium.Cartesian3.fromDegrees(h.lon, h.lat, 100),
      pixelSize: 5,
      color: h.sensor === 'MODIS' ? Cesium.Color.YELLOW : Cesium.Color.RED,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.6),
      outlineWidth: 1,
    });
    count++;
  }
  shown.value = count;
}

function flyToArea() {
  if (!viewer) return;
  const { lat, lon, radiusKm } = props.area;
  if (![lat, lon, radiusKm].every(Number.isFinite)) return;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(
      lon,
      lat,
      Math.max(radiusKm * 6000, 200000),
    ),
  });
}

defineExpose({ flyToArea });

onMounted(() => {
  viewer = new Cesium.Viewer(container.value, {
    baseLayer: new Cesium.ImageryLayer(
      new Cesium.UrlTemplateImageryProvider({
        url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 18,
        credit: 'Esri World Imagery',
      }),
    ),
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
  });

  points = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(props.area.lon, props.area.lat, 1800000),
  });
  drawArea();
  drawHotspots();

  handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction((click) => {
    const cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid);
    if (!cartesian) return;
    const c = Cesium.Cartographic.fromCartesian(cartesian);
    emit('select', {
      lat: Cesium.Math.toDegrees(c.latitude),
      lon: Cesium.Math.toDegrees(c.longitude),
    });
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
});

watch(() => [props.area.lat, props.area.lon, props.area.radiusKm], drawArea);
watch(() => props.hotspots, drawHotspots);

onBeforeUnmount(() => {
  handler?.destroy();
  viewer?.destroy();
});
</script>

<template>
  <div class="globe-wrap">
    <div ref="container" class="globe"></div>
    <div class="globe-legend">
      <span><i class="dot modis"></i> MODIS</span>
      <span><i class="dot viirs"></i> VIIRS</span>
      <span class="globe-count">
        Showing {{ shown }} of {{ hotspots.length }} hotspots
      </span>
    </div>
  </div>
</template>

<style scoped>
.globe-wrap { position: relative; }
.globe {
  width: 100%;
  height: 420px;
  border-radius: 8px;
  overflow: hidden;
}
.globe-legend {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 6px 10px;
  background: rgba(10, 10, 15, 0.75);
  border-radius: 6px;
  font-size: 12px;
  color: #eee;
}
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
}
.dot.modis { background: #ffeb3b; }
.dot.viirs { background: #ff1744; }
.globe-count { color: #aaa; }
</style>