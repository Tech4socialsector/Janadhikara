<template>
  <Tooltip :text="`Search (${shortcutLabel})`">
    <button
      class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
      @click="open = true"
    >
      <FeatherIcon name="search" class="h-4 w-4" />
    </button>
  </Tooltip>

  <!-- No :options.title - the input itself is the dialog's only real
  header. autofocus so opening (click or Cmd/Ctrl+K) drops the cursor
  straight into the field, same as the old inline input did on focus. -->
  <Dialog v-model="open" :options="{ size: 'lg' }">
    <template #body>
      <div class="flex flex-col">
        <div class="relative flex-shrink-0 border-b p-3 dark:border-gray-800">
          <FeatherIcon name="search" class="pointer-events-none absolute left-6 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            ref="inputRef"
            v-model="query"
            type="text"
            placeholder="Search or type a command"
            class="h-9 w-full rounded border border-gray-200 bg-gray-50 pl-8 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-gray-300 focus:outline-none focus:ring-1 focus:ring-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500"
            @keydown.esc="open = false"
            @keydown.up.prevent="moveHighlight(-1)"
            @keydown.down.prevent="moveHighlight(1)"
            @keydown.enter.prevent="selectHighlighted"
          />
        </div>

        <div v-if="query.trim()" class="max-h-96 overflow-y-auto py-2">
          <div v-if="moduleMatches.length" class="mb-1">
            <div class="px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
              Modules
            </div>
            <button
              v-for="item in moduleMatches"
              :key="`mod-${item.route}`"
              :class="rowClass(flatKey('mod', item))"
              @click="goToList(item)"
              @mouseenter="highlightKey = flatKey('mod', item)"
            >
              <FeatherIcon name="folder" class="h-4 w-4 flex-shrink-0 text-gray-400" />
              <span class="text-sm text-gray-900 dark:text-gray-100">Go to {{ item.label || item.doctype_name }}</span>
            </button>
          </div>

          <div v-if="createMatches.length" class="mb-1">
            <div class="px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
              Create New
            </div>
            <button
              v-for="item in createMatches"
              :key="`new-${item.route}`"
              :class="rowClass(flatKey('new', item))"
              @click="goToNew(item)"
              @mouseenter="highlightKey = flatKey('new', item)"
            >
              <FeatherIcon name="plus" class="h-4 w-4 flex-shrink-0 text-gray-400" />
              <span class="text-sm text-gray-900 dark:text-gray-100">New {{ item.label || item.doctype_name }}</span>
            </button>
          </div>

          <div>
            <div class="px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
              Search Results
            </div>
            <div v-if="searchResource.loading" class="px-3 py-3 text-center text-sm text-gray-500">
              Searching...
            </div>
            <div
              v-else-if="!moduleMatches.length && !createMatches.length && searchRecords.length === 0"
              class="px-3 py-3 text-center text-sm text-gray-500 dark:text-gray-400"
            >
              No results.
            </div>
            <button
              v-for="(item, idx) in searchRecords"
              :key="`rec-${item.doctype_name}-${item.name}-${idx}`"
              :class="rowClass(`rec-${idx}`, true)"
              @click="selectRecord(item)"
              @mouseenter="highlightKey = `rec-${idx}`"
            >
              <span class="text-sm text-gray-900 dark:text-gray-100">{{ item.description || item.name }}</span>
              <span class="text-xs text-gray-500 dark:text-gray-400">{{ item.doctype_name }}</span>
            </button>
          </div>
        </div>

        <div v-else class="px-3 py-6 text-center text-sm text-gray-400 dark:text-gray-500">
          Start typing to search records, or "new" to create one.
        </div>

        <div class="flex flex-shrink-0 items-center gap-4 border-t bg-white px-3 py-2 text-xs text-gray-400 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-500">
          <span class="flex items-center gap-1.5">
            <span class="flex items-center gap-0.5">
              <kbd class="flex h-5 w-5 items-center justify-center rounded border border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
                <FeatherIcon name="arrow-up" class="h-3 w-3" />
              </kbd>
              <kbd class="flex h-5 w-5 items-center justify-center rounded border border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
                <FeatherIcon name="arrow-down" class="h-3 w-3" />
              </kbd>
            </span>
            Navigate
          </span>
          <span class="flex items-center gap-1.5">
            <kbd class="flex h-5 items-center rounded border border-gray-300 bg-gray-50 px-1.5 font-sans dark:border-gray-700 dark:bg-gray-800">Enter</kbd>
            Select
          </span>
          <span class="flex items-center gap-1.5">
            <kbd class="flex h-5 items-center rounded border border-gray-300 bg-gray-50 px-1.5 font-sans dark:border-gray-700 dark:bg-gray-800">Esc</kbd>
            Close
          </span>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { Dialog, FeatherIcon, Tooltip } from 'frappe-ui'
