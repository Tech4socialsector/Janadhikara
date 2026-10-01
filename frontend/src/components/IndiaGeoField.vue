<template>
  <div>
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">
      {{ field.label }}<span v-if="field.reqd" class="text-red-500">*</span>
    </label>
    <div class="india-geo-combobox min-w-0">
      <Combobox
        open-on-focus
        open-on-click
        :options="options"
        :loading="loading"
        :disabled="disabled"
        :placeholder="placeholder"
        :model-value="modelValue"
        @update:model-value="(value) => $emit('update:modelValue', value || null)"
      />
    </div>
    <p v-if="error" class="mt-1.5 text-xs text-red-500">{{ error }}</p>
    <p v-else-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">
      {{ field.description }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Combobox } from 'frappe-ui'
import { useIndiaGeoData } from '@/composables/useIndiaGeoData'

// Renders a Data field as a plain searchable dropdown backed directly by
// a free, static India states/districts dataset (see useIndiaGeoData) -
// no Frappe Link field, no State List/District master doctype behind it.
// The underlying DocField is just a Data field holding whatever string
// the user picks, same as typing it in by hand.
//
// Which dataset (every state, or one state's districts) comes entirely
// from this field's own `options` ("india_state" / "india_district" -
// see DynamicField.vue's controlType routing), not its fieldname - any
// Data field on any doctype can opt into either by declaring that
// options value, the same as a Link field names its linked doctype via
// its own `options`.
const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: null },
  disabled: { type: Boolean, default: false },
  // Resolved from this field's own link_filters the same generic way
  // LinkField.vue's cascading filters are (see DynamicField.vue's
  // linkFilters computed) - {fieldname: value} pairs. india_district has
  // exactly one meaningful filter dimension (which state to narrow to),
  // so whichever key names it, its value is what's used - no fieldname
  // ("state") hardcoded here either.
  filters: { type: Object, default: () => ({}) },
})
defineEmits(['update:modelValue'])

const { states, districtsByState, loading, error } = useIndiaGeoData()

const isDistrictLevel = computed(() => props.field.options === 'india_district')
const filterValue = computed(() => Object.values(props.filters)[0] || '')

const placeholder = computed(() => {
  if (isDistrictLevel.value && !filterValue.value) return 'Select a State first'
  return `Select ${props.field.label}`
})

const options = computed(() => {
  const names = isDistrictLevel.value
    ? districtsByState.value[filterValue.value] || []
    : states.value
  const opts = names.map((name) => ({ label: name, value: name }))
  // Unconditional, same as every other Select/Link field in the app now -
  // a required field is still only enforced empty-or-not at save time, not
  // by removing the ability to clear it while editing.
  opts.unshift({ label: 'Select option', value: '' })
  return opts
})
</script>

<style scoped>
/* Same trigger-fills-its-container fix as LinkField.vue's Combobox - reka-ui
renders the actual input/button a few levels deep in its own unstyled
wrapper divs, so width:100% needs forcing all the way down or the control
shrinks to fit its content instead of filling the field. */
.india-geo-combobox :deep(> div) {
  display: block;
  width: 100%;
}
.india-geo-combobox :deep([data-slot='trigger']) {
  width: 100%;
}
</style>
