<template>
  <!-- Helpdesk's recipient field: a chip per person, and a search that adds more from the people who can see the ticket -->
  <div class="relative flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
    <span v-for="u in chosen" :key="u.user" class="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full bg-surface-gray-2 py-0.5 pl-1 pr-2 text-sm text-ink-gray-8">
      <span class="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[9px] font-semibold" :class="avatarClass(u.user)">{{ initials(u.name) }}</span>
      <span class="truncate" :title="u.email">{{ u.name }}</span>
      <button type="button" class="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8" :aria-label="`${t('Remove')} ${u.name}`" @click="remove(u.user)"><FeatherIcon name="x" class="h-3 w-3" /></button>
    </span>
    <input
      ref="input"
      v-model="query"
      type="text"
      class="h-7 min-w-[7rem] flex-1 border-0 bg-transparent p-0 text-base text-ink-gray-9 placeholder-ink-gray-4 focus:outline-none focus:ring-0"
      :placeholder="chosen.length ? '' : placeholder"
      autocomplete="off"
      @focus="open = true"
      @keydown.down.prevent="move(1)"
      @keydown.up.prevent="move(-1)"
      @keydown.enter.prevent="add(matches[active])"
      @keydown.backspace="!query && chosen.length && remove(chosen[chosen.length - 1].user)"
      @keydown.esc.stop="open = false"
    />
    <ul v-if="open && matches.length" class="absolute left-0 top-full z-30 mt-1 max-h-56 w-full min-w-[14rem] max-w-sm overflow-y-auto rounded-lg border bg-surface-white p-1 shadow-lg dark:border-gray-700" role="listbox">
      <li v-for="(u, i) in matches" :key="u.user" role="option" :aria-selected="i === active">
        <button type="button" class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm" :class="i === active ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-2'" @mousedown.prevent="add(u)">
          <span class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-semibold" :class="avatarClass(u.user)">{{ initials(u.name) }}</span>
          <span class="min-w-0"><span class="block truncate text-ink-gray-9">{{ u.name }}</span><span class="block truncate text-xs text-ink-gray-5">{{ u.email }}</span></span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import { avatarClass, initials } from '@/data/support'
import { t } from '@/utils/translate'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
const query = ref('')
const open = ref(false)
const active = ref(0)
const input = ref(null)

const byUser = computed(() => Object.fromEntries(props.options.map((o) => [o.user, o])))
const chosen = computed(() => props.modelValue.map((u) => byUser.value[u] || { user: u, name: u, email: u }))
const matches = computed(() => {
  const q = query.value.trim().toLowerCase()
  return props.options.filter((o) => !props.modelValue.includes(o.user) && (!q || o.name.toLowerCase().includes(q) || o.email.toLowerCase().includes(q)))
})
watch(matches, () => (active.value = 0))
const move = (d) => matches.value.length && (active.value = (active.value + d + matches.value.length) % matches.value.length)
function add(u) {
  if (!u) return
  emit('update:modelValue', [...props.modelValue, u.user])
  query.value = ''
  open.value = matches.value.length > 1
}
const remove = (user) => emit('update:modelValue', props.modelValue.filter((x) => x !== user))
const close = (e) => {
  if (open.value && !e.target.closest?.('.relative')) open.value = false
}
onMounted(() => document.addEventListener('click', close))
onBeforeUnmount(() => document.removeEventListener('click', close))
defineExpose({ focus: () => input.value?.focus() })
</script>
