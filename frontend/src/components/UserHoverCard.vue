<template>
  <Popover trigger="hover" :hover-delay="0.15" :placement="placement" class="w-full">
    <template #target>
      <slot />
    </template>
    <template #body-main>
      <div class="w-64 max-w-[80vw] overflow-hidden rounded-lg">
        <div class="flex items-center gap-3 bg-gradient-to-br from-gray-50 to-white p-4 dark:from-gray-800 dark:to-gray-900">
          <Avatar
            :image="session.user_image"
            :label="session.full_name || session.user"
            size="2xl"
            shape="circle"
            class="ring-4 ring-white dark:ring-gray-900"
          />
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
              {{ session.full_name || session.user }}
            </div>
            <div class="truncate text-xs text-gray-500 dark:text-gray-400">
              {{ session.user }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { Popover, Avatar } from 'frappe-ui'
import { session } from '@/data/session'

defineProps({
  placement: { type: String, default: 'right-end' },
})
</script>
