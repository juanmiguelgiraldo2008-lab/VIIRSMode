<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue';
import * as Cesium from 'cesium';

const emit = defineEmits(['select']);
const container = ref(null);
let viewer = null;
let handler = null;

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

  // Start over Portugal
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(-8, 39.5, 1800000),
  });

  handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction((click) => {
    const cartesian = viewer.camera.pickEllipsoid(
      click.position,
      viewer.scene.globe.ellipsoid,
    );
    if (!cartesian) return;
    const c = Cesium.Cartographic.fromCartesian(cartesian);
    const lat = Cesium.Math.toDegrees(c.latitude);
    const lon = Cesium.Math.toDegrees(c.longitude);
    viewer.entities.removeAll();
    viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat),
      point: {
        pixelSize: 12,
        color: Cesium.Color.RED,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
      },
    });
    emit('select', { lat, lon });
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
});

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