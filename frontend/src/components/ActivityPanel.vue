<template>
  <!-- Activity for this record, newest first. Data comes from Frappe's get_activity_timeline. -->
  <!-- Hidden when the record has no activity at all (e.g. a record nobody has touched yet). -->
  <section v-if="items.length" class="mt-8 rounded-xl border border-outline-gray-2 bg-surface-white p-4 sm:p-5">
    <div class="mb-4 flex items-center justify-between">
      <h3 class="flex items-center gap-2 text-base font-semibold text-ink-gray-9">
        <FeatherIcon name="activity" class="h-4 w-4 text-ink-gray-5" />
        Activity
        <span class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs font-medium text-ink-gray-6">{{ items.length }}</span>
      </h3>
      <!-- Only with more than 10 entries, e.g. 25 entries -> "Show all 25"; click again -> "Show recent". -->
      <Button v-if="items.length > LIMIT" variant="ghost" size="sm" @click="showAll = !showAll">
        {{ showAll ? 'Show recent' : `Show all ${items.length}` }}
      </Button>
    </div>

    <ol>
      <li v-for="(item, i) in visibleItems" :key="item.key" class="relative flex gap-3 pb-5 last:pb-0">
        <!-- Connector line to the next entry -->
        <span v-if="i !== visibleItems.length - 1" class="absolute start-[15px] top-9 -bottom-1 w-px bg-outline-gray-2" />
        <!-- Avatar (initials) with a small badge showing what kind of entry it is -->
        <span class="relative z-10 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold" :class="avatarClass(item.author)">
          {{ initials(item.author) }}
          <span class="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full border border-outline-gray-2 bg-surface-white text-ink-gray-6">
            <FeatherIcon :name="iconFor(item)" class="h-2.5 w-2.5" />
          </span>
        </span>

        <div class="min-w-0 flex-1">
          <!-- Who, and when -->
          <div class="flex items-baseline justify-between gap-3">
            <p class="min-w-0 truncate text-sm font-medium leading-6 text-ink-gray-9">{{ item.author || t('Someone') }}</p>
            <time class="flex-shrink-0 text-xs text-ink-gray-5" :title="fullDatetime(item.timestamp)">{{ ago(item.timestamp) }}</time>
          </div>

          <!-- What they did -->
          <p class="break-words text-sm leading-5 text-ink-gray-6">
            <template v-if="item.changes && item.changes.length > 1">
              made {{ item.changes.length }} changes
              <button type="button" class="ms-1 rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs font-medium text-ink-gray-7 hover:bg-surface-gray-3" @click="toggle(item.key)">
                {{ open.has(item.key) ? 'Hide' : 'Details' }}
              </button>
            </template>
            <template v-else-if="item.changes">{{ item.changes[0].prefix }}</template>
            <template v-else-if="item.file">
              {{ item.text }}
              <a v-if="item.href" :href="item.href" target="_blank" class="font-medium text-ink-gray-9 hover:underline">{{ item.file }}</a>
              <span v-else class="font-medium text-ink-gray-9">{{ item.file }}</span>
            </template>
            <template v-else-if="item.card">{{ item.icon === 'mail' ? 'sent an email' : 'commented' }}</template>
            <template v-else>{{ said(item) }}</template>
          </p>

          <!-- One field change: old value -> new value, wrapping on a narrow screen -->
          <div v-if="item.changes && item.changes.length === 1 && changeShown(item.changes[0])" class="mt-1.5 flex flex-wrap items-center gap-1.5 text-sm">
            <span v-if="isBlob(item.changes[0].from) || isBlob(item.changes[0].to)" class="text-ink-gray-5">(map / structured data)</span>
            <template v-else>
              <span v-if="item.changes[0].from != null" class="max-w-full break-words rounded-md bg-surface-gray-2 px-2 py-0.5 text-ink-gray-5 line-through" :title="item.changes[0].from">{{ clip(item.changes[0].from) }}</span>
              <FeatherIcon v-if="item.changes[0].from != null && item.changes[0].to != null" name="arrow-right" class="h-3.5 w-3.5 flex-shrink-0 text-ink-gray-4" />
              <span v-if="item.changes[0].to != null" class="max-w-full break-words rounded-md bg-surface-gray-2 px-2 py-0.5 font-medium text-ink-gray-9" :title="item.changes[0].to">{{ clip(item.changes[0].to) }}</span>
            </template>
          </div>

          <!-- Several changes: a card, one line per field, opened by Details -->
          <ul v-if="item.changes && item.changes.length > 1 && open.has(item.key)" class="mt-2 divide-y divide-outline-gray-1 overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-gray-1 text-sm">
            <li v-for="c in item.changes" :key="c.key" class="px-3 py-2">
              <p class="cap-first text-xs text-ink-gray-5">{{ c.prefix }}</p>
              <div v-if="!(isBlob(c.from) || isBlob(c.to))" class="mt-1 flex flex-wrap items-center gap-1.5">
                <span v-if="c.from != null" class="max-w-full break-words rounded-md bg-surface-gray-2 px-2 py-0.5 text-ink-gray-5 line-through" :title="c.from">{{ clip(c.from) }}</span>
                <FeatherIcon v-if="c.from != null && c.to != null" name="arrow-right" class="h-3.5 w-3.5 flex-shrink-0 text-ink-gray-4" />
                <span v-if="c.to != null" class="max-w-full break-words rounded-md bg-surface-white px-2 py-0.5 font-medium text-ink-gray-9" :title="c.to">{{ clip(c.to) }}</span>
              </div>
              <p v-else class="mt-1 text-ink-gray-5">(map / structured data)</p>
            </li>
          </ul>

          <!-- Comment or email body -->
          <div v-if="item.card" class="mt-1.5 rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-8">
            <p v-if="item.subject" class="mb-0.5 font-medium">{{ item.subject }}</p>
            <p class="whitespace-pre-wrap break-words">{{ item.body }}</p>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { createResource, Button, FeatherIcon } from 'frappe-ui'
