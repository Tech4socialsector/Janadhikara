<template>
  <!-- A Link value for a list filter: a pop-up list of the records to search and click, not an ID to type. -->
  <Autocomplete
    :options="options"
    :loading="entry.loading"
    :max-options="500"
    :placeholder="placeholder"
    :model-value="chosen"
    @update:model-value="$emit('update:modelValue', $event?.value ?? '')"
  />
</template>

<script setup>
import { computed } from 'vue'
import { Autocomplete } from 'frappe-ui'
import { linkOptions } from '@/data/linkOptions'

const props = defineProps({
  doctype: { type: String, required: true }, // the doctype the Link points at
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  // a first entry that clears the filter (the quick filter boxes use their own label for it)
  allLabel: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

const entry = computed(() => linkOptions(props.doctype))
const options = computed(() => (props.allLabel ? [{ label: props.allLabel, value: '' }, ...entry.value.options] : entry.value.options))
const chosen = computed(() => (props.modelValue ? entry.value.options.find((o) => o.value === props.modelValue) || { label: props.modelValue, value: props.modelValue } : null))
</script>
