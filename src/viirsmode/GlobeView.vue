<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import * as Cesium from 'cesium';
import { areaBbox } from './hotspots.js';

const props = defineProps({ area: { type: Object, required: true } });
const emit = defineEmits(['select']);
const container = ref(null);
let viewer = null;
let handler = null;

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
      color: Cesium.Color.RED,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
    },
  });
  viewer.entities.add({
    rectangle: {
      coordinates: Cesium.Rectangle.fromDegrees(b.west, b.south, b.east, b.north),
      material: Cesium.Color.RED.withAlpha(0.2),
      outline: true,
      outlineColor: Cesium.Color.RED,
      height: 0,
    },
  });
}

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

  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(props.area.lon, props.area.lat, 1800000),
  });
  drawArea();

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



onBeforeUnmount(() => {
  handler?.destroy();
  viewer?.destroy();
});
</script>

<template>
  <div ref="container" class="globe"></div>
</template>

<style scoped>
.globe {
  width: 100%;
  height: 420px;
  border-radius: 8px;
  overflow: hidden;
}
</style>