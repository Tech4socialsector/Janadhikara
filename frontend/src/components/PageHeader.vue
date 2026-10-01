<template>
  <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
    <div class="min-w-0">
      <slot name="title" />
      <p v-if="description" class="mt-0.5 text-sm text-ink-gray-5">{{ description }}</p>
    </div>

    <!-- Desktop: the actions move up into the header bar (TopNavbar's
    #page-header-actions), next to the breadcrumbs, the way Helpdesk puts a
    page's primary buttons. `defer` waits for that element to exist. Phones
    have no header bar (MobileShell), so there it stays in place, here. -->
    <Teleport v-if="$slots.actions" to="#page-header-actions" defer :disabled="isMobile">
      <div class="flex flex-shrink-0 items-center gap-2">
        <slot name="actions" />
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'

defineProps({
  description: { type: String, default: '' },
})

const isMobile = useBreakpoints(breakpointsTailwind).smaller('sm')
</script>
