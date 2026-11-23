<template>
  <!-- The phone's ticket card: id, status and time on top; the subject; priority and type; then who it is between -->
  <router-link
    :to="{ name: 'SupportTicket', params: { name: ticket.name } }"
    class="block rounded-xl border bg-surface-white p-3.5 shadow-sm transition active:scale-[0.99] active:bg-surface-gray-1 dark:border-gray-800"
    :class="selected ? 'border-ink-gray-9 bg-surface-gray-1 ring-1 ring-ink-gray-9' : ''"
  >
    <div class="flex items-center gap-2">
      <!-- a tap target to pick this ticket for the Actions menu (the rest of the card opens it) -->
      <label v-if="selectable" class="-m-2.5 -ml-2 flex h-10 w-10 flex-shrink-0 cursor-pointer items-center justify-center" @click.stop>
        <input type="checkbox" class="form-checkbox h-[1.125rem] w-[1.125rem] cursor-pointer !rounded-[4px] border-gray-300 dark:border-gray-600 dark:bg-gray-800" :checked="selected" :aria-label="`${t('Select')} ${ticket.name}`" @click.stop @change="$emit('toggle')" />
      </label>
      <span class="font-mono text-xs text-ink-gray-5">{{ ticket.name }}</span>
      <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" :class="STATUS_STYLE[ticket.status]"><span class="h-1.5 w-1.5 rounded-full" :class="STATUS_DOT[ticket.status]" />{{ t(ticket.status) }}</span>
      <span v-if="ticket.overdue" class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-500/15 dark:text-red-300">{{ t('Overdue') }}</span>
      <span class="ml-auto flex-shrink-0 text-xs text-ink-gray-5">{{ timeAgo(ticket.modified) }}</span>
    </div>

    <p class="mt-2 line-clamp-2 break-words text-base font-semibold leading-snug text-ink-gray-9">{{ ticket.subject }}</p>

    <div class="mt-2.5 flex flex-wrap items-center gap-2">
      <span class="inline-flex items-center gap-1.5 rounded-md bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-8"><PriorityBars :priority="ticket.priority" class="!h-3.5 !w-3.5" />{{ t(ticket.priority) }}</span>
      <span class="rounded-md bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-7">{{ t(ticket.ticket_type) }}</span>
    </div>

    <div v-if="showRequester || ticket.sla_due" class="mt-3 flex items-center gap-2 border-t pt-2.5 text-sm dark:border-gray-800">
      <template v-if="showRequester">
        <span class="flex min-w-0 items-center gap-1.5 text-ink-gray-7">
          <span class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-semibold" :class="avatarClass(ticket.raised_by)">{{ initials(ticket.raised_by_name || ticket.raised_by) }}</span>
          <span class="truncate">{{ ticket.raised_by_name || ticket.raised_by }}</span>
        </span>
        <FeatherIcon name="arrow-right" class="h-3 w-3 flex-shrink-0 text-ink-gray-4" />
        <span v-if="ticket.assigned_to" class="flex min-w-0 items-center gap-1.5 text-ink-gray-7">
          <span class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-semibold" :class="avatarClass(ticket.assigned_to)">{{ initials(ticket.assigned_name || ticket.assigned_to) }}</span>
          <span class="truncate">{{ ticket.assigned_name }}</span>
        </span>
        <span v-else class="text-ink-gray-4">{{ t('Unassigned') }}</span>
      </template>
      <span v-else-if="ticket.assigned_to" class="truncate text-ink-gray-6">{{ t('Assigned to') }} {{ ticket.assigned_name }}</span>
      <span v-else class="text-ink-gray-4">{{ t('Not yet assigned') }}</span>
    </div>
  </router-link>
</template>

<script setup>
import { FeatherIcon } from 'frappe-ui'
import PriorityBars from '@/components/support/PriorityBars.vue'
import { STATUS_DOT, STATUS_STYLE, avatarClass, initials, timeAgo } from '@/data/support'
import { t } from '@/utils/translate'

defineProps({
  ticket: { type: Object, required: true },
  showRequester: { type: Boolean, default: false },
  selectable: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
})
defineEmits(['toggle'])
</script>
