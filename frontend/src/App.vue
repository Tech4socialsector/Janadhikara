<template>
  <FrappeUIProvider>
    <router-view v-slot="{ Component, route }">
      <!-- DoctypeList/DoctypeForm/EmailAccountForm reuse the same component
      instance when only a route param changes (different doctypeRoute or
      name, same route record) - Vue Router's default behavior. Their data
      loading (useMeta/useDoc/useNewDoc) runs once at setup and isn't wired
      to react to those params changing, so without a fresh mount per
      param value, navigating from one doctype/record to another via the
      sidebar silently kept showing the previous one until a hard refresh
      forced a real remount. Keying only these routes (not every route)
      keeps Home/Dashboard/Worklist - which have no such params - from
      remounting their shell on every navigation for no reason. -->
      <!-- A page that fails while it is being drawn would otherwise leave a white screen
      (seen after going Back): say so and offer a way out instead. -->
      <div v-if="pageError" class="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <p class="text-base font-medium text-ink-gray-8">{{ t("This page didn't load properly.") }}</p>
        <div class="flex gap-2">
          <Button variant="subtle" @click="goBack">{{ t('Go back') }}</Button>
          <Button variant="solid" @click="reloadPage">{{ t('Try again') }}</Button>
        </div>
      </div>
      <component
        v-else
        :is="Component"
        :key="route.meta.remountOnParamChange ? route.fullPath : route.name"
      />
    </router-view>
    <PwaUpdatePrompt />
  </FrappeUIProvider>
</template>

<script setup>
import { onErrorCaptured, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, FrappeUIProvider } from 'frappe-ui'
import { t } from '@/utils/translate'
import '@/data/session'
import '@/data/theme'
import { brandingResource } from '@/data/branding'
import PwaUpdatePrompt from '@/components/PwaUpdatePrompt.vue'

// Only failures while a page is set up or drawn blank the screen; a failing button click does not.
// Vue names the step in words while developing and as an error code in the built app.
const DRAWING = /setup function|render function|mounted hook|runtime-(0|1|bm|m)$/
const pageError = ref(false)
const route = useRoute()
const router = useRouter()
onErrorCaptured((error, instance, info) => {
  if (DRAWING.test(String(info))) pageError.value = true
  return true // still reported by app.config.errorHandler
})
// the next page gets a fresh start
watch(() => route.fullPath, () => (pageError.value = false))
const goBack = () => (history.length > 1 ? router.back() : router.push({ name: 'Home' }))
const reloadPage = () => window.location.reload()

// The browser tab icon should match whatever logo is actually configured
// in App Settings (app_logo, editable by an admin at any time) rather than
// a static file baked in at build time. index.html ships a default
// favicon.png as a fallback for the moment before this resolves (and for
// sites that haven't set a logo at all).
watch(
  () => brandingResource.data?.app_logo,
  (logo) => {
    if (!logo) return
    const link = document.getElementById('app-favicon')
    if (link) link.href = logo
  },
  { immediate: true },
)

// Same reasoning as the favicon above, for the PWA install icon: the
// manifest vite-plugin-pwa injects at build time (<link rel="manifest">,
// no id/customization hook available) points at static PNGs baked in from
// whatever logo existed at build time. janadhikara.api.get_pwa_manifest
// generates the manifest live from App Setting.app_logo instead - swapping
// the link here (rather than templating janadhikara.html server-side)
// matches how the favicon itself is handled, and works from the very
// first load since it doesn't depend on any other resource resolving
// first.
const manifestLink = document.querySelector('link[rel="manifest"]')
if (manifestLink) {
  manifestLink.href = '/api/method/janadhikara.api.get_pwa_manifest'
}
</script>
