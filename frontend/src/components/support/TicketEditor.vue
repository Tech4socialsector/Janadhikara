<template>
  <!-- Helpdesk's composer: To row, rich-text body, attachments, and a bottom bar with the tools on the left and
  Discard / Send on the right. -->
  <div class="overflow-hidden rounded-lg border bg-surface-white shadow-sm dark:border-gray-700" @keydown.capture="onKey">
    <!-- To (and Cc), as in Helpdesk: people can be removed and added; the team's replies go to the requester by default -->
    <div class="flex items-center gap-2 border-b px-3 py-2 dark:border-gray-700 sm:px-4">
      <span class="text-sm text-ink-gray-4">{{ t('To') }}:</span>
      <RecipientField v-if="editable" ref="toField" :model-value="to" :options="options" :placeholder="t('Add a person')" @update:model-value="$emit('update:to', $event)" />
      <span v-else class="inline-flex min-w-0 items-center rounded-full bg-surface-gray-2 px-2.5 py-0.5 text-sm text-ink-gray-8"><span class="truncate">{{ fixedTo }}</span></span>
      <Button v-if="editable" variant="ghost" size="sm" :class="showCc || cc.length ? '!bg-surface-gray-4' : '!text-ink-gray-4'" @click="toggleCc">{{ t('Cc') }}</Button>
    </div>
    <div v-if="editable && (showCc || cc.length)" class="flex items-center gap-2 border-b px-3 py-2 dark:border-gray-700 sm:px-4">
      <span class="text-sm text-ink-gray-4">{{ t('Cc') }}:</span>
      <RecipientField ref="ccField" :model-value="cc" :options="options.filter((o) => !to.includes(o.user))" :placeholder="t('Add a person')" @update:model-value="$emit('update:cc', $event)" />
    </div>

    <TextEditor
      ref="editorRef"
      :content="modelValue"
      :placeholder="placeholder"
      editor-class="prose-sm max-w-full min-h-[5.5rem] max-h-[35vh] overflow-y-auto px-3 py-3 focus:outline-none sm:min-h-[6.5rem] sm:px-4"
      :upload-function="uploadImage"
      @change="$emit('update:modelValue', $event)"
    >
      <template #bottom="{ editor }">
        <ul v-if="attachments.length" class="flex flex-wrap gap-2 px-3 pb-2 sm:px-4">
          <li v-for="file in attachments" :key="file.url" class="inline-flex items-center gap-1.5 rounded bg-surface-gray-2 px-2 py-1 text-sm text-ink-gray-7">
            <FeatherIcon name="paperclip" class="h-3.5 w-3.5" /><span class="max-w-[12rem] truncate">{{ file.name }}</span>
            <button type="button" class="text-ink-gray-5 hover:text-ink-gray-8" :aria-label="t('Remove')" @click="$emit('remove-file', file)"><FeatherIcon name="x" class="h-3.5 w-3.5" /></button>
          </li>
        </ul>

        <div class="flex flex-col gap-2 border-t px-2 py-2 dark:border-gray-700 sm:flex-row sm:items-center sm:justify-between sm:px-3">
          <!-- the tools: spread across the width on a phone (no sideways scrolling), packed on the left on a computer -->
          <div class="flex min-w-0 items-center justify-between sm:flex-1 sm:justify-start sm:gap-0.5 sm:overflow-x-auto">
            <ToolButton :label="t('Attach file')" :loading="uploading" @click="pickFile"><FeatherIcon name="paperclip" class="h-[1.125rem] w-[1.125rem] sm:h-4 sm:w-4" /></ToolButton>
            <input ref="fileInput" type="file" class="hidden" @change="onFile" />
            <span class="mx-1 hidden h-4 w-px flex-shrink-0 bg-outline-gray-2 sm:block" />
            <ToolButton v-for="tool in tools" :key="tool.label" :label="tool.label" :active="tool.active?.(editor)" @click="tool.run(editor)">
              <span v-if="tool.text" class="text-base sm:text-sm" :class="tool.text.class">{{ tool.text.char }}</span>
              <FeatherIcon v-else :name="tool.icon" class="h-[1.125rem] w-[1.125rem] sm:h-4 sm:w-4" />
            </ToolButton>
          </div>
          <!-- Discard and Send: Send takes the width on a phone, and carries the shortcut only on a computer -->
          <div class="flex flex-shrink-0 items-center gap-2 border-t pt-2 dark:border-gray-700 sm:border-0 sm:pt-0">
            <Button class="sm:!h-7" @click="$emit('discard')">{{ t('Discard') }}</Button>
            <Button class="flex-1 sm:flex-none" variant="solid" :loading="sending" :disabled="empty || uploading" @click="$emit('send')">
              {{ t('Send') }}<span class="ml-1 hidden sm:inline">({{ isMac ? '⌘' : 'Ctrl' }} + ⏎)</span>
            </Button>
          </div>
        </div>
      </template>
    </TextEditor>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, ref } from 'vue'
