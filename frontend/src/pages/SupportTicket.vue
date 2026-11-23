<template>
  <AppLayout>
    <Skeleton v-if="loading && !ticket" height="14rem" />
    <ErrorMessage v-else-if="error && !ticket" :message="error" />

    <!-- The Frappe Helpdesk layout: a slim header, the conversation on the left with its composer pinned underneath,
    and the ticket's fields in a panel on the right. On a computer the two panes fill the screen and scroll on their own. -->
    <div v-else-if="ticket" class="-mx-4 -mt-4 -mb-[calc(5rem-var(--mobile-nav-h,56px))] flex flex-col sm:-mx-6 sm:-my-4 lg:h-[calc(100vh-3.25rem)]">
      <!-- Header -->
      <header class="flex min-h-[2.75rem] flex-shrink-0 flex-wrap items-center justify-between gap-x-2 gap-y-2.5 border-b bg-surface-white px-4 py-2.5 dark:border-gray-800 sm:px-5 md:py-1.5">
        <!-- the trail (Home / Support / ticket) is in the navbar; the header carries the subject -->
        <h1 class="hidden min-w-0 flex-1 truncate text-base font-medium text-ink-gray-9 md:block">{{ ticket.subject }}</h1>
        <!-- phone: the ID sits on the status line; the title and its chips follow below -->
        <span class="rounded-md bg-surface-gray-2 px-2 py-1 font-mono text-xs text-ink-gray-6 md:hidden">{{ ticket.name }}</span>
        <h1 class="order-last basis-full break-words text-xl font-semibold leading-snug text-ink-gray-9 md:hidden">{{ ticket.subject }}</h1>
        <div class="order-last flex basis-full flex-wrap items-center gap-2 pb-2 md:hidden">
          <span class="inline-flex items-center gap-1.5 rounded-md bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-8"><PriorityBars :priority="ticket.priority" class="!h-3.5 !w-3.5" />{{ t(ticket.priority) }}</span>
          <span class="rounded-md bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-7">{{ t(ticket.ticket_type) }}</span>
          <span class="inline-flex items-center gap-1.5 rounded-md bg-surface-gray-2 py-1 pl-1 pr-2 text-xs text-ink-gray-7">
            <span v-if="ticket.assigned_to" class="flex h-4 w-4 items-center justify-center rounded-full text-[8px] font-semibold" :class="avatarClass(ticket.assigned_to)">{{ initials(ticket.assigned_name || ticket.assigned_to) }}</span>
            <FeatherIcon v-else name="user" class="ml-1 h-3.5 w-3.5 text-ink-gray-4" />
            {{ ticket.assigned_name || t('Unassigned') }}
          </span>
        </div>
        <div class="ml-auto flex flex-shrink-0 items-center gap-2 md:ml-0">
          <Button v-if="ticket.can_work && ticket.assigned_to !== options?.user && !isClosed" variant="ghost" @click="change({ assigned_to: options.user })">
            <template #prefix><FeatherIcon name="user-plus" class="h-4 w-4" /></template>
            <span class="hidden sm:inline">{{ t('Assign to me') }}</span><span class="sr-only sm:hidden">{{ t('Assign to me') }}</span>
          </Button>
          <!-- The team picks any status; the requester can close or reopen -->
          <Dropdown v-if="ticket.can_work" :options="statusMenu" placement="right">
            <Button>
              <template #prefix><span class="h-2 w-2 rounded-full" :class="STATUS_DOT[ticket.status]" /></template>
              {{ t(ticket.status) }}
              <template #suffix><FeatherIcon name="chevron-down" class="h-4 w-4" /></template>
            </Button>
          </Dropdown>
          <span v-else class="inline-flex h-7 items-center gap-2 rounded bg-surface-gray-2 px-2.5 text-base text-ink-gray-8"><span class="h-2 w-2 rounded-full" :class="STATUS_DOT[ticket.status]" />{{ t(ticket.status) }}</span>
          <Button v-if="!ticket.can_work && !isClosed" @click="setStatus('Closed')">{{ t('Close ticket') }}</Button>
          <Button v-else-if="isClosed" variant="subtle" @click="setStatus('Open')">{{ t('Reopen') }}</Button>
        </div>
      </header>

      <div class="flex min-h-0 flex-1 flex-col lg:flex-row">
        <!-- Conversation -->
        <section class="flex min-h-0 min-w-0 flex-1 flex-col">
          <div class="sticky -top-4 z-10 flex flex-shrink-0 items-center border-b bg-surface-white px-2 dark:border-gray-800 sm:px-4 lg:static" role="tablist">
            <button type="button" role="tab" :aria-selected="!showDetails" class="-mb-px flex flex-1 items-center justify-center gap-1.5 border-b-2 px-3 py-3 text-base transition-colors lg:flex-none lg:py-2.5" :class="!showDetails ? 'border-ink-gray-9 font-medium text-ink-gray-9' : 'border-transparent text-ink-gray-5'" @click="showDetails && toggleDetails()">
              <FeatherIcon name="activity" class="h-4 w-4" />{{ t('Activity') }}
            </button>
            <!-- on a phone the ticket's fields have no panel beside the conversation: they are a tab -->
            <button type="button" role="tab" :aria-selected="showDetails" class="-mb-px flex flex-1 items-center justify-center gap-1.5 border-b-2 px-3 py-3 text-base transition-colors lg:hidden" :class="showDetails ? 'border-ink-gray-9 font-medium text-ink-gray-9' : 'border-transparent text-ink-gray-5'" @click="!showDetails && toggleDetails()">
              <FeatherIcon name="info" class="h-4 w-4" />{{ t('Details') }}
            </button>
          </div>

          <div ref="scroller" class="min-h-[16rem] flex-1 overflow-y-auto scroll-smooth px-4 py-6 sm:px-6" :class="showDetails ? 'max-lg:hidden' : ''" role="log" :aria-label="t('Activity')">
            <!-- A timeline: a vertical line with each person's avatar and each change on it -->
            <ol class="timeline relative space-y-5">
              <template v-for="entry in timeline" :key="entry.key">
                <!-- The request, and every reply: a card with a header (who, what, when) and the message -->
                <li v-if="entry.kind !== 'log'" class="relative pl-10 sm:pl-12">
                  <span class="absolute left-0 top-0 flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-semibold ring-4 ring-white dark:ring-gray-900 sm:h-8 sm:w-8 sm:text-[11px]" :class="avatarClass(entry.user)">{{ initials(entry.name) }}</span>
                  <article class="overflow-hidden rounded-lg border bg-surface-white shadow-sm dark:border-gray-800">
                    <header class="flex items-start justify-between gap-3 border-b px-3 py-2 dark:border-gray-800 sm:px-4" :class="entry.team ? 'bg-blue-50/70 dark:bg-blue-500/10' : 'bg-surface-gray-1'">
                      <div class="min-w-0">
                        <p class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                          <span class="text-base font-medium text-ink-gray-9">{{ entry.name }}</span>
                          <span v-if="entry.mine" class="text-xs text-ink-gray-5">({{ t('you') }})</span>
                          <span v-if="entry.team" class="rounded-full bg-blue-100 px-2 py-px text-[11px] font-medium text-blue-700 dark:bg-blue-500/20 dark:text-blue-300">{{ t('Team') }}</span>
                          <span class="hidden text-sm text-ink-gray-5 sm:inline">{{ entry.kind === 'request' ? t('opened this ticket') : t('replied') }}</span>
                        </p>
                        <!-- on a phone the action sits on its own line under the name -->
                        <p class="text-xs text-ink-gray-5 sm:hidden">{{ entry.kind === 'request' ? t('opened this ticket') : t('replied') }}</p>
                      </div>
                      <time class="flex-shrink-0 whitespace-nowrap pt-0.5 text-xs text-ink-gray-5" :title="when(entry.creation)">{{ timeAgo(entry.creation) }}</time>
                    </header>
                    <p v-if="entry.cc?.length || (entry.to?.length && !(entry.to.length === 1 && entry.to[0].user === ticket.raised_by))" class="flex flex-wrap gap-x-3 border-b bg-surface-gray-1/50 px-3 py-1.5 text-xs text-ink-gray-5 dark:border-gray-800 sm:px-4">
                      <span v-if="entry.to?.length"><span class="text-ink-gray-4">{{ t('To') }}</span> {{ entry.to.map((x) => x.name).join(', ') }}</span>
                      <span v-if="entry.cc?.length"><span class="text-ink-gray-4">{{ t('Cc') }}</span> {{ entry.cc.map((x) => x.name).join(', ') }}</span>
                    </p>
                    <div class="px-3 py-3 sm:px-4 sm:py-3.5">
                      <div class="prose prose-sm max-w-full break-words text-ink-gray-8" v-html="entry.html" />
                      <div v-if="entry.kind === 'request' && (ticket.reference_doctype || ticket.attachment)" class="mt-3 flex flex-wrap gap-2 border-t pt-3 dark:border-gray-800">
                        <span v-if="ticket.reference_doctype" class="inline-flex items-center gap-1.5 rounded-md bg-surface-gray-2 px-2.5 py-1 text-sm text-ink-gray-7"><FeatherIcon name="file-text" class="h-3.5 w-3.5" />{{ ticket.reference_doctype }}<span v-if="ticket.reference_record" class="font-mono text-xs">· {{ ticket.reference_record }}</span></span>
                        <a v-if="ticket.attachment" :href="ticket.attachment" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 rounded-md bg-surface-gray-2 px-2.5 py-1 text-sm text-ink-gray-7 hover:bg-surface-gray-3"><FeatherIcon name="paperclip" class="h-3.5 w-3.5" />{{ fileName(ticket.attachment) }}</a>
                      </div>
                    </div>
                  </article>
                </li>

                <!-- A change to the ticket: a small icon on the line and one quiet sentence -->
                <li v-else class="relative flex min-h-[1.5rem] items-start gap-2 pl-10 text-sm text-ink-gray-5 sm:items-center sm:pl-12">
                  <span class="absolute left-0.5 top-0 flex h-6 w-6 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6 ring-4 ring-white dark:ring-gray-900 sm:left-1"><FeatherIcon :name="LOG_ICON[entry.field] || 'edit-2'" class="h-3 w-3" /></span>
                  <div class="min-w-0 flex-1 pt-0.5 sm:flex sm:flex-wrap sm:items-center sm:gap-x-1.5 sm:pt-0">
                    <span class="block sm:inline"><span class="font-medium text-ink-gray-7">{{ entry.by }}</span> {{ entry.field === 'Assignee' ? (entry.new ? t('assigned this to') : t('unassigned this')) : `${t('changed')} ${t(entry.field).toLowerCase()}` }}</span>
                    <span class="mt-1 flex flex-wrap items-center gap-1 sm:mt-0 sm:inline-flex">
                      <template v-if="entry.field !== 'Assignee' && entry.old"><span class="rounded-full bg-surface-gray-2 px-2 py-px text-xs text-ink-gray-7">{{ t(entry.old) }}</span><FeatherIcon name="arrow-right" class="h-3 w-3 flex-shrink-0 text-ink-gray-4" /></template>
                      <span v-if="entry.new" class="rounded-full bg-surface-gray-2 px-2 py-px text-xs font-medium text-ink-gray-8">{{ t(entry.new) }}</span>
                    </span>
                  </div>
                  <time class="flex-shrink-0 whitespace-nowrap pt-0.5 text-xs text-ink-gray-4 sm:pt-0" :title="when(entry.creation)">{{ timeAgo(entry.creation) }}</time>
                </li>
              </template>

              <li v-if="timeline.length === 1" class="relative pl-10 sm:pl-12">
                <p class="rounded-lg border border-dashed px-4 py-4 text-center text-sm text-ink-gray-5 dark:border-gray-800">{{ ticket.can_work ? t('Nobody has replied yet. Be the first.') : t('The team has not replied yet. You will be notified when they do.') }}</p>
              </li>
            </ol>
          </div>

          <!-- Composer: Reply opens an editor under the feed -->
          <div v-if="!isClosed" class="sticky z-10 flex-shrink-0 border-t bg-surface-white dark:border-gray-800 max-sm:bottom-[calc(var(--mobile-nav-h,56px)-5rem)] sm:-bottom-4 lg:static" :class="showDetails ? 'max-lg:hidden' : ''">
            <div class="flex items-center gap-1.5 px-3 py-2 sm:px-5 sm:py-2.5">
              <Button variant="ghost" :class="composing ? '!bg-surface-gray-4' : ''" @click="toggleComposer">
                <template #prefix><FeatherIcon name="mail" class="h-4 w-4" /></template>
                {{ t('Reply') }}
              </Button>
            </div>
            <div v-if="composing" class="px-3 pb-3 sm:px-5 sm:pb-3.5">
              <TicketEditor
                ref="composer"
                v-model="message"
                v-model:to="toUsers"
                v-model:cc="ccUsers"
                :editable="ticket.can_work"
                :options="ticket.recipients || []"
                :fixed-to="t('The help desk team')"
                :placeholder="t('Hi, we are looking into this.')"
                :sending="sending"
                :attachments="files"
                @send="send"
                @discard="discard"
                @close="composing = false"
                @add-file="addFile"
                @remove-file="(f) => (files = files.filter((x) => x.url !== f.url))"
              />
              <ErrorMessage v-if="error" class="mt-2" :message="error" />
            </div>
          </div>
          <p v-else class="flex-shrink-0 border-t bg-surface-gray-1 px-5 py-3 text-center text-base text-ink-gray-5 dark:border-gray-800" :class="showDetails ? 'max-lg:hidden' : ''">{{ t('This ticket is closed. Reopen it to reply.') }}</p>
        </section>

        <!-- Right panel -->
        <aside :class="showDetails ? '' : 'max-lg:hidden'" class="flex-shrink-0 overflow-y-auto overflow-x-hidden border-t bg-surface-white dark:border-gray-800 lg:w-[22rem] lg:border-l lg:border-t-0">
          <div class="space-y-4 p-4">
            <!-- The requester, as Helpdesk's contact card -->
            <div class="flex items-center gap-3">
              <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-semibold" :class="avatarClass(ticket.raised_by)">{{ initials(ticket.raised_by_name || ticket.raised_by) }}</span>
              <div class="min-w-0">
                <p class="truncate text-base font-medium text-ink-gray-9">{{ ticket.raised_by_name || ticket.raised_by }}</p>
                <a v-if="ticket.requester_email" :href="`mailto:${ticket.requester_email}`" class="block truncate text-sm text-ink-gray-5 hover:text-ink-gray-8">{{ ticket.requester_email }}</a>
              </div>
            </div>

            <!-- Service level -->
            <div class="rounded-lg border p-3 dark:border-gray-800">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm text-ink-gray-5">{{ isClosed ? t('Resolved') : t('Resolution by') }}</p>
                <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" :class="slaChip.class">{{ slaChip.label }}</span>
              </div>
              <p class="mt-1 text-base text-ink-gray-9">{{ slaWhen }}</p>
              <p v-if="ticket.first_response_on" class="mt-1.5 text-sm text-ink-gray-5">{{ t('First response') }}: {{ when(ticket.first_response_on) }}</p>
            </div>
          </div>

          <div class="divide-y border-t dark:divide-gray-800 dark:border-gray-800">
            <Section :label="t('Overview')">
              <div class="space-y-2.5 pb-3 pt-0.5">
                <Field :label="t('Assignee')">
                  <select v-if="ticket.can_work" class="ghost-select" :value="ticket.assigned_to || ''" @change="change({ assigned_to: $event.target.value })">
                    <option v-for="o in agentOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                  </select>
                  <span v-else class="px-2 text-base text-ink-gray-8">{{ ticket.assigned_name || t('Not yet assigned') }}</span>
                </Field>
                <Field :label="t('Priority')">
                  <select v-if="ticket.can_work" class="ghost-select" :value="ticket.priority" @change="change({ priority: $event.target.value })">
                    <option v-for="o in priorityOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                  </select>
                  <span v-else class="inline-flex items-center gap-2 px-2 text-base" :class="PRIORITY_STYLE[ticket.priority]"><span class="h-2 w-2 rounded-sm" :class="PRIORITY_DOT[ticket.priority]" />{{ t(ticket.priority) }}</span>
                </Field>
                <Field :label="t('Type')"><span class="px-2 text-base text-ink-gray-8">{{ t(ticket.ticket_type) }}</span></Field>
                <Field v-if="ticket.city" :label="t('City')"><span class="px-2 text-base text-ink-gray-8">{{ ticket.city }}</span></Field>
                <Field :label="t('Raised')"><span class="px-2 text-base text-ink-gray-8">{{ when(ticket.creation) }}</span></Field>
              </div>
            </Section>

            <Section v-if="ticket.reference_doctype" :label="t('About')">
              <div class="space-y-2.5 pb-3 pt-0.5">
                <Field :label="t('Form')"><span class="px-2 text-base text-ink-gray-8">{{ ticket.reference_doctype }}</span></Field>
                <Field v-if="ticket.reference_record" :label="t('Record')"><span class="px-2 font-mono text-sm text-ink-gray-8">{{ ticket.reference_record }}</span></Field>
              </div>
            </Section>

            <Section v-if="ticket.can_work || ticket.resolution" :label="t('Resolution')">
              <div class="pb-3 pt-0.5">
                <template v-if="ticket.can_work">
                  <textarea v-model="resolution" rows="3" class="w-full resize-y rounded-md border-0 bg-surface-gray-2 px-2.5 py-2 text-base text-ink-gray-9 placeholder-ink-gray-4 focus:bg-surface-white focus:outline-none focus:ring-2 focus:ring-outline-gray-3" :placeholder="t('What was done')" />
                  <Button v-if="resolution !== (ticket.resolution || '')" class="mt-2 w-full" variant="subtle" @click="change({ resolution })">{{ t('Save resolution') }}</Button>
                </template>
                <p v-else class="whitespace-pre-line text-base text-ink-gray-8">{{ ticket.resolution }}</p>
              </div>
            </Section>
          </div>
        </aside>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, defineComponent, h, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, Dropdown, ErrorMessage, FeatherIcon, toast } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import Skeleton from '@/components/Skeleton.vue'