import { searchQuery, searchResource } from '@/data/search'
import { flatModuleItems } from '@/data/modules'

const router = useRouter()
const inputRef = ref(null)
const open = ref(false)
const query = searchQuery

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
const shortcutLabel = isMac ? '⌘K' : 'Ctrl+K'

// The global Cmd/Ctrl+K shortcut opens the dialog directly, same shortcut
// as before when it just focused the always-mounted input - autofocus
// inside Dialog now does what that focus() call used to.
function onGlobalKeydown(e) {
  if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    open.value = true
  }
}
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onGlobalKeydown)
}

watch(open, (isOpen) => {
  if (isOpen) {
    nextTick(() => inputRef.value?.focus())
  } else {
    query.value = ''
  }
})

const NEW_PREFIX = /^new\s+/i

const moduleMatches = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q || NEW_PREFIX.test(query.value.trim())) return []
  return flatModuleItems.value
    .filter((item) => (item.label || item.doctype_name).toLowerCase().includes(q))
    .slice(0, 5)
})

const createMatches = computed(() => {
  const raw = query.value.trim()
  const q = NEW_PREFIX.test(raw) ? raw.replace(NEW_PREFIX, '').trim().toLowerCase() : raw.toLowerCase()
  if (!q) return []
  return flatModuleItems.value
    .filter((item) => (item.label || item.doctype_name).toLowerCase().includes(q))
    .slice(0, 5)
})

const searchRecords = computed(() => searchResource.data || [])

const runSearch = useDebounceFn(() => {
  const raw = query.value.trim()
  if (raw && !NEW_PREFIX.test(raw)) {
    searchResource.fetch()
  }
}, 300)

watch(query, runSearch)

function flatKey(prefix, item) {
  return `${prefix}-${item.route}`
}

// One ordered list across all three result groups (same top-to-bottom
// order they render in) so Up/Down/Enter can move through the whole
// popup as a single list, matching how a command palette is expected to
// behave - not per-group navigation.
const flatResults = computed(() => [
  ...moduleMatches.value.map((item) => ({ key: flatKey('mod', item), run: () => goToList(item) })),
  ...createMatches.value.map((item) => ({ key: flatKey('new', item), run: () => goToNew(item) })),
  ...searchRecords.value.map((item, idx) => ({ key: `rec-${idx}`, run: () => selectRecord(item) })),
])

const highlightKey = ref(null)

// Keep the highlight valid as results change while typing - default to
// the first row whenever the current highlight no longer exists in the
// new result set (including right after the very first keystroke, when
// nothing has been highlighted yet).
watch(flatResults, (results) => {
  if (!results.some((r) => r.key === highlightKey.value)) {
    highlightKey.value = results[0]?.key ?? null
  }
})

function rowClass(key, isColumn = false) {
  const base = isColumn
    ? 'flex w-full flex-col items-start px-3 py-1.5 text-left'
    : 'flex w-full items-center gap-2 px-3 py-1.5 text-left'
  return [
    base,
    highlightKey.value === key
      ? 'bg-gray-100 dark:bg-gray-800'
      : 'hover:bg-gray-50 dark:hover:bg-gray-800',
  ]
}

function moveHighlight(delta) {
  const results = flatResults.value
  if (!results.length) return
  const currentIndex = results.findIndex((r) => r.key === highlightKey.value)
  const nextIndex = (currentIndex + delta + results.length) % results.length
  highlightKey.value = results[nextIndex].key
}

function selectHighlighted() {
  const results = flatResults.value
  const current = results.find((r) => r.key === highlightKey.value)
  ;(current || results[0])?.run()
}

function reset() {
  open.value = false
  query.value = ''
}

function goToList(item) {
  reset()
  router.push({ name: 'DoctypeList', params: { doctypeRoute: item.route } })
}

function goToNew(item) {
  reset()
  router.push({ name: 'DoctypeNew', params: { doctypeRoute: item.route } })
}

function selectRecord(item) {
  reset()
  router.push({ name: 'DoctypeForm', params: { doctypeRoute: item.route, name: item.name } })
}
</script>
