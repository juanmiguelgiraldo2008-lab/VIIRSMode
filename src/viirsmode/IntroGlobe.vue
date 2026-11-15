<template>
  <div
    class="intro-globe"
    :class="{ fading: transitioning }"
    aria-hidden="true"
  >
    <svg
      class="intro-globe-art"
      viewBox="0 0 720 720"
      role="presentation"
      focusable="false"
    >
      <defs>
        <radialGradient id="intro-sphere-fill" cx="36%" cy="32%" r="72%">
          <stop offset="0%" stop-color="#151317" />
          <stop offset="58%" stop-color="#0c0b0e" />
          <stop offset="86%" stop-color="#08080a" />
          <stop offset="100%" stop-color="#291923" />
        </radialGradient>
        <radialGradient id="intro-sphere-glow" cx="65%" cy="38%" r="72%">
          <stop offset="52%" stop-color="#ce718c" stop-opacity="0" />
          <stop offset="88%" stop-color="#b24d71" stop-opacity=".12" />
          <stop offset="100%" stop-color="#d67692" stop-opacity=".46" />
        </radialGradient>
        <pattern
          id="intro-sphere-dots"
          width="7"
          height="7"
          patternUnits="userSpaceOnUse"
        >
          <circle cx="2" cy="2" r=".85" fill="#f3d9e3" fill-opacity=".8" />
        </pattern>
        <clipPath id="intro-sphere-clip">
          <circle cx="360" cy="360" r="270" />
        </clipPath>
        <filter
          id="intro-sphere-blur"
          x="-80%"
          y="-80%"
          width="260%"
          height="260%"
        >
          <feGaussianBlur stdDeviation="9" />
        </filter>
      </defs>

      <circle
        class="intro-globe-halo"
        cx="360"
        cy="360"
        r="278"
        fill="none"
        stroke="#bd6683"
        stroke-opacity=".22"
        stroke-width="26"
        filter="url(#intro-sphere-blur)"
      />
      <circle cx="360" cy="360" r="270" fill="url(#intro-sphere-fill)" />

      <g clip-path="url(#intro-sphere-clip)">
        <rect
          x="90"
          y="90"
          width="540"
          height="540"
          fill="url(#intro-sphere-dots)"
          opacity=".1"
        />
        <rect
          x="90"
          y="90"
          width="540"
          height="540"
          fill="url(#intro-sphere-glow)"
        />
        <g
          class="intro-globe-continent"
          fill="url(#intro-sphere-dots)"
          fill-opacity=".92"
        >
          <path
            d="m246 194 24-19 38 4 22 17-11 20-30 3-14 23-25-5-13-19 9-24Zm22 56 24 11 19 29-8 29-19 19-9 37-19 16-12-25 5-30-14-26 8-29 25-31Zm124-87 39 5 17 20 33 8 11 24-23 13-27-10-12 21-27 4-13-20-26-8 4-31 24-26Zm83 111 33-10 33 19 7 28-23 15-9 34-32 19-16-23 8-29-15-23 14-30Zm-66 89 35 6 22 22-4 38-25 18-21-19-24 8-12-27 10-28 19-18Zm-110 87 28-9 28 16 15 35-16 33-28-10-20-30-18-10 11-25Z"
          />
        </g>
        <g
          class="intro-globe-grid"
          fill="none"
          stroke="#cf91a5"
          stroke-opacity=".08"
        >
          <ellipse cx="360" cy="360" rx="150" ry="270" />
          <ellipse cx="360" cy="360" rx="74" ry="270" />
          <path
            d="M92 360h536M112 270h496M112 450h496M168 180h384M168 540h384"
          />
        </g>
      </g>

      <g class="intro-globe-routes" fill="none" stroke="#d4a0b0">
        <path d="M118 360C224 264 280 478 385 355S532 224 604 322" />
        <path
          d="M202 158C246 281 455 234 519 160M145 507c102-83 191-70 258 11s127 83 180 19"
        />
        <path d="M171 251c99-27 124 148 207 167s91-118 178-118" />
        <path d="M311 105c-35 121 18 174 99 224s61 142 30 242" />
      </g>

      <g class="intro-globe-nodes">
        <circle cx="118" cy="360" r="4" />
        <circle cx="385" cy="355" r="5" />
        <circle cx="604" cy="322" r="4" />
        <circle cx="202" cy="158" r="3" />
        <circle cx="519" cy="160" r="4" />
        <circle cx="403" cy="329" r="3" />
        <circle cx="478" cy="300" r="3" />
        <circle cx="311" cy="105" r="3" />
        <circle cx="440" cy="571" r="4" />
        <circle cx="145" cy="507" r="3" />
        <circle cx="583" cy="537" r="3" />
      </g>

      <circle
        cx="360"
        cy="360"
        r="270"
        fill="none"
        stroke="#d7839c"
        stroke-opacity=".55"
        stroke-width="1.2"
      />
      <ellipse
        class="intro-globe-orbit"
        cx="360"
        cy="360"
        rx="324"
        ry="86"
        fill="none"
        stroke="#8dc4ff"
        stroke-opacity=".4"
        stroke-width="1.2"
        transform="rotate(-27 360 360)"
      />
      <ellipse
        class="intro-globe-orbit intro-globe-orbit--second"
        cx="360"
        cy="360"
        rx="305"
        ry="118"
        fill="none"
        stroke="#8dc4ff"
        stroke-opacity=".22"
        stroke-width="1"
        transform="rotate(58 360 360)"
      />
    </svg>
    <span class="intro-globe-caption">A CONNECTED VIEW OF OUR PLANET</span>
  </div>
</template>

<script setup>
defineProps({
  transitioning: { type: Boolean, default: false },
});
</script>