import TicketEditor from '@/components/support/TicketEditor.vue'
import PriorityBars from '@/components/support/PriorityBars.vue'
import {
  addReply, getTicket, loadSupportOptions, supportOptions, updateTicket,
  STATUS_DOT, PRIORITY_DOT, PRIORITY_STYLE, initials, avatarClass, timeAgo,
} from '@/data/support'
import { setPageTitle } from '@/data/pageTitle'
import { t } from '@/utils/translate'

// A label and its value on one row (Helpdesk's side-panel field)
const Field = defineComponent({
  props: { label: String },
  setup: (props, { slots }) => () =>
    h('div', { class: 'flex items-center gap-2 leading-5' }, [
      h('div', { class: 'w-[6.5rem] flex-shrink-0 truncate text-base text-ink-gray-5' }, props.label),
      h('div', { class: 'min-w-0 flex-1' }, slots.default?.()),
    ]),
})
// A collapsible section of the side panel
const Section = defineComponent({
  props: { label: String },
  setup(props, { slots }) {
    const opened = ref(true)
    return () =>
      h('div', { class: 'px-4' }, [
        h('button', { type: 'button', class: 'flex w-full items-center gap-1 py-3.5 text-left', onClick: () => (opened.value = !opened.value), 'aria-expanded': opened.value }, [
          h('span', { class: 'text-base font-medium text-ink-gray-8' }, props.label),
          h(FeatherIcon, { name: 'chevron-right', class: `h-3.5 w-3.5 text-ink-gray-5 transition-transform ${opened.value ? 'rotate-90' : ''}` }),
        ]),
        opened.value ? slots.default?.() : null,
      ])
  },
})