import { fullDatetime, parseServerDatetime } from '@/utils/time'
import { initials, avatarClass } from '@/data/support'
import { t } from '@/utils/translate'

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
})

const LIMIT = 10
const showAll = ref(false)
const open = reactive(new Set())
const toggle = (key) => (open.has(key) ? open.delete(key) : open.add(key))

const timeline = createResource({
  url: 'frappe.desk.form.activity.get_activity_timeline',
  params: { doctype: props.doctype, name: props.name },
  auto: true,
})

const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
function ago(value) {
  const date = parseServerDatetime(value)
  if (!date) return ''
  const seconds = Math.round((date.getTime() - Date.now()) / 1000)
  const steps = [['year', 31536000], ['month', 2592000], ['week', 604800], ['day', 86400], ['hour', 3600], ['minute', 60]]
  for (const [unit, size] of steps) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

// The backend sentence without its actor, which the entry's header already names: "You created this document" -> "created this document"
function said(item) {
  const text = String(item.text || '')
  const name = item.author ? item.author.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') : ''
  return text.replace(new RegExp(`^(You${name ? `|${name}` : ''}) `), '')
}
const changeShown = (c) => c.from != null || c.to != null

// Raw JSON (a map shape, a stored list) isn't readable as text: show a label instead of the value
const isBlob = (v) => typeof v === 'string' && /^\s*[{[]/.test(v)

function iconFor(item) {
  if (item.icon && item.icon !== 'dot') return item.icon
  if (item.changes) return 'edit-3'
  if (/created/i.test(item.text || '')) return 'plus'
  if (/assign/i.test(item.text || '')) return 'user-check'
  return 'circle'
}

function clip(value, limit = 40) {
  const s = value == null ? '' : String(value)
  return s.length > limit ? `${s.slice(0, limit)}…` : s
}

function stripHtml(html) {
  return (new DOMParser().parseFromString(String(html || ''), 'text/html').body.textContent || '').trim()
}

const LOG_ICONS = {
  like: 'heart', workflow: 'git-branch', info: 'info', view: 'eye',
  edited: 'edit-2', shared: 'users', milestone: 'flag',
}

// Backend rows -> display items. Field changes saved together (same Version) fold into one item.
const items = computed(() => {
  const out = []
  for (const a of timeline.data?.activities || []) {
    const d = a.data || {}
    const author = a.author?.fullname || ''
    const base = { key: a.key, timestamp: a.timestamp, author, image: a.author?.image }
    if (a.type === 'version') {
      // Parent doctype only: child-table row changes carry no fieldname, so drop them
      // (submit/cancel also carry none, but are kept).
      if (!d.fieldname && !/^(submitted|cancelled) /.test(d.text || '')) continue
      const change = {
        key: a.key,
        prefix: d.type === 'diff' ? d.prefix : d.text,
        from: d.type === 'diff' ? d.from : null,
        to: d.type === 'diff' ? d.to : null,
      }
      const group = a.key.replace(/^version:/, '').replace(/-\d+$/, '')
      const last = out[out.length - 1]
      if (last?.group === group) last.changes.push(change)
      else out.push({ ...base, icon: 'dot', group, changes: [change] })
    } else if (a.type === 'comment') {
      out.push({ ...base, card: true, icon: 'message-square', image: a.author?.image, body: stripHtml(d.content) })
    } else if (a.type === 'email') {
      out.push({ ...base, card: true, icon: 'mail', image: a.author?.image, subject: d.subject, body: stripHtml(d.content) })
    } else if (a.type === 'attachment_log') {
      out.push({
        ...base, icon: d.action === 'removed' ? 'trash-2' : 'paperclip', lead: author,
        text: d.action === 'removed' ? 'removed attachment' : 'attached', file: d.fileName, href: d.fileUrl,
      })
    } else if (d.text) {
      const dot = ['created', 'assigned', 'assignment_completed'].includes(d.subtype)
      out.push({ ...base, icon: dot ? 'dot' : LOG_ICONS[d.subtype] || 'dot', text: d.text })
    }
  }
  return out.reverse() // newest first
})

const visibleItems = computed(() => (showAll.value ? items.value : items.value.slice(0, LIMIT)))
</script>

<style scoped>
.cap-first::first-letter {
  text-transform: capitalize;
}
</style>
