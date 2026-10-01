<template>
  <div>
    <FormControl
      type="autocomplete"
      :label="field.label"
      :required="!!field.reqd"
      :disabled="disabled || !doctype"
      :options="options"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event?.value ?? $event ?? '')"
    />
    <p class="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
      <template v-if="!doctype">Choose the target doctype first - its fields will be listed here.</template>
      <template v-else-if="loading">Loading fields...</template>
      <template v-else-if="fieldtypes && !options.length">
        This doctype has no {{ fieldtypes.join(' / ') }} field the chosen function can use.
      </template>
      <template v-else>{{ field.description }}</template>
    </p>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { FormControl } from 'frappe-ui'
import { loadDoctypeFields } from '@/data/doctypeMeta'

// A field-name picker: lists the real fields of whichever doctype another
// field (e.g. "Target Doctype") currently points at, instead of making
// someone type a fieldname from memory. Stores the plain fieldname, so the
// underlying DocField stays an ordinary Autocomplete/Data in Desk.
const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: null },
  // The doctype whose fields to list - the caller resolves this from the
  // sibling/parent field that holds it.
  doctype: { type: String, default: null },
  // When set, only fields of these types are offered (e.g. a function's
  // accepted trigger field types). null/undefined = every field.
  fieldtypes: { type: Array, default: null },
  disabled: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const fields = ref([])
const loading = ref(false)

watch(
  () => props.doctype,
  async (doctype) => {
    fields.value = []
    if (!doctype) return
    loading.value = true
    fields.value = await loadDoctypeFields(doctype)
    loading.value = false
  },
  { immediate: true },
)

const options = computed(() => {
  const allowed = props.fieldtypes
  const list = fields.value
    .filter((f) => !allowed || allowed.includes(f.fieldtype))
    .map((f) => ({
    label: `${f.label || f.fieldname}  (${f.fieldname} · ${f.fieldtype})`,
    value: f.fieldname,
  }))
  // A saved value that isn't in the list (doctype changed, field removed)
  // still has to display, rather than silently looking empty.
  if (props.modelValue && !list.some((o) => o.value === props.modelValue)) {
    list.unshift({ label: props.modelValue, value: props.modelValue })
  }
  return list
})
</script>