const route = useRoute()
const router = useRouter()
const name = computed(() => route.params.name)
const options = supportOptions
const ticket = ref(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
// On a phone the editor starts closed, so the conversation has the screen.
const composing = ref(typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches)
const showDetails = ref(false)
const toUsers = ref([])
const ccUsers = ref([])
let recipientsFor = null
const sending = ref(false)
const resolution = ref('')
const scroller = ref(null)
const composer = ref(null)
const files = ref([])

const isClosed = computed(() => ['Resolved', 'Closed'].includes(ticket.value?.status))
const back = () => router.push({ name: 'SupportDesk', query: ticket.value?.can_work ? { view: 'queue' } : {} })

const when = (v) => new Date(String(v).replace(' ', 'T')).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
const fileName = (url) => decodeURIComponent(String(url).split('/').pop() || t('Attachment'))

// The conversation in time order: the request, the team's and the requester's replies, and the ticket's changes
const messages = computed(() => {
  const x = ticket.value
  if (!x) return []
  return x.replies
    .filter((r) => !r.is_internal)
    .map((r) => ({ key: r.name, kind: 'msg', name: r.author_name, user: r.author, html: r.html, creation: r.creation, team: r.from_team, to: r.to, cc: r.cc, mine: r.author === options.value?.user }))
})
const logs = computed(() => (ticket.value?.activity || []).map((a, i) => ({ ...a, key: `log-${i}`, kind: 'log' })))
const LOG_ICON = { Status: 'refresh-cw', Priority: 'flag', Assignee: 'user-check', Type: 'tag' }
// The request first, then the replies and the ticket's changes in time order
const timeline = computed(() => {
  const x = ticket.value
  if (!x) return []
  const request = { key: 'request', kind: 'request', name: x.raised_by_name || x.raised_by, user: x.raised_by, html: x.description_html, creation: x.creation, team: false, mine: x.raised_by === options.value?.user }
  const items = [...messages.value, ...logs.value].sort((a, b) => String(a.creation).localeCompare(String(b.creation)))
  return [request, ...items]
})

const slaChip = computed(() => {
  const x = ticket.value
  if (['Resolved', 'Closed'].includes(x.status)) {
    const late = x.sla_due && x.resolved_on && String(x.resolved_on) > String(x.sla_due)
    return late ? { label: t('Late'), class: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300' } : { label: t('Fulfilled'), class: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' }
  }
  return x.overdue ? { label: t('Overdue'), class: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300' } : { label: t('On track'), class: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300' }
})
const slaWhen = computed(() => {
  const x = ticket.value
  if (x.resolved_on) return when(x.resolved_on)
  return x.sla_due ? when(x.sla_due) : '-'
})

const statusMenu = computed(() => (options.value?.statuses || []).map((s) => ({ label: t(s), onClick: () => setStatus(s) })))
const priorityOptions = computed(() => (options.value?.priorities || []).map((s) => ({ label: t(s), value: s })))
const agentOptions = computed(() => [{ label: t('Unassigned'), value: '' }, ...(options.value?.agents || []).map((a) => ({ label: a.name, value: a.user }))])

const clean = (e) => String(e?.messages?.[0] || e?.message || t('Something went wrong.')).replace(/<[^>]+>/g, '')
const toBottom = () =>
  nextTick(() => {
    if (window.matchMedia('(min-width: 1024px)').matches) {
      if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
    } else {
      // below lg the page scrolls, not the feed
      const page = scroller.value?.closest('main')
      page?.scrollTo({ top: page.scrollHeight })
    }
  })
function show(data) {
  ticket.value = data
  // the To line starts with the requester; changes made while writing are kept until the reply is sent
  if (recipientsFor !== data.name) {
    recipientsFor = data.name
    toUsers.value = [data.raised_by]
    ccUsers.value = []
  }
  resolution.value = data.resolution || ''
  setPageTitle(data.name)
}
async function load(quiet = false) {
  if (!quiet) loading.value = true
  try {
    show(await getTicket(name.value))
    error.value = ''
  } catch (e) {
    if (!quiet || !ticket.value) error.value = clean(e)
  }
  loading.value = false
}
function toggleDetails() {
  showDetails.value = !showDetails.value
  nextTick(() => (showDetails.value ? scroller.value?.closest('main')?.scrollTo({ top: 0 }) : toBottom()))
}
function toggleComposer() {
  composing.value = !composing.value
  if (composing.value) nextTick(() => composer.value?.focus())
}
function discard() {
  message.value = ''
  files.value = []
  toUsers.value = [ticket.value.raised_by]
  ccUsers.value = []
  composing.value = false
}
function addFile(file) {
  if (file.error) toast.error(file.error)
  else files.value = [...files.value, file]
}
const esc = (v) => String(v).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])
async function send() {
  const text = message.value.replace(/<[^>]*>/g, '').trim()
  if ((!text && !files.value.length && !/<img/.test(message.value)) || sending.value) return
  sending.value = true
  error.value = ''
  try {
    // attached files go into the message as links under the text
    const links = files.value.map((f) => `<li><a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.name)}</a></li>`).join('')
    await addReply(name.value, message.value + (links ? `<p>${esc(t('Attachments'))}:</p><ul>${links}</ul>` : ''), 0, ticket.value.can_work ? toUsers.value : null, ticket.value.can_work ? ccUsers.value : null)
    message.value = ''
    files.value = []
    ccUsers.value = []
    toUsers.value = [ticket.value.raised_by]
    await load(true)
    toBottom()
  } catch (e) {
    error.value = clean(e)
  } finally {
    sending.value = false
  }
}
async function change(args) {
  try {
    show(await updateTicket({ name: name.value, ...args }))
    toast.success(t('Saved'))
  } catch (e) {
    toast.error(clean(e))
    load(true)
  }
}
const setStatus = (status) => (status && status !== ticket.value?.status ? change({ status }) : null)
// New replies from the other side show up without a reload.
let poll = null
onMounted(async () => {
  await loadSupportOptions()
  await load()
  toBottom()
  poll = setInterval(() => document.visibilityState === 'visible' && !message.value && load(true), 20000)
})
onBeforeUnmount(() => clearInterval(poll))
watch(name, async () => {
  await load()
  toBottom()
})
</script>

<style scoped>
/* The vertical line of the timeline runs behind the avatars (the avatars carry a white ring to cut it) */
.timeline::before {
  content: '';
  position: absolute;
  left: 0.875rem;
  top: 1rem;
  bottom: 1rem;
  width: 1px;
  background: var(--outline-gray-2, #e5e7eb);
}
@media (min-width: 640px) {
  .timeline::before {
    left: 1rem;
  }
}

/* A select that looks like plain text until hovered (Helpdesk's side-panel fields) */
.ghost-select {
  width: 100%;
  cursor: pointer;
  border-radius: 0.375rem;
  border: 0;
  background-color: transparent;
  padding: 0.25rem 1.75rem 0.25rem 0.5rem;
  font-size: 0.875rem;
  color: var(--ink-gray-8, #374151);
}
.ghost-select:hover,
.ghost-select:focus {
  background-color: var(--surface-gray-2, #f3f4f6);
  outline: none;
}
</style>
