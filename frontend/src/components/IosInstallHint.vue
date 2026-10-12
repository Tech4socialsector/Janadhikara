<template>
  <!-- iPhones have no install button: the app is added from Safari's Share menu. Shown once per device (until closed),
  only in Safari on an iPhone/iPad when the app is not already installed. -->
  <div
    v-if="show"
    class="fixed inset-x-3 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-30 rounded-xl border bg-white p-3.5 shadow-lg dark:border-gray-700 dark:bg-gray-900 sm:hidden"
    role="status"
  >
    <div class="flex items-start gap-3">
      <img src="/pwa-64x64.png" alt="" class="h-10 w-10 flex-shrink-0 rounded-lg" />
      <div class="min-w-0 flex-1 text-sm text-gray-800 dark:text-gray-200">
        <p class="font-semibold">{{ t('Install this app on your iPhone') }}</p>
        <p class="mt-0.5 text-ink-gray-6">
          {{ t('Tap') }}
          <FeatherIcon name="share" class="-mt-0.5 mx-0.5 inline h-4 w-4 align-middle" />
          {{ t('(Share) in Safari, then') }} <b>{{ t('Add to Home Screen') }}</b>. {{ t('It then works offline and keeps your saved data safe.') }}
        </p>
      </div>
      <Button variant="ghost" size="sm" icon="x" :aria-label="t('Close')" @click="dismiss" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
import { t } from '@/utils/translate'

const KEY = 'janadhikara-ios-install-hint'
const read = () => {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}
const closed = ref(!!read())

// iPhone / iPad (iPadOS reports itself as a Mac with touch), in a Safari tab and not yet installed.
const ua = navigator.userAgent
const isIos = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
const isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua)
const installed = window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches
const show = computed(() => isIos && isSafari && !installed && !closed.value)

function dismiss() {
  closed.value = true
  try {
    localStorage.setItem(KEY, '1')
  } catch {
    // shown again next time
  }
}
</script>
