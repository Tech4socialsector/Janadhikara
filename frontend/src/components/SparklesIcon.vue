<template>
  <!-- The assistant's mark: a glowing orb - a ring around a bright core with a
  small highlight - in the app's indigo-to-pink gradient, like a voice assistant
  "listening". Colours are built in, so it reads on any background. -->
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
    <defs>
      <linearGradient id="janadhikara-ai-glow" x1="3" y1="21" x2="21" y2="3" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#6366f1" />
        <stop offset="0.55" stop-color="#a855f7" />
        <stop offset="1" stop-color="#ec4899" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" stroke="url(#janadhikara-ai-glow)" stroke-width="1.75" opacity="0.45" />
    <circle cx="12" cy="12" r="6.25" stroke="url(#janadhikara-ai-glow)" stroke-width="1.75" />
    <circle cx="12" cy="12" r="3" fill="url(#janadhikara-ai-glow)" />
    <circle cx="19.5" cy="4.5" r="1.5" fill="url(#janadhikara-ai-glow)" />
  </svg>
</template>
