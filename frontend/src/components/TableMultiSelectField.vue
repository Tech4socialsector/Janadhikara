<template>
  <div>
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">{{ field.label }}</label>
    <MultiSelect
      class="w-full [&_button]:w-full"
      :model-value="selectedValues"
      :options="options"
      :placeholder="`Select ${targetDoctype}...`"
      @update:model-value="onUpdate"
    />
    <div v-if="options.length" class="mt-1 flex items-center gap-1">
      <Button v-if="selectedValues.length < options.length" variant="ghost" size="sm" @click="onUpdate(options.map((o) => o.value))">{{ t('Select all') }}</Button>
      <Button v-if="selectedValues.length" variant="ghost" size="sm" @click="onUpdate([])">{{ t('Clear all') }}</Button>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { Button, MultiSelect, useCall } from 'frappe-ui'
import { t } from '@/utils/translate'

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

// A Table MultiSelect's own child doctype (field.options) has exactly one
// meaningful field besides the standard ones - that's the Link to the
// doctype actually being selected from (e.g. App Module Setting Role.role
// links to Role). Fetch that child doctype's meta once to find it.
const childMetaResource = useCall({
  url: `/api/v2/doctype/${props.field.options}/meta`,
  method: 'GET',
  cacheKey: `janadhikara-meta-${props.field.options}`,
})

const linkFieldname = computed(() => {
  const fields = childMetaResource.data?.fields || []
  const linkField = fields.find((f) => f.fieldtype === 'Link')
  return linkField?.fieldname || null
})

const targetDoctype = computed(() => {
  const fields = childMetaResource.data?.fields || []
  const linkField = fields.find((f) => f.fieldtype === 'Link')
  return linkField?.options || ''
})

// useCall's `url` is passed through Vue's unref() internally, which only
// unwraps a ref/computed - a plain arrow function is returned as-is and
// gets template-string-stringified into the request path, never actually
// invoked. A computed() is what unref() actually resolves.
const targetRecordsUrl = computed(() => `/api/v2/document/${targetDoctype.value}`)

const targetRecordsResource = useCall({
  url: targetRecordsUrl,
  method: 'GET',
  // The v2 API has no "unlimited" sentinel (limit: 0 fetches zero rows, not
  // all of them) - this is a multi-select options list, not a paged view,
  // so a large fixed limit stands in for "effectively all".
  params: () => ({ fields: JSON.stringify(['name']), limit: 1000 }),
  immediate: false,
})

watch(
  targetDoctype,
  (value) => {
    if (value) targetRecordsResource.fetch()
  },
  { immediate: true },
)

const options = computed(() => {
  const rows = targetRecordsResource.data || []
  return rows.map((r) => ({ label: props.field.option_labels?.[r.name] || r.name, value: r.name }))
})

const selectedValues = computed(() => {
  if (!linkFieldname.value) return []
  return (props.modelValue || []).map((row) => row[linkFieldname.value]).filter(Boolean)
})

function onUpdate(values) {
  if (!linkFieldname.value) return
  emit(
    'update:modelValue',
    values.map((v) => ({ [linkFieldname.value]: v })),
  )
}
</script>
