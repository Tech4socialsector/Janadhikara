<template>
  <!-- One tile on the Home page: a tinted rounded icon over its label. A link when it has a `to`, else a button. -->
  <component
    :is="to ? 'router-link' : 'button'"
    v-bind="to ? { to } : { type: 'button' }"
    class="group flex flex-col items-center gap-1.5 rounded-xl px-1 py-2 text-center transition-colors duration-150 hover:bg-surface-gray-2"
  >
    <span
      class="module-tile-icon relative flex h-12 w-12 items-center justify-center rounded-2xl transition-transform duration-150 ease-out group-hover:-translate-y-0.5 group-active:scale-95 sm:h-16 sm:w-16"
      :class="tint"
    >
      <SyncCloudIcon v-if="syncIcon" class="h-6 w-6 sm:h-7 sm:w-7" />
      <LucideIcon v-else :name="icon" class="h-6 w-6 sm:h-7 sm:w-7" />
      <span
        v-if="badge > 0"
        class="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1 text-xs font-semibold text-white ring-2 ring-white dark:ring-gray-900"
      >
        {{ badge > 99 ? '99+' : badge }}
      </span>
    </span>
    <span class="line-clamp-2 text-xs font-medium leading-tight text-ink-gray-8 sm:text-sm">{{ label }}</span>
  </component>
</template>

<script setup>
import LucideIcon from '@/components/LucideIcon.vue'
import SyncCloudIcon from '@/components/SyncCloudIcon.vue'

defineProps({
  icon: { type: String, default: 'file-text' },
  label: { type: String, required: true },
  to: { type: [Object, String], default: null },
  tint: { type: String, default: '' },
  badge: { type: Number, default: 0 },
  syncIcon: { type: Boolean, default: false },
})
</script>
