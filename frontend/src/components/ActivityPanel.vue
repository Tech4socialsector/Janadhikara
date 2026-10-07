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
        <!-- Connector line to the next entry; the last entry has nothing below it, so no line. -->
        <span v-if="i !== visibleItems.length - 1" class="absolute start-[11px] top-7 -bottom-1 w-px bg-outline-gray-2" />
        <span class="relative z-10 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-outline-gray-2 bg-surface-gray-1 text-ink-gray-6">
          <FeatherIcon :name="iconFor(item)" class="h-3 w-3" />
        </span>

        <div class="min-w-0 flex-1">
          <div class="flex items-baseline justify-between gap-4">
            <p class="min-w-0 text-sm leading-6 text-ink-gray-6 pt-px">
              <!-- Backend log lines already name the actor ("You created…"), so only name it elsewhere. -->
              <!-- Actor name: shown for field changes ("Administrator changed Status"), attachments
              ("Administrator attached x.pdf"), comments and emails. Hidden when the backend text
              already names the actor ("You created this document", "Ravi assigned this to you"). -->
              <span v-if="!item.text || item.file || item.changes" class="font-medium text-ink-gray-9">{{ item.author }}{{ ' ' }}</span>
              <!-- Several field changes saved in one go: "Administrator made 3 changes  details". -->
              <template v-if="item.changes && item.changes.length > 1">
                made {{ item.changes.length }} changes
                <button type="button" class="ms-1 text-xs text-ink-gray-5 underline-offset-2 hover:text-ink-gray-8 hover:underline" @click="toggle(item.key)">
                  {{ open.has(item.key) ? 'hide' : 'details' }}
                </button>
              </template>
              <!-- One field change, shown inline: "Administrator changed Has Intervention Units 0 → 1". -->
              <template v-else-if="item.changes">
                {{ item.changes[0].prefix }}
                <!-- Old value only when there was one: "changed Status Open → Closed",
                but "set Pincode to 562125" has no old value, so no strikethrough or arrow. -->
                <span v-if="isBlob(item.changes[0].from) || isBlob(item.changes[0].to)" class="text-ink-gray-5">(map / structured data)</span>
                <template v-else-if="item.changes[0].from != null">
                  <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-ink-gray-5 line-through" :title="item.changes[0].from">{{ clip(item.changes[0].from) }}</span>
                  →
                </template>
                <!-- New value; absent for "cleared" or "updated" entries, e.g. "updated Remarks". -->
                <span v-if="item.changes[0].to != null && !isBlob(item.changes[0].from) && !isBlob(item.changes[0].to)" class="rounded bg-surface-gray-2 px-1.5 py-0.5 font-medium text-ink-gray-9" :title="item.changes[0].to">{{ clip(item.changes[0].to) }}</span>
              </template>
              <!-- Attachment: "Administrator attached photo.jpg" / "removed attachment photo.jpg". -->
              <template v-else-if="item.file">
                {{ item.text }}
                <!-- A link when the file still exists; plain text when it was removed. -->
                <a v-if="item.href" :href="item.href" target="_blank" class="font-medium text-ink-gray-9 hover:underline">{{ item.file }}</a>
                <span v-else class="font-medium text-ink-gray-9">{{ item.file }}</span>
              </template>
              <!-- Comment or email: the text itself goes in the grey box below, e.g.
              "Priya commented" + box "Visited again, family has moved". -->
              <template v-else-if="item.card">{{ item.icon === 'mail' ? 'sent an email' : 'commented' }}</template>
              <!-- Anything else, using the backend's own sentence: "You created this document". -->
              <template v-else>{{ item.text }}</template>
            </p>
            <time class="flex-shrink-0 text-xs text-ink-gray-5" :title="fullDatetime(item.timestamp)">{{ ago(item.timestamp) }}</time>
          </div>

          <!-- The list behind "details" for a multi-change entry, e.g. "Set State to Karnataka",
          "Set District to Bengaluru Urban". Closed until clicked. -->
          <ul v-if="item.changes && item.changes.length > 1 && open.has(item.key)" class="mt-2 space-y-1.5 rounded-lg bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-6">
            <li v-for="c in item.changes" :key="c.key">
              <span class="cap-first">{{ c.prefix }}</span>
              <!-- Same rule as above: arrow and old value only when a value was replaced. -->
              <span v-if="isBlob(c.from) || isBlob(c.to)" class="text-ink-gray-5">(map / structured data)</span>
              <template v-else>
                <template v-if="c.from != null">
                  <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-ink-gray-5 line-through" :title="c.from">{{ clip(c.from) }}</span>
                  →
                </template>
                <span v-if="c.to != null" class="rounded bg-surface-gray-2 px-1.5 py-0.5 font-medium text-ink-gray-9" :title="c.to">{{ clip(c.to) }}</span>
              </template>
            </li>
          </ul>

          <!-- Body of a comment or email; the subject line only exists for emails. -->
          <div v-if="item.card" class="mt-1.5 rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-8">
            <!-- e.g. "Re: Household visit" -->
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
