<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-semibold text-ink-gray-9 sm:text-xl">{{ t('Sync Data') }}</h1>
        <p class="mt-0.5 flex items-center gap-1.5 text-xs text-ink-gray-5">
          <span class="h-2 w-2 rounded-full" :class="online ? 'bg-green-500' : 'bg-red-500'" />
          {{ online ? 'Online' : 'Offline' }} · {{ queue.length }} waiting to upload<template v-if="queue.length"> · {{ formatBytes(queueBytes) }}</template>
        </p>
      </template>
      <template #actions>
        <Dropdown v-if="tab === 'sync' && queue.length" :options="downloadOptions" placement="bottom-end">
          <Button variant="solid" icon-left="download">
            <span class="max-sm:hidden">{{ t('Download copy') }}</span>
          </Button>
        </Dropdown>
        <Button
          v-if="tab === 'sync'"
          variant="solid"
          icon-left="lucide-cloud-upload"
          :disabled="!queue.length || !online || syncState.running"
          :loading="syncState.running"
          @click="startSync"
        >
          {{ syncState.running ? 'Uploading…' : selected.length ? `Upload ${selected.length} selected` : 'Upload all' }}
        </Button>
      </template>
    </PageHeader>

    <TabButtons v-model="tab" :buttons="tabButtons" class="mb-4 max-sm:w-full" />

    <template v-if="tab === 'sync'">
    <!-- Uploading: a rising cloud, a bar and a count. -->
    <div v-if="syncState.running" class="mb-4 rounded-2xl border border-outline-gray-1 bg-surface-white p-5 shadow-sm">
      <div class="flex items-center gap-4">
        <span class="sync-cloud flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-surface-blue-2 text-ink-blue-3">
          <LucideIcon name="cloud-upload" class="h-7 w-7" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-base font-semibold text-ink-gray-9">{{ t('Uploading your data…') }}</p>
          <p class="text-sm text-ink-gray-5">{{ syncState.done }} of {{ syncState.total }} done</p>
          <div class="mt-3 h-2.5 overflow-hidden rounded-full bg-surface-gray-3">
            <div class="sync-bar h-full rounded-full bg-blue-500" :style="{ width: progress + '%' }" />
          </div>
        </div>
      </div>
    </div>

    <!-- Offline: what is going on and what can still be done. -->
    <div
      v-if="!online"
      class="mb-4 flex items-start gap-3 rounded-2xl border border-outline-amber-1 bg-surface-amber-1 p-4 text-sm text-ink-gray-8"
    >
      <FeatherIcon name="wifi-off" class="mt-0.5 h-5 w-5 flex-shrink-0 text-ink-amber-3" />
      <div>
        <p class="font-semibold">{{ t('You are offline.') }}</p>
        <p class="text-ink-gray-6">
          Records you save are kept on this device. You can <b>download a copy</b> to see all of it, and upload it when the connection is back.
        </p>
      </div>
    </div>

    <!-- All caught up. -->
    <div
      v-if="!queue.length && !syncState.running"
      class="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-outline-gray-2 bg-surface-white py-16 text-center"
    >
      <span class="sync-pop flex h-16 w-16 items-center justify-center rounded-full bg-surface-green-2 text-ink-green-3">
        <LucideIcon name="circle-check-big" class="h-8 w-8" />
      </span>
      <p class="text-base font-semibold text-ink-gray-8">{{ t('Everything is synced') }}</p>
      <p class="max-w-sm text-sm text-ink-gray-5">
        {{ t('Records saved without a connection are listed here until they are uploaded. Nothing is waiting right now.') }}
      </p>
      <p v-if="lastResult" class="flex max-w-sm items-center gap-1.5 text-sm text-ink-green-3">
        <LucideIcon name="circle-check-big" class="h-4 w-4 flex-shrink-0" />
        {{ lastResult }}
      </p>
    </div>

    <template v-if="queue.length">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-sm font-semibold text-ink-gray-8">
          {{ t('Waiting to upload') }}
          <span v-if="selected.length" class="ml-1 font-normal text-ink-gray-5">· {{ selected.length }} selected</span>
        </h2>
        <div class="flex items-center gap-1">
          <Button v-if="selected.length" size="sm" variant="ghost" @click="clearSelection">{{ t('Clear') }}</Button>
          <Button v-else-if="isMobile" size="sm" variant="ghost" @click="selectAll">{{ t('Select all') }}</Button>
        </div>
      </div>

      <!-- Grid (the default on a computer): one row per saved record. -->
      <ListView
        v-if="!isMobile"
        :key="gridKey"
        :columns="columns"
        :rows="rows"
        row-key="id"
        :options="{ selectable: true, showTooltip: false, resizeColumn: false }"
        @update:selections="(sel) => (selected = Array.from(sel))"
      >
        <template #cell="{ column, row, item }">
          <ListRowItem :column="column" :row="row" :item="item" v-slot="{ label }">
            <span v-if="column.key === 'status'" class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" :class="statusChip(row.raw)">
              <span v-if="row.raw.status === 'syncing'" class="sync-spinner h-3 w-3 rounded-full border-2 border-current border-t-transparent" />
              <LucideIcon v-else-if="row.raw.status === 'done'" name="circle-check-big" class="sync-pop h-3.5 w-3.5" />
              {{ label }}
            </span>
            <span v-else-if="column.key === 'actions'" class="flex items-center gap-1" @click.stop>
              <Button v-if="row.raw.status === 'conflict'" variant="subtle" size="sm" @click="resolving = row.raw">{{ t('Resolve') }}</Button>
              <Button v-else-if="row.raw.status === 'failed'" variant="ghost" size="sm" icon="rotate-cw" :tooltip="t('Try again')" :aria-label="t('Try again')" :disabled="!online || syncState.running" @click="retry(row.raw)" />
              <Button variant="ghost" size="sm" icon="edit-2" :tooltip="t('Edit before uploading')" :aria-label="t('Edit')" :disabled="row.raw.status === 'syncing'" @click="editItem(row.raw)" />
              <Button variant="ghost" size="sm" icon="eye" :tooltip="t('View what is saved')" :aria-label="t('View')" @click="viewing = row.raw" />
              <Button variant="ghost" size="sm" icon="trash-2" :tooltip="t('Remove from this device')" :aria-label="t('Discard')" :disabled="row.raw.status === 'syncing'" @click="confirmDiscard = row.raw" />
            </span>
            <span v-else-if="column.key === 'title'" class="truncate font-medium text-ink-gray-9">
              {{ label }}
              <span v-if="row.raw.error" class="block truncate text-xs font-normal text-ink-red-4">{{ row.raw.error }}</span>
              <span v-else-if="row.raw.waitingOn" class="block truncate text-xs font-normal text-ink-amber-3">Waiting for {{ row.raw.waitingOn }} to upload first</span>
              <span v-else-if="row.raw.status === 'conflict'" class="block truncate text-xs font-normal text-ink-amber-3">{{ t('Changed on the server meanwhile - choose which to keep') }}</span>
            </span>
            <span v-else class="truncate">{{ label }}</span>
          </ListRowItem>
        </template>
        <template #default>
          <ListHeader />
          <ListRows />
        </template>
      </ListView>

      <!-- Cards (phones, or by choice): the same records, one tappable card each. -->
      <ul v-else class="space-y-2.5 pb-24">
        <li
          v-for="item in queue"
          :key="item.id"
          class="flex items-center gap-3 rounded-xl border bg-surface-white px-3 py-3 shadow-sm"
          :class="selected.includes(item.id) ? 'border-outline-gray-5 ring-1 ring-outline-gray-5' : 'border-outline-gray-1'"
          @click="toggle(item.id)"
        >
          <input
            type="checkbox"
            class="form-checkbox h-4 w-4 flex-shrink-0 !rounded-[3px] border-gray-300"
            :checked="selected.includes(item.id)"
            :aria-label="`Select ${item.title}`"
            @click.stop
            @change="toggle(item.id)"
          />
          <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full" :class="statusTile(item)">
            <span v-if="item.status === 'syncing'" class="sync-spinner h-5 w-5 rounded-full border-2 border-current border-t-transparent" />
            <LucideIcon v-else-if="item.status === 'done'" name="circle-check-big" class="sync-pop h-5 w-5" />
            <FeatherIcon v-else-if="item.status === 'failed' || item.status === 'conflict'" name="alert-triangle" class="h-5 w-5" />
            <FeatherIcon v-else name="clock" class="h-5 w-5" />
          </span>
          <div class="min-w-0 flex-1">
            <p class="truncate text-[15px] font-medium text-ink-gray-9">{{ item.title }}</p>
            <p class="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-ink-gray-5">
              <span>{{ item.doctype }}</span>
              <span class="rounded-full bg-surface-gray-2 px-1.5 py-0.5">{{ item.action === 'insert' ? 'New' : 'Edited' }}</span>
              <span>saved {{ savedAt(item.createdAt) }}</span>
            </p>
            <p v-if="item.error" class="mt-1 text-xs text-ink-red-4">{{ item.error }}</p>
            <p v-else-if="item.waitingOn" class="mt-1 text-xs text-ink-amber-3">Waiting for {{ item.waitingOn }} to upload first</p>
            <p v-else-if="item.status === 'conflict'" class="mt-1 text-xs text-ink-amber-3">{{ t('Changed on the server meanwhile - choose which to keep') }}</p>
          </div>
          <div class="flex flex-shrink-0 items-center gap-1" @click.stop>
            <Button v-if="item.status === 'conflict'" variant="subtle" size="sm" @click="resolving = item">{{ t('Resolve') }}</Button>
            <Button v-else-if="item.status === 'failed'" variant="ghost" size="sm" icon="rotate-cw" :aria-label="t('Try again')" :disabled="!online || syncState.running" @click="retry(item)" />
            <Button variant="ghost" size="sm" icon="edit-2" :tooltip="t('Edit before uploading')" :aria-label="t('Edit')" :disabled="item.status === 'syncing'" @click="editItem(item)" />
            <Button variant="ghost" size="sm" icon="eye" :tooltip="t('View what is saved')" :aria-label="t('View')" @click="viewing = item" />
            <Button variant="ghost" size="sm" icon="trash-2" :tooltip="t('Remove from this device')" :aria-label="t('Discard')" :disabled="item.status === 'syncing'" @click="confirmDiscard = item" />
          </div>
        </li>
      </ul>
    </template>

    </template>

    <template v-else>
    <!-- Download tab: one offline copy of everything the person may see. -->
    <section class="mb-4 rounded-2xl border border-outline-gray-1 bg-surface-white p-5 shadow-sm">
      <div class="flex flex-wrap items-center gap-4">
        <span class="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-7">
          <LucideIcon name="database" class="h-7 w-7" />
        </span>
        <div class="min-w-0 flex-1 max-sm:basis-[calc(100%-4.5rem)]">
          <h2 class="text-base font-semibold text-ink-gray-9">{{ t('Offline copy') }}</h2>
          <p class="text-sm text-ink-gray-5">
            <template v-if="storeInfo">Saved on this device {{ savedAt(new Date(storeInfo.generated.replace(' ', 'T')).getTime()) }}.</template>
            <template v-else>{{ t('Not downloaded yet. Download it to open, search and edit your records, and use the dashboard, with no internet.') }}</template>
          </p>
        </div>
        <div class="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Button
            variant="solid"
            icon-left="lucide-cloud-download"
            class="max-sm:flex-1"
            :disabled="!online || storeState.downloading"
            :loading="storeState.downloading"
            @click="doDownload"
          >
            {{ storeInfo ? 'Update' : 'Download' }}
          </Button>
          <Button v-if="storeInfo" variant="ghost" icon="trash-2" :tooltip="t('Remove the offline copy from this device')" :aria-label="t('Remove')" @click="showRemove = true" />
        </div>
      </div>

      <!-- Size and contents at a glance. -->
      <dl v-if="storeInfo" class="mt-5 grid grid-cols-3 gap-3">
        <div class="rounded-xl bg-surface-gray-1 px-3 py-3 text-center">
          <dt class="text-xs text-ink-gray-5">{{ t('Stored size') }}</dt>
          <dd class="mt-0.5 text-lg font-semibold text-ink-gray-9">{{ formatBytes(storeInfo.bytes) }}</dd>
          <dd class="text-2xs text-ink-gray-5">{{ t('compressed') }}</dd>
        </div>
        <div class="rounded-xl bg-surface-gray-1 px-3 py-3 text-center">
          <dt class="text-xs text-ink-gray-5">{{ t('Records') }}</dt>
          <dd class="mt-0.5 text-lg font-semibold text-ink-gray-9">{{ totalRecords }}</dd>
        </div>
        <div class="rounded-xl bg-surface-gray-1 px-3 py-3 text-center">
          <dt class="text-xs text-ink-gray-5">{{ t('Lists') }}</dt>
          <dd class="mt-0.5 text-lg font-semibold text-ink-gray-9">{{ Object.keys(storeInfo.counts).length }}</dd>
        </div>
      </dl>

      <!-- Is this device ready for offline? -->
      <div class="mt-5 rounded-xl border border-outline-gray-1 p-4">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h3 class="text-sm font-semibold text-ink-gray-9">{{ t('Ready for offline?') }}</h3>
          <Button size="sm" variant="ghost" icon-left="refresh-cw" :loading="checking" @click="runReadiness">{{ t('Check again') }}</Button>
        </div>
        <ul class="space-y-2">
          <li v-for="c in readiness" :key="c.key" class="flex items-start gap-2.5 text-sm">
            <span
              class="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full"
              :class="c.ok ? 'bg-surface-green-2 text-ink-green-3' : 'bg-surface-red-2 text-ink-red-4'"
            >
              <FeatherIcon :name="c.ok ? 'check' : 'x'" class="h-3 w-3" />
            </span>
            <p class="min-w-0">
              <span class="font-medium text-ink-gray-8">{{ c.label }}</span>
              <span class="block text-xs text-ink-gray-5">{{ c.detail }}</span>
            </p>
          </li>
        </ul>
      </div>

      <div v-if="storeState.downloading" class="mt-4">
        <p class="mb-1.5 text-sm text-ink-gray-6">{{ storeState.step }}</p>
        <div class="h-2 overflow-hidden rounded-full bg-surface-gray-3">
          <div class="sync-bar h-full rounded-full bg-blue-500" :style="{ width: storeState.percent + '%' }" />
        </div>
      </div>
      <p v-if="storeState.error" class="mt-3 text-sm text-ink-red-4">{{ storeState.error }}</p>
      <p v-if="!online && !storeInfo" class="mt-3 text-sm text-ink-gray-5">{{ t('You need internet to download. Do it before you go offline next time.') }}</p>

      <!-- Look through what is stored; tap a record to open it. -->
      <div v-if="storeInfo" class="mt-5">
        <div class="mb-3 flex flex-col gap-2 sm:flex-row">
          <FormControl type="select" v-model="myDoctype" :options="myOptions" class="sm:w-64" />
          <TextInput v-model="mySearch" type="text" :placeholder="t('Search')" class="flex-1" />
        </div>
        <ul class="max-h-[50vh] divide-y divide-outline-gray-1 overflow-auto rounded-lg border border-outline-gray-1">
          <li v-for="r in myRows" :key="r.name">
            <button class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left hover:bg-surface-gray-1" @click="openRecord(r)">
              <span class="min-w-0">
                <span class="block truncate text-sm font-medium text-ink-gray-9">{{ r.label }}</span>
                <span class="block truncate text-xs text-ink-gray-5">{{ r.name }}<template v-if="r.edited"> · edited here, waiting to upload</template></span>
              </span>
              <FeatherIcon name="chevron-right" class="h-4 w-4 flex-shrink-0 text-ink-gray-4" />
            </button>
          </li>
          <li v-if="!myRows.length" class="px-3 py-6 text-center text-sm text-ink-gray-5">{{ t('Nothing here.') }}</li>
        </ul>
      </div>
      <p class="mt-3 flex items-center gap-1.5 text-xs text-ink-gray-5">
        <FeatherIcon name="lock" class="h-3.5 w-3.5" />
        {{ t('Only what you are allowed to see - no files or photos. Kept encrypted on this device, only for you, and removed when you sign out. Nothing is downloaded or uploaded on its own.') }}
      </p>
    </section>

    </template>

    <!-- Someone changed the same fields on the server: choose. -->
    <Dialog v-model="showResolve" :options="{ title: 'Changed on the server meanwhile', size: '2xl' }">
      <template #body-content>
        <p class="mb-3 text-sm text-ink-gray-6">
          "{{ resolving?.title }}" was changed by someone else after you saved your edit. These fields differ:
        </p>
        <div class="max-h-[50vh] space-y-3 overflow-y-auto pr-1">
          <div v-for="f in resolving?.conflict || []" :key="f.fieldname" class="rounded-lg border border-outline-gray-1 p-3 text-sm">
            <p class="mb-2 font-medium text-ink-gray-9">{{ f.label }}</p>
            <div class="grid gap-2 sm:grid-cols-2">
              <div class="rounded bg-surface-blue-1 p-2"><p class="text-xs text-ink-gray-5">{{ t('Your edit') }}</p><p class="whitespace-pre-wrap break-words text-ink-gray-9">{{ show(f.mine) }}</p></div>
              <div class="rounded bg-surface-gray-1 p-2"><p class="text-xs text-ink-gray-5">{{ t('On the server') }}</p><p class="whitespace-pre-wrap break-words text-ink-gray-9">{{ show(f.server) }}</p></div>
            </div>
          </div>
        </div>
        <div class="mt-4 flex justify-end gap-2">
          <Button size="sm" icon-left="x" @click="resolving = null">{{ t('Decide later') }}</Button>
          <Button size="sm" icon-left="server" :disabled="!online || syncState.running" @click="resolve('server')">{{ t('Keep server') }}</Button>
          <Button size="sm" variant="solid" icon-left="check" :disabled="!online || syncState.running" :loading="syncState.running" @click="resolve('mine')">{{ t('Keep mine') }}</Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showRemove" :options="{ title: 'Remove the offline copy?', size: 'sm' }">
      <template #body-content>
        <p class="text-sm text-ink-gray-6">{{ t('You will not be able to open your records or use the dashboard without internet until you download again. Edits not yet uploaded stay in the waiting list.') }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button size="sm" icon-left="x" @click="showRemove = false">{{ t('Keep') }}</Button>
          <Button size="sm" variant="solid" theme="red" icon-left="trash-2" @click="doRemove">{{ t('Remove') }}</Button>
        </div>
      </template>
    </Dialog>

    <!-- What is saved, field by field. -->
    <Dialog v-model="showView" :options="{ title: viewing?.title || 'Saved data', size: '2xl' }">
      <template #body-content>
        <dl v-if="viewing" class="max-h-[60vh] space-y-2 overflow-y-auto pr-1 text-sm">
          <div v-for="[key, value] in viewRows" :key="key" class="grid grid-cols-[10rem_1fr] gap-3 border-b border-outline-gray-1 pb-2">
            <dt class="truncate text-ink-gray-5">{{ key }}</dt>
            <dd class="whitespace-pre-wrap break-words text-ink-gray-9">{{ value }}</dd>
          </div>
        </dl>
        <div class="mt-4 flex justify-end">
          <Button size="sm" icon-left="x" @click="viewing = null">{{ t('Close') }}</Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showDiscard" :options="{ title: 'Remove from this device?', size: 'sm' }">
      <template #body-content>
        <p class="text-sm text-ink-gray-6">
          "{{ confirmDiscard?.title }}" has not been uploaded. Removing it deletes the only copy.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <Button size="sm" icon-left="x" @click="confirmDiscard = null">{{ t('Keep') }}</Button>
          <Button size="sm" variant="solid" theme="red" icon-left="trash-2" @click="doDiscard">{{ t('Remove') }}</Button>
        </div>
      </template>
    </Dialog>
  </AppLayout>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import { online } from '@/data/connection'
import { Button, Dialog, Dropdown, FeatherIcon, FormControl, ListHeader, ListRowItem, ListRows, ListView, TabButtons, TextInput, toast } from 'frappe-ui'
import { t } from '@/utils/translate'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { queue, syncState, syncAll, resolveConflict, discard, downloadJson, downloadCsv, loadQueue } from '@/data/offlineQueue'
import { session } from '@/data/session'
import { storeInfo, storeState, downloadOffline, removeStore, getTable, loadStoreInfo, checkOfflineReadiness } from '@/data/offlineStore'
import { setPageTitle } from '@/data/pageTitle'

setPageTitle('Sync Data')
loadQueue()
loadStoreInfo(session.user)

const router = useRouter()

const isMobile = useBreakpoints(breakpointsTailwind).smaller('sm')

// Grid by default on a computer; the cards layout is one click away (phones always use cards).
const layout = ref('grid') // grid on a computer, cards on a phone
const layoutButtons = [
  { label: 'Grid', value: 'grid', icon: 'grid', hideLabel: true, tooltip: 'Grid' },
  { label: 'Cards', value: 'cards', icon: 'list', hideLabel: true, tooltip: 'Cards' },
]
const columns = [
  { label: 'Record', key: 'title', width: '22%' },
  { label: 'Doctype', key: 'doctype', width: '16%' },
  { label: 'Change', key: 'change', width: '9%' },
  { label: 'Saved on', key: 'saved', width: '16%' },
  { label: 'Status', key: 'status', width: '14%' },
  { label: '', key: 'actions', width: '11%' },
]
const STATUS_LABEL = { pending: 'Waiting', syncing: 'Uploading', done: 'Uploaded', failed: 'Failed', conflict: 'Conflict' }
const rows = computed(() =>
  queue.value.map((item) => ({
    id: item.id,
    title: item.title,
    doctype: item.doctype,
    change: item.action === 'insert' ? 'New' : 'Edited',
    saved: savedAt(item.createdAt),
    status: STATUS_LABEL[item.status],
    actions: '',
    raw: item,
  })),
)

// Which records are ticked (the grid reports its own selection; the cards use toggle()).
const selected = ref([])
const gridKey = ref(0)
const toggle = (id) => {
  selected.value = selected.value.includes(id) ? selected.value.filter((i) => i !== id) : [...selected.value, id]
}
const selectAll = () => {
  selected.value = queue.value.map((i) => i.id) // cards only - the grid has its own header checkbox
}
const clearSelection = () => {
  selected.value = []
  gridKey.value++
}
const statusChip = (item) => statusTile(item)
watch(layout, () => clearSelection())
const viewing = ref(null)
const confirmDiscard = ref(null)
const lastResult = ref(null)

const showView = computed({ get: () => !!viewing.value, set: (v) => !v && (viewing.value = null) })
const showDiscard = computed({ get: () => !!confirmDiscard.value, set: (v) => !v && (confirmDiscard.value = null) })

const progress = computed(() => (syncState.value.total ? Math.round((syncState.value.done / syncState.value.total) * 100) : 0))

const downloadOptions = [
  { label: 'Download as JSON', icon: 'file-text', onClick: downloadJson },
  { label: 'Download as CSV (Excel)', icon: 'file', onClick: downloadCsv },
]

function savedAt(ms) {
  return new Date(ms).toLocaleString([], { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

function statusTile(item) {
  return {
    pending: 'bg-surface-amber-2 text-ink-amber-3',
    syncing: 'bg-surface-blue-2 text-ink-blue-3',
    done: 'bg-surface-green-2 text-ink-green-3',
    failed: 'bg-surface-red-2 text-ink-red-4',
    conflict: 'bg-surface-amber-2 text-ink-amber-3',
  }[item.status]
}

const viewRows = computed(() =>
  Object.entries(viewing.value?.doc || {})
    .filter(([key, value]) => value !== null && value !== '' && key !== 'doctype')
    .map(([key, value]) => [key.replace(/_/g, ' '), typeof value === 'object' ? JSON.stringify(value, null, 1) : String(value)]),
)

const editItem = (item) => router.push({ name: 'OfflineEdit', params: { offlineId: item.id } })

// --- Offline reference data -----------------------------------------------------------
const steps = [
  { title: 'Save as usual', text: 'No internet? Fill in and save a form. It is kept safely on this device.' },
  { title: 'Come back online', text: 'Your saved records stay here, encrypted. Nothing is sent on its own.' },
  { title: 'Upload here', text: 'Check the list, then press Upload. Each record is removed once it is uploaded.' },
]
const queueBytes = computed(() => new Blob([JSON.stringify(queue.value.map((i) => i.doc))]).size)
const readiness = ref([])
const checking = ref(false)
async function runReadiness() {
  checking.value = true
  try {
    readiness.value = await checkOfflineReadiness()
  } finally {
    checking.value = false
  }
}
const tab = ref('sync')
const tabButtons = computed(() => [
  { label: queue.value.length ? `Offline Sync (${queue.value.length})` : 'Offline Sync', value: 'sync', icon: 'upload-cloud' },
  { label: 'Download', value: 'download', icon: 'download-cloud' },
])
const showRemove = ref(false)
const formatBytes = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)
watch([tab, () => storeInfo.value, () => storeState.value.downloading], ([t, , busy]) => {
  if (t === 'download' && !busy) runReadiness()
}, { immediate: true })
async function doDownload() {
  await downloadOffline(session.user)
  if (!storeState.value.error) toast.success('The offline copy is saved on this device')
}
async function doRemove() {
  showRemove.value = false
  await removeStore()
  myList.value = []
  toast.success('Removed from this device')
}

async function startSync() {
  const { uploaded, failed, conflicts } = await syncAll(selected.value.length ? [...selected.value] : null)
  clearSelection()
  if (conflicts) toast.error(`${conflicts} changed on the server meanwhile - press Resolve on the amber items.`)
  if (failed) toast.error(`${failed} could not be uploaded - see the red items.`)
  if (uploaded) {
    toast.success(`${uploaded} uploaded`)
    lastResult.value = `${uploaded} uploaded - nothing is stored on this device any more`
  }
}

const retry = async (item) => {
  const { uploaded } = await syncAll([item.id])
  if (uploaded) toast.success('Uploaded')
}

// --- Conflicts -------------------------------------------------------------------------------
const resolving = ref(null)
const showResolve = computed({ get: () => !!resolving.value, set: (v) => !v && (resolving.value = null) })
const show = (v) => (v == null || v === '' ? '(empty)' : typeof v === 'object' ? JSON.stringify(v, null, 1) : String(v))
async function resolve(choice) {
  const item = resolving.value
  if (!item) return
  const outcome = await resolveConflict(item.id, choice)
  resolving.value = null
  if (choice === 'server') toast.success('Kept the server version - your edit was removed from this device.')
  else if (outcome === 'done') toast.success('Uploaded - your edit replaced the server values.')
  else if (outcome === 'failed') toast.error('Could not upload - see the red item.')
}

// --- Look through the offline copy ----------------------------------------------------------------------
const myDoctype = ref('')
const mySearch = ref('')
const myList = ref([])
const myTitleField = ref('name')
const totalRecords = computed(() => Object.values(storeInfo.value?.counts || {}).reduce((a, b) => a + b, 0))
const myOptions = computed(() => Object.entries(storeInfo.value?.counts || {}).filter(([d]) => !storeInfo.value?.children?.includes(d)).map(([d, n]) => ({ label: `${d} (${n})`, value: d })))
watch([myDoctype, () => storeInfo.value], async () => {
  if (!myDoctype.value || !myOptions.value.some((o) => o.value === myDoctype.value)) myDoctype.value = myOptions.value[0]?.value || ''
  const table = myDoctype.value ? await getTable(myDoctype.value) : null
  myTitleField.value = table?.title_field || 'name'
  myList.value = table?.docs || []
}, { immediate: true })
const myRows = computed(() => {
  const q = mySearch.value.trim().toLowerCase()
  return myList.value
    .map((d) => ({
      name: d.name,
      label: d[myTitleField.value] || d.name,
      edited: queue.value.some((i) => i.action === 'update' && i.doctype === myDoctype.value && i.name === d.name),
    }))
    .filter((r) => !q || `${r.label} ${r.name}`.toLowerCase().includes(q))
    .slice(0, 200)
})
const openRecord = (r) => router.push({ name: 'OfflineRecord', params: { doctype: myDoctype.value, name: r.name } })

async function doDiscard() {
  const item = confirmDiscard.value
  confirmDiscard.value = null
  if (item) await discard(item.id)
}

// Back online with things waiting? A gentle nudge - the upload is always the user's call.
watch(online, (isOnline, wasOnline) => {
  if (isOnline && !wasOnline && queue.value.length) toast.info(`You are back online - ${queue.value.length} waiting to upload.`)
})
</script>

<style scoped>
.sync-cloud {
  animation: sync-float 1.2s ease-in-out infinite;
}
.sync-bar {
  transition: width 0.35s ease;
  background-image: linear-gradient(90deg, rgba(255, 255, 255, 0.35) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.35) 50%, rgba(255, 255, 255, 0.35) 75%, transparent 75%);
  background-size: 1rem 1rem;
  animation: sync-stripes 0.8s linear infinite;
}
.sync-spinner {
  animation: sync-spin 0.8s linear infinite;
}
.sync-pop {
  animation: sync-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes sync-float {
  0%, 100% { transform: translateY(2px); }
  50% { transform: translateY(-4px); }
}
@keyframes sync-stripes {
  to { background-position: 1rem 0; }
}
@keyframes sync-spin {
  to { transform: rotate(360deg); }
}
@keyframes sync-pop {
  from { transform: scale(0.4); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .sync-cloud, .sync-bar, .sync-spinner, .sync-pop { animation: none; }
}
</style>