import { Button, FeatherIcon, TextEditor, Tooltip } from 'frappe-ui'
import RecipientField from '@/components/support/RecipientField.vue'
import { uploadAttachment } from '@/data/support'
import { t } from '@/utils/translate'

const props = defineProps({
  modelValue: { type: String, default: '' },
  // the team can choose who a reply goes to; the requester writes to the team
  editable: { type: Boolean, default: false },
  options: { type: Array, default: () => [] },
  to: { type: Array, default: () => [] },
  cc: { type: Array, default: () => [] },
  fixedTo: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  sending: { type: Boolean, default: false },
  attachments: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue', 'update:to', 'update:cc', 'send', 'discard', 'close', 'add-file', 'remove-file'])
defineExpose({ focus: () => editorRef.value?.editor?.commands.focus() })

const editorRef = ref(null)
const fileInput = ref(null)
const uploading = ref(false)
const isMac = typeof navigator !== 'undefined' && /Mac/i.test(navigator.platform)
const empty = computed(() => (!props.modelValue.replace(/<[^>]*>/g, '').trim() && !/<img/.test(props.modelValue)) || (props.editable && !props.to.length))
const showCc = ref(false)
const ccField = ref(null)
const toggleCc = () => {
  showCc.value = !showCc.value
  if (showCc.value) setTimeout(() => ccField.value?.focus(), 0)
}

// A tool button of the bottom bar
const ToolButton = defineComponent({
  props: { label: String, active: Boolean, loading: Boolean },
  emits: ['click'],
  setup: (p, { slots, emit: out }) => () =>
    h(Tooltip, { text: p.label }, () =>
      h('button', { type: 'button', 'aria-label': p.label, disabled: p.loading, class: `flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md text-ink-gray-8 transition-colors hover:bg-surface-gray-3 active:bg-surface-gray-3 sm:h-7 sm:w-7 sm:rounded ${p.active ? 'bg-surface-gray-3' : ''}`, onMousedown: (e) => e.preventDefault(), onClick: () => out('click') }, slots.default?.()),
    ),
})
const tools = [
  { label: t('Bold'), text: { char: 'B', class: 'font-bold' }, active: (e) => e.isActive('bold'), run: (e) => e.chain().focus().toggleBold().run() },
  { label: t('Italic'), text: { char: 'I', class: 'italic font-serif' }, active: (e) => e.isActive('italic'), run: (e) => e.chain().focus().toggleItalic().run() },
  { label: t('Underline'), text: { char: 'U', class: 'underline' }, active: (e) => e.isActive('underline'), run: (e) => e.chain().focus().toggleUnderline().run() },
  { label: t('Bulleted list'), icon: 'list', active: (e) => e.isActive('bulletList'), run: (e) => e.chain().focus().toggleBulletList().run() },
  { label: t('Numbered list'), text: { char: '1.', class: 'font-medium' }, active: (e) => e.isActive('orderedList'), run: (e) => e.chain().focus().toggleOrderedList().run() },
  { label: t('Code'), icon: 'code', active: (e) => e.isActive('code'), run: (e) => e.chain().focus().toggleCode().run() },
  {
    label: t('Link'), icon: 'link', active: (e) => e.isActive('link'),
    run: (e) => {
      const url = window.prompt(t('Link address'), 'https://')
      if (url === null) return
      url.trim() ? e.chain().focus().extendMarkRange('link').setLink({ href: url.trim() }).run() : e.chain().focus().unsetLink().run()
    },
  },
]

const pickFile = () => fileInput.value?.click()
async function onFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  uploading.value = true
  try {
    emit('add-file', { name: file.name, url: await uploadAttachment(file) })
  } catch (err) {
    emit('add-file', { error: String(err?.message || t('The file could not be uploaded.')) })
  } finally {
    uploading.value = false
  }
}
// Images pasted or dropped into the editor become private attachments too
const uploadImage = async (file) => ({ file_url: await uploadAttachment(file), file_name: file.name, is_private: 1 })
const onKey = (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    e.stopPropagation()
    if (!empty.value && !props.sending) emit('send')
  } else if (e.key === 'Escape') {
    emit('close')
  }
}
</script>
