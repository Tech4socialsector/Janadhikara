<template>
  <!-- The signed-in user's card: avatar, name, email and (optionally) Settings /
  Log out. Opens on hover. On a touch screen a tap does the same - the target slot
  gets `open` / `isOpen`, so a tap can open it (a hover trigger alone never
  fires there). Used for the desktop sidebar footer and the mobile bottom bar. -->
  <Popover trigger="hover" :hover-delay="0.15" :placement="placement" class="w-full">
    <template #target="{ open, isOpen }">
      <slot :open="open" :is-open="isOpen" />
    </template>
    <template #body-main="{ close }">
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
            <div class="truncate text-base font-semibold text-ink-gray-9">
              {{ session.full_name || session.user }}
            </div>
            <div class="truncate text-sm text-ink-gray-5">
              {{ session.user }}
            </div>
          </div>
        </div>
        <div v-if="withActions" class="flex flex-col gap-1 border-t border-outline-gray-1 p-2">
          <Button variant="ghost" class="w-full !justify-start" icon-left="settings" @click="close(); openSettingsDialog()">
            Settings
          </Button>
          <Button variant="ghost" class="w-full !justify-start" icon-left="log-out" @click="close(); logoutResource.submit()">
            Log out
          </Button>
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { Popover, Avatar, Button } from 'frappe-ui'
import { session, logoutResource } from '@/data/session'
import { openSettingsDialog } from '@/data/settingsDialog'

defineProps({
  placement: { type: String, default: 'right-end' },
  // Show Settings and Log out under the name (the phone has no sidebar footer).
  withActions: { type: Boolean, default: false },
})
</script>
