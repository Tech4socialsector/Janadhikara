<template>
  <div class="flex flex-col gap-5">
    <div v-if="loading" class="space-y-4">
      <Skeleton v-for="i in 4" :key="i" height="1.5rem" />
    </div>
    <template v-else>
      <!-- How I'm told about new tasks and mentions: the bell, email, and push alerts
      on this device (they still arrive when the app is closed). -->
      <div class="rounded-xl border border-outline-gray-1 p-4">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h3 class="text-sm font-semibold text-ink-gray-9">Alerts</h3>
          <Button size="sm" variant="subtle" icon-left="bell" :loading="enablingAll" @click="enableEverything">Turn on everything</Button>
        </div>
        <div class="flex flex-col gap-4">
          <Switch
            :model-value="prefs.in_app"
            label="In-app notifications"
            description="The bell in the app, and a pop-up when something new arrives."
            @update:model-value="setPref('in_app', $event)"
          />
          <Switch
            :model-value="prefs.email"
            label="Email me"
            description="Get an email when a task is assigned to you."
            @update:model-value="setPref('email', $event)"
          />
          <Switch
            :model-value="push === 'on'"
            :disabled="push === 'unsupported' || push === 'blocked'"
            label="Push alerts on this device"
            :description="pushDescription"
            @update:model-value="setPush"
          />
        </div>
      </div>

      <Switch
        v-model="settings.thread_notify"
        label="Email Threads"
        description="Send notifications for email threads on documents you're involved in."
        @update:model-value="save('thread_notify', $event)"
      />
      <Switch
        v-model="settings.document_follow_notify"
        label="Followed Documents"
        description="Send notifications for documents you follow."
        @update:model-value="save('document_follow_notify', $event)"
      />
      <Switch
        v-model="settings.send_me_a_copy"
        label="Copy of Outgoing Emails"
        description="Send me a copy of emails I send out."
        @update:model-value="save('send_me_a_copy', $event)"
      />
      <Switch
        v-model="settings.mute_sounds"
        label="Mute Sounds"
        description="Mute notification sounds in the app."
        @update:model-value="save('mute_sounds', $event)"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Switch, Button, call, toast } from 'frappe-ui'
import { enablePushAlerts, disablePushAlerts, pushStatus } from '@/data/realtime'
import Skeleton from '@/components/Skeleton.vue'
import { session } from '@/data/session'

const FIELDS = ['thread_notify', 'document_follow_notify', 'send_me_a_copy', 'mute_sounds']

const settings = reactive({
  thread_notify: false,
  document_follow_notify: false,
  send_me_a_copy: false,
  mute_sounds: false,
})
const loading = ref(true)

// --- Alerts: bell / email / push -------------------------------------------
const prefs = reactive({ in_app: true, email: false })
const push = ref('off') // 'on' | 'off' | 'blocked' | 'unsupported'
const enablingAll = ref(false)
const pushDescription = computed(
  () =>
    ({
      on: 'This device gets an alert for new tasks, even when the app is closed.',
      off: 'Get an alert on this phone or computer, even when the app is closed.',
      blocked: 'Blocked in the browser - allow notifications for this site in its settings first.',
      unsupported: "This browser can't receive push alerts. Install the app or use Chrome / Edge / Firefox.",
    })[push.value],
)

call('janadhikara.notification_prefs.get_notification_preferences').then((res) => {
  const data = res?.message ?? res
  prefs.in_app = !!data.in_app
  prefs.email = !!data.email
})
pushStatus().then((status) => (push.value = status))

async function setPref(key, value) {
  const previous = prefs[key]
  prefs[key] = value
  try {
    await call('janadhikara.notification_prefs.set_notification_preferences', { [key]: value ? 1 : 0 })
  } catch {
    prefs[key] = previous
    toast.error('Could not save')
  }
}

async function setPush(on) {
  if (on) {
    if (await enablePushAlerts()) push.value = 'on'
  } else {
    await disablePushAlerts()
    push.value = 'off'
    toast.success('Push alerts are off for this device.')
  }
  push.value = await pushStatus()
}

async function enableEverything() {
  enablingAll.value = true
  try {
    await call('janadhikara.notification_prefs.set_notification_preferences', { in_app: 1, email: 1 })
    prefs.in_app = true
    prefs.email = true
    if (push.value !== 'on' && push.value !== 'unsupported') await setPush(true)
    toast.success('In-app, email and push alerts are on.')
  } catch {
    toast.error('Could not turn everything on')
  } finally {
    enablingAll.value = false
  }
}

call('frappe.client.get_value', {
  doctype: 'User',
  filters: session.user,
  fieldname: FIELDS,
})
  .then((data) => {
    FIELDS.forEach((f) => {
      settings[f] = !!data?.[f]
    })
  })
  .finally(() => {
    loading.value = false
  })

async function save(fieldname, value) {
  try {
    await call('frappe.client.set_value', {
      doctype: 'User',
      name: session.user,
      fieldname,
      value: value ? 1 : 0,
    })
  } catch (e) {
    toast.error('Could not save')
    settings[fieldname] = !value
  }
}
</script>
