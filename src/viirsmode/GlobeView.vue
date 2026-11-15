<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import * as Cesium from 'cesium';
import { hotspotsInView } from './hotspots.js';

const props = defineProps({
  area: { type: Object, required: true },
  hotspots: { type: Array, default: () => [] },
  live: { type: Boolean, default: false },
  intro: { type: Boolean, default: false },
});
const emit = defineEmits(['select']);

const MAX_POINTS = 6000;
const MAX_HOTSPOT_VIEW_HEIGHT = 8000000;
const INTRO_ROTATION_RATE = (Math.PI * 2) / (5 * 60);
const container = ref(null);
const shown = ref(0);
let viewer = null;
let handler = null;
let points = null;
let onCameraMoveEnd = null;
let onIntroFrame = null;
let lastIntroFrame = 0;

function drawHotspots() {
  if (!viewer || !points) return;
  points.removeAll();
  if (props.intro) {
    shown.value = 0;
    return;
  }
  const cameraHeight = viewer.camera.positionCartographic.height;
  if (!props.live && cameraHeight > MAX_HOTSPOT_VIEW_HEIGHT) {
    shown.value = 0;
    return;
  }
  const rectangle = viewer.camera.computeViewRectangle(
    viewer.scene.globe.ellipsoid,
  );
  if (!rectangle) {
    shown.value = 0;
    return;
  }
  const bounds = {
    west: Cesium.Math.toDegrees(rectangle.west),
    east: Cesium.Math.toDegrees(rectangle.east),
    south: Cesium.Math.toDegrees(rectangle.south),
    north: Cesium.Math.toDegrees(rectangle.north),
  };
  const pointLimit = Math.max(
    300,
    Math.floor((MAX_POINTS * 1800000) / Math.max(cameraHeight, 1)),
  );
  const list = hotspotsInView(props.hotspots, bounds, pointLimit);
  let count = 0;
  for (const h of list) {
    points.add({
      id: h,
      position: Cesium.Cartesian3.fromDegrees(h.lon, h.lat, 100),
      pixelSize: 3,
      color: h.sensor === 'MODIS' ? Cesium.Color.YELLOW : Cesium.Color.RED,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.6),
      outlineWidth: 0,
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

function flyToWorld() {
  if (!viewer) return;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(0, 0, 10000000),
  });
}

function startIntro() {
  if (!viewer) return Promise.resolve();
  if (onIntroFrame) {
    viewer.scene.preUpdate.removeEventListener(onIntroFrame);
    onIntroFrame = null;
  }
  return new Promise((resolve) => {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(-18, 8, 8200000),
      duration: 2.8,
      complete: resolve,
      cancel: resolve,
    });
  });
}

defineExpose({ flyToArea, flyToWorld, startIntro });

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
  viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(
    Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK,
  );

  points = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());

  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(
      props.intro ? -28 : props.area.lon,
      props.intro ? 20 : props.area.lat,
      props.intro ? 16000000 : 1800000,
    ),
  });
  drawHotspots();

  if (props.intro) {
    lastIntroFrame = performance.now();
    onIntroFrame = () => {
      const now = performance.now();
      const elapsedSeconds = Math.min((now - lastIntroFrame) / 1000, 0.05);
      lastIntroFrame = now;
      viewer.camera.rotate(
        Cesium.Cartesian3.UNIT_Z,
        -INTRO_ROTATION_RATE * elapsedSeconds,
      );
    };
    viewer.scene.preUpdate.addEventListener(onIntroFrame);
  }

  onCameraMoveEnd = () => drawHotspots();
  viewer.camera.moveEnd.addEventListener(onCameraMoveEnd);

  handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction((click) => {
    const picked = viewer.scene.pick(click.position);
    const hotspot = picked?.id?.date ? picked.id : null;
    if (!hotspot) return;
    emit('select', { lat: hotspot.lat, lon: hotspot.lon, hotspot });
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
});

watch(() => [props.hotspots, props.live, props.intro], drawHotspots);

onBeforeUnmount(() => {
  handler?.destroy();
  if (onCameraMoveEnd) {
    viewer?.camera.moveEnd.removeEventListener(onCameraMoveEnd);
  }
  if (onIntroFrame) {
    viewer?.scene.preUpdate.removeEventListener(onIntroFrame);
  }
  viewer?.destroy();
});
</script>

<template>
  <div class="globe-wrap">
    <div ref="container" class="globe"></div>
    <div v-if="!intro" class="globe-legend">
      <span><i class="dot modis"></i> MODIS</span>
      <span><i class="dot viirs"></i> VIIRS</span>
      <span class="globe-count">
        {{ shown ? `${shown} hotspots` : 'Zoom in to view hotspots' }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.globe-wrap {
  position: absolute;
  inset: 0;
}
.globe {
  position: absolute;
  inset: 0;
}
.globe-legend {
  position: absolute;
  top: 96px;
  left: 20px;
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 6px 10px;
  background: rgba(10, 10, 15, 0.75);
  border-radius: 6px;
  font-size: 12px;
  color: #eee;
  pointer-events: none;
}
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
}
.dot.modis {
  background: #ffeb3b;
}
.dot.viirs {
  background: #ff1744;
}
.globe-count {
  color: #aaa;
}
</style>
