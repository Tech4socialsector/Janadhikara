<template>
  <!-- A computer: the app's standard list (grey header band, square checkboxes, evenly spaced columns, plain text).
  A phone: one card per ticket. -->
  <div>
    <div class="hidden md:block" role="table" :aria-label="t('Tickets')">
      <div role="row" class="grid items-center gap-x-4 rounded-lg bg-surface-gray-2 px-3 py-2 text-sm text-ink-gray-5" :style="{ gridTemplateColumns: columns }">
        <input v-if="agent" type="checkbox" class="form-checkbox h-4 w-4 cursor-pointer !rounded-[3px] border-gray-300 dark:border-gray-600 dark:bg-gray-800" :checked="allSelected" :indeterminate.prop="someSelected" :aria-label="t('Select all')" @change="toggleAll" />
        <span role="columnheader">{{ t('ID') }}</span>
        <span role="columnheader">{{ t('Subject') }}</span>
        <span role="columnheader">{{ t('Status') }}</span>
        <span role="columnheader">{{ t('Priority') }}</span>
        <span role="columnheader">{{ t('Type') }}</span>
        <span v-if="agent" role="columnheader">{{ t('Requester') }}</span>
        <span role="columnheader">{{ t('Assigned to') }}</span>
        <span role="columnheader">{{ t('Respond by') }}</span>
        <span role="columnheader">{{ t('Last Modified') }}</span>
      </div>

      <div
        v-for="row in rows"
        :key="row.name"
        role="row"
        class="grid cursor-pointer items-center gap-x-4 rounded-md px-3 py-3 text-base text-ink-gray-7 transition-colors hover:bg-surface-gray-1"
        :class="selected.includes(row.name) ? 'bg-surface-gray-1' : ''"
        :style="{ gridTemplateColumns: columns }"
        @click="open(row)"
      >
        <input v-if="agent" type="checkbox" class="form-checkbox h-4 w-4 cursor-pointer !rounded-[3px] border-gray-300 dark:border-gray-600 dark:bg-gray-800" :checked="selected.includes(row.name)" :aria-label="`${t('Select')} ${row.name}`" @click.stop @change="toggle(row.name)" />
        <span class="truncate text-ink-gray-8">{{ row.name }}</span>
        <span class="truncate" :title="row.subject">{{ row.subject }}</span>
        <span class="truncate">{{ t(row.status) }}</span>
        <span class="truncate">{{ t(row.priority) }}</span>
        <span class="truncate">{{ t(row.ticket_type) }}</span>
        <span v-if="agent" class="truncate">{{ row.raised_by_name || row.raised_by }}</span>
        <span class="truncate" :class="row.assigned_to ? '' : 'text-ink-gray-4'">{{ row.assigned_name || '-' }}</span>
        <span class="truncate" :class="row.overdue ? 'font-medium text-red-600 dark:text-red-400' : ''">{{ finished(row) ? '-' : short(row.sla_due) }}</span>
        <span class="truncate">{{ timeAgo(row.modified) }}</span>
      </div>
    </div>

    <div class="space-y-2.5 md:hidden">
      <!-- select all, for the team's Actions menu -->
      <label v-if="agent" class="flex w-fit cursor-pointer items-center gap-2.5 px-1 py-1 text-sm text-ink-gray-7">
        <input type="checkbox" class="form-checkbox h-[1.125rem] w-[1.125rem] cursor-pointer !rounded-[4px] border-gray-300 dark:border-gray-600 dark:bg-gray-800" :checked="allSelected" :indeterminate.prop="someSelected" @change="toggleAll" />
        {{ selected.length ? `${selected.length} ${t('selected')}` : t('Select all') }}
      </label>
      <TicketRow v-for="row in rows" :key="row.name" :ticket="row" :show-requester="agent" :selectable="agent" :selected="selected.includes(row.name)" @toggle="toggle(row.name)" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import TicketRow from '@/components/support/TicketRow.vue'
import { timeAgo } from '@/data/support'
import { t } from '@/utils/translate'

const props = defineProps({
  rows: { type: Array, required: true },
  agent: { type: Boolean, default: false },
  selected: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:selected'])
const router = useRouter()

// Columns share the width evenly, the subject taking the most (the team also has a checkbox and a requester column)
const columns = computed(() =>
  props.agent
    ? '1rem 6.5rem minmax(0,3fr) minmax(0,1.3fr) minmax(0,1fr) minmax(0,1.4fr) minmax(0,1.4fr) minmax(0,1.4fr) minmax(0,1.4fr) minmax(0,1fr)'
    : '6.5rem minmax(0,3fr) minmax(0,1.3fr) minmax(0,1fr) minmax(0,1.4fr) minmax(0,1.4fr) minmax(0,1.4fr) minmax(0,1fr)',
)
const finished = (row) => ['Resolved', 'Closed'].includes(row.status)
const open = (row) => router.push({ name: 'SupportTicket', params: { name: row.name } })
const short = (v) => (v ? new Date(String(v).replace(' ', 'T')).toLocaleString([], { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }) : '-')
const allSelected = computed(() => props.rows.length > 0 && props.rows.every((r) => props.selected.includes(r.name)))
const someSelected = computed(() => props.selected.length > 0 && !allSelected.value)
const toggle = (name) => emit('update:selected', props.selected.includes(name) ? props.selected.filter((n) => n !== name) : [...props.selected, name])
const toggleAll = () => emit('update:selected', allSelected.value ? [] : props.rows.map((r) => r.name))
</script>
