<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-semibold text-ink-gray-9 sm:text-xl">Sync Data</h1>
        <p class="mt-0.5 flex items-center gap-1.5 text-xs text-ink-gray-5">
          <span class="h-2 w-2 rounded-full" :class="online ? 'bg-green-500' : 'bg-red-500'" />
          {{ online ? 'Online' : 'Offline' }} · {{ queue.length }} waiting to upload<template v-if="queue.length"> · {{ formatBytes(queueBytes) }}</template>
        </p>
      </template>
      <template #actions>
        <Dropdown v-if="tab === 'sync' && queue.length" :options="downloadOptions" placement="bottom-end">
          <Button variant="solid" icon-left="download">
            <span class="max-sm:hidden">Download copy</span>
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
          <p class="text-base font-semibold text-ink-gray-9">Uploading your data…</p>
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
        <p class="font-semibold">You are offline.</p>
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
      <p class="text-base font-semibold text-ink-gray-8">Everything is synced</p>
      <p class="max-w-sm text-sm text-ink-gray-5">
        Records saved without a connection are listed here until they are uploaded. Nothing is waiting right now.
      </p>
      <p v-if="lastResult" class="flex max-w-sm items-center gap-1.5 text-sm text-ink-green-3">
        <LucideIcon name="circle-check-big" class="h-4 w-4 flex-shrink-0" />
        {{ lastResult }}
      </p>
    </div>

    <template v-if="queue.length">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-sm font-semibold text-ink-gray-8">
          Waiting to upload
          <span v-if="selected.length" class="ml-1 font-normal text-ink-gray-5">· {{ selected.length }} selected</span>
        </h2>
        <div class="flex items-center gap-1">
          <Button v-if="selected.length" size="sm" variant="ghost" @click="clearSelection">Clear</Button>
          <Button v-else-if="isMobile" size="sm" variant="ghost" @click="selectAll">Select all</Button>
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
              <Button variant="ghost" size="sm" icon="edit-2" tooltip="Edit before uploading" aria-label="Edit" :disabled="row.raw.status === 'syncing'" @click="editItem(row.raw)" />
              <Button variant="ghost" size="sm" icon="eye" tooltip="View what is saved" aria-label="View" @click="viewing = row.raw" />
              <Button variant="ghost" size="sm" icon="trash-2" tooltip="Remove from this device" aria-label="Discard" :disabled="row.raw.status === 'syncing'" @click="confirmDiscard = row.raw" />
            </span>
            <span v-else-if="column.key === 'title'" class="truncate font-medium text-ink-gray-9">
              {{ label }}
              <span v-if="row.raw.error" class="block truncate text-xs font-normal text-ink-red-4">{{ row.raw.error }}</span>
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
            <FeatherIcon v-else-if="item.status === 'failed'" name="alert-triangle" class="h-5 w-5" />
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
          </div>
          <div class="flex flex-shrink-0 items-center gap-1" @click.stop>
            <Button variant="ghost" size="sm" icon="edit-2" tooltip="Edit before uploading" aria-label="Edit" :disabled="item.status === 'syncing'" @click="editItem(item)" />
            <Button variant="ghost" size="sm" icon="eye" tooltip="View what is saved" aria-label="View" @click="viewing = item" />
            <Button variant="ghost" size="sm" icon="trash-2" tooltip="Remove from this device" aria-label="Discard" :disabled="item.status === 'syncing'" @click="confirmDiscard = item" />
          </div>
        </li>
      </ul>
    </template>

    </template>

    <template v-else>
    <!-- Download tab: the offline copy of masters and linked records. -->
    <section class="mb-4 rounded-2xl border border-outline-gray-1 bg-surface-white p-5 shadow-sm">
      <div class="flex flex-wrap items-center gap-4">
        <span class="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-7">
          <LucideIcon name="database" class="h-7 w-7" />
        </span>
        <div class="min-w-0 flex-1 max-sm:basis-[calc(100%-4.5rem)]">
          <h2 class="text-base font-semibold text-ink-gray-9">Offline reference data</h2>
          <p class="text-sm text-ink-gray-5">
            <template v-if="packInfo">Saved on this device {{ savedAt(new Date(packInfo.generated.replace(' ', 'T')).getTime()) }}.</template>
            <template v-else>Not downloaded yet. Without it, dropdowns for masters and linked records stay empty when there is no internet.</template>
          </p>
        </div>
        <div class="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Button v-if="packInfo" variant="solid" icon-left="eye" class="max-sm:flex-1" @click="showBrowse = true">Browse</Button>
          <Button
            variant="solid"
            icon-left="lucide-cloud-download"
            class="max-sm:flex-1"
            :disabled="!online || packState.downloading"
            :loading="packState.downloading"
            @click="downloadPack"
          >
            {{ packInfo ? 'Update' : 'Download' }}
          </Button>
          <Button v-if="packInfo" variant="ghost" icon="trash-2" tooltip="Remove the downloaded copy from this device" aria-label="Remove" @click="showRemovePack = true" />
        </div>
      </div>

      <!-- Size and contents at a glance. -->
      <dl v-if="packInfo" class="mt-5 grid grid-cols-3 gap-3">
        <div class="rounded-xl bg-surface-gray-1 px-3 py-3 text-center">
          <dt class="text-xs text-ink-gray-5">File size</dt>
          <dd class="mt-0.5 text-lg font-semibold text-ink-gray-9">{{ formatBytes(packInfo.bytes) }}</dd>
          <dd class="text-2xs text-ink-gray-5">compressed</dd>
        </div>
        <div class="rounded-xl bg-surface-gray-1 px-3 py-3 text-center">
          <dt class="text-xs text-ink-gray-5">Records</dt>
          <dd class="mt-0.5 text-lg font-semibold text-ink-gray-9">{{ totalRecords }}</dd>
        </div>
        <div class="rounded-xl bg-surface-gray-1 px-3 py-3 text-center">
          <dt class="text-xs text-ink-gray-5">Lists</dt>
          <dd class="mt-0.5 text-lg font-semibold text-ink-gray-9">{{ Object.keys(packInfo.counts).length }}</dd>
        </div>
      </dl>

      <div v-if="packState.downloading" class="mt-4">
        <p class="mb-1.5 text-sm text-ink-gray-6">{{ packState.step }}</p>
        <div class="h-2 overflow-hidden rounded-full bg-surface-gray-3">
          <div class="sync-bar h-full rounded-full bg-blue-500" :style="{ width: packState.percent + '%' }" />
        </div>
      </div>
      <p v-if="packState.error" class="mt-3 text-sm text-ink-red-4">{{ packState.error }}</p>
      <p v-if="!online && !packInfo" class="mt-3 text-sm text-ink-gray-5">You need internet to download. Do it before you go offline next time.</p>
      <p class="mt-3 flex items-center gap-1.5 text-xs text-ink-gray-5">
        <FeatherIcon name="lock" class="h-3.5 w-3.5" />
        Field data only - no images or files. Only what you are allowed to see, kept encrypted on this device and removed when you are back online.
      </p>
    </section>

    </template>

    <!-- Look through the downloaded copy. -->
    <Dialog v-model="showBrowse" :options="{ title: 'Offline reference data', size: '4xl' }">
      <template #body-content>
        <div class="mb-3 flex flex-col gap-2 sm:flex-row">
          <FormControl type="select" v-model="browseDoctype" :options="browseOptions" class="sm:w-64" />
          <TextInput v-model="browseSearch" type="text" placeholder="Search" class="flex-1" />
        </div>
        <div class="max-h-[55vh] overflow-auto rounded-lg border border-outline-gray-1">
          <table class="w-full text-left text-sm">
            <thead class="sticky top-0 bg-surface-gray-1 text-xs text-ink-gray-5">
              <tr><th v-for="c in browseColumns" :key="c" class="whitespace-nowrap px-3 py-2 font-medium">{{ c.replace(/_/g, ' ') }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in browseRows" :key="i" class="border-t border-outline-gray-1">
                <td v-for="(cell, j) in row" :key="j" class="max-w-[16rem] truncate px-3 py-1.5 text-ink-gray-8">{{ cell }}</td>
              </tr>
              <tr v-if="!browseRows.length"><td :colspan="browseColumns.length || 1" class="px-3 py-6 text-center text-ink-gray-5">Nothing here.</td></tr>
            </tbody>
          </table>
        </div>
        <p class="mt-2 text-xs text-ink-gray-5">Showing up to 200 rows.</p>
        <div class="mt-3 flex justify-end"><Button size="sm" icon-left="x" @click="showBrowse = false">Close</Button></div>
      </template>
    </Dialog>

    <Dialog v-model="showRemovePack" :options="{ title: 'Remove the downloaded copy?', size: 'sm' }">
      <template #body-content>
        <p class="text-sm text-ink-gray-6">Pickers for masters and linked records will be empty offline until you download it again.</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button size="sm" icon-left="x" @click="showRemovePack = false">Keep</Button>
          <Button size="sm" variant="solid" theme="red" icon-left="trash-2" @click="doRemovePack">Remove</Button>
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
          <Button size="sm" icon-left="x" @click="viewing = null">Close</Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showDiscard" :options="{ title: 'Remove from this device?', size: 'sm' }">
      <template #body-content>
        <p class="text-sm text-ink-gray-6">
          "{{ confirmDiscard?.title }}" has not been uploaded. Removing it deletes the only copy.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <Button size="sm" icon-left="x" @click="confirmDiscard = null">Keep</Button>
          <Button size="sm" variant="solid" theme="red" icon-left="trash-2" @click="doDiscard">Remove</Button>
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
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { queue, syncState, syncAll, discard, downloadJson, downloadCsv, loadQueue } from '@/data/offlineQueue'
import { packInfo, packState, downloadPack, removePack, getPack, loadPackInfo } from '@/data/offlinePack'
import { setPageTitle } from '@/data/pageTitle'

setPageTitle('Sync Data')
loadQueue()
loadPackInfo()

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
const STATUS_LABEL = { pending: 'Waiting', syncing: 'Uploading', done: 'Uploaded', failed: 'Failed' }
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
  }[item.status]
}

const viewRows = computed(() =>
  Object.entries(viewing.value?.doc || {})
    .filter(([key, value]) => value !== null && value !== '' && key !== 'doctype')
    .map(([key, value]) => [key.replace(/_/g, ' '), typeof value === 'object' ? JSON.stringify(value, null, 1) : String(value)]),
)

const editItem = (item) => router.push({ name: 'OfflineEdit', params: { offlineId: item.id } })

// --- Offline reference data -----------------------------------------------------------
const packMenu = [
  { label: 'Browse the data', icon: 'eye', onClick: () => (showBrowse.value = true) },
  { label: 'Remove from this device', icon: 'trash-2', onClick: () => (showRemovePack.value = true) },
]
const steps = [
  { title: 'Save as usual', text: 'No internet? Fill in and save a form. It is kept safely on this device.' },
  { title: 'Come back online', text: 'Your saved records stay here, encrypted. Nothing is sent on its own.' },
  { title: 'Upload here', text: 'Check the list, then press Upload. Each record is removed once it is uploaded.' },
]
const queueBytes = computed(() => new Blob([JSON.stringify(queue.value.map((i) => i.doc))]).size)
const tab = ref('sync')
const tabButtons = computed(() => [
  { label: queue.value.length ? `Offline Sync (${queue.value.length})` : 'Offline Sync', value: 'sync', icon: 'upload-cloud' },
  { label: 'Download', value: 'download', icon: 'download-cloud' },
])
const showRemovePack = ref(false)
const showBrowse = ref(false)
const browseDoctype = ref('')
const browseSearch = ref('')
const pack = ref(null)
const totalRecords = computed(() => Object.values(packInfo.value?.counts || {}).reduce((a, b) => a + b, 0))
const formatBytes = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)
const browseOptions = computed(() =>
  Object.entries(packInfo.value?.counts || {}).map(([d, n]) => ({ label: `${d} (${n})`, value: d })),
)
watch(showBrowse, async (open) => {
  if (!open) return
  pack.value = await getPack()
  if (!browseDoctype.value || !pack.value?.doctypes?.[browseDoctype.value]) browseDoctype.value = browseOptions.value[0]?.value || ''
})
const browseTable = computed(() => pack.value?.doctypes?.[browseDoctype.value])
const browseColumns = computed(() => (browseTable.value?.columns || []).slice(0, 7))
const browseRows = computed(() => {
  const table = browseTable.value
  if (!table) return []
  const q = browseSearch.value.trim().toLowerCase()
  const cols = browseColumns.value.length
  return table.rows
    .filter((r) => !q || r.some((c) => String(c ?? '').toLowerCase().includes(q)))
    .slice(0, 200)
    .map((r) => r.slice(0, cols))
})
async function doRemovePack() {
  showRemovePack.value = false
  await removePack()
  toast.success('Removed from this device')
}

async function startSync() {
  const { uploaded, failed } = await syncAll(selected.value.length ? [...selected.value] : null)
  clearSelection()
  if (failed) toast.error(`${failed} could not be uploaded - see the red items.`)
  if (uploaded) {
    toast.success(`${uploaded} uploaded`)
    lastResult.value = `${uploaded} uploaded - nothing is stored on this device any more`
  }
}

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
