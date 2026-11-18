<template>
  <div class="space-y-6 [&_input:not([type=checkbox]):not([type=radio])]:h-8 [&_[data-slot=trigger]]:h-8 [&_[data-slot=trigger]]:w-full [&_select]:h-8">
    <div v-for="(section, sIdx) in laidOut" :key="sIdx" v-show="isSectionVisible(section)">
      <h3 v-if="section.label" class="text-base font-medium text-gray-700 dark:text-gray-300" :class="section.description ? 'mb-1' : 'mb-3'">
        {{ section.label }}
      </h3>
      <p v-if="section.description" class="mb-3 text-p-xs text-ink-gray-5">{{ section.description }}</p>
      <!-- One grid per section: as many columns as the width allows (about 19rem each), the questions flowing along the
      rows in question order. Short answers share a row; long ones (text, many options, a map) take the whole row. -->
      <div class="form-grid">
        <div v-if="sIdx === 0 && showNameField">
          <FormControl
            type="text"
            label="Name"
            required
            :disabled="!isNew"
            :model-value="isNew ? newDocName : name"
            @update:model-value="$emit('update:newDocName', $event)"
          />
        </div>
        <div v-for="field in section.fields" :key="field.fieldname" :data-fieldname="field.fieldname" class="min-w-0 scroll-mt-24" :class="{ 'form-full': isFullWidth(field) }">
          <DynamicField
            :field="field"
            :doctype="doctype"
            :docname="isNew ? null : name"
            :sibling-values="values"
            :model-value="values[field.fieldname]"
            @update:model-value="values[field.fieldname] = $event"
            @address-resolved="$emit('address-resolved', $event)"
            @pincode-resolved="$emit('pincode-resolved', $event)"
            @location-resolved="$emit('location-resolved', $event)"
            @geo-changed="$emit('geo-changed', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { FormControl } from 'frappe-ui'
import DynamicField from '@/components/DynamicField.vue'
import { computed } from 'vue'
import { evaluateDependsOn } from '@/utils/dependsOn'

// Factored out of DoctypeForm.vue so the same section/column rendering
// can be used twice from there without duplicating it verbatim: once for
// the desktop tab switcher's single active tab, and once per tab inside
// the mobile accordion (see DoctypeForm.vue) where every tab's fields
// need to render, just collapsed until expanded.
const props = defineProps({
  sections: { type: Array, required: true },
  doctype: { type: String, required: true },
  name: { type: String, default: null },
  isNew: { type: Boolean, default: false },
  newDocName: { type: String, default: '' },
  values: { type: Object, required: true },
  // Only the Name field for a "prompt" autoname doctype belongs on one
  // specific tab's first section (matching where DoctypeForm.vue always
  // put it before this was split out) - passed in as a plain boolean
  // rather than recomputed here, since "which tab/section that actually
  // is" is the caller's own layout decision, not this component's.
  showNameField: { type: Boolean, default: false },
})
defineEmits(['update:newDocName', 'address-resolved', 'pincode-resolved', 'location-resolved', 'geo-changed'])

// Every section is laid out from the questions that are showing (a conditional "Please specify" box that is hidden
// leaves no gap): they are put in question-number order (an unnumbered one stays with the numbered question before
// it) and flow along the section's grid, as many to a row as the width allows. The columns a doctype was designed
// with no longer fix the layout, so the form fills a wide screen and stacks on a phone.
const numberOf = (label) => {
  // the number, then an optional letter right after it (16.1.1a), then the dot and the question text
  const m = /^\s*(\d+(?:\.\d+)*)([a-z]?)\.?\s/i.exec(label || '')
  return m ? [...m[1].split('.').map(Number), m[2] ? m[2].toLowerCase().charCodeAt(0) - 96 : 0] : null
}
const compareNumbers = (a, b) => {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const d = (a[i] ?? -1) - (b[i] ?? -1)
    if (d) return d
  }
  return 0
}

const laidOut = computed(() =>
  props.sections.map((section) => {
    const visible = section.columns.flat().filter((f) => evaluateDependsOn(f.depends_on, props.values))
    let lastKey = null
    const keyed = visible.map((field, order) => {
      lastKey = numberOf(field.label) || lastKey
      return { field, order, key: lastKey }
    })
    keyed.sort((a, b) => (a.key && b.key ? compareNumbers(a.key, b.key) : 0) || a.order - b.order)
    return { ...section, fields: keyed.map((k) => k.field) }
  })
)

// Which questions take a whole row: long answers, lists of many options and the map. Everything else (a name, a
// number, a date, a dropdown, a Yes / No) is one cell of the grid. The option rule mirrors DynamicField's: up to four
// short options sit side by side in a small box; more than that (or long ones) is a box that needs the width.
const WHOLE_ROW_TYPES = new Set([
  'Small Text', 'Text', 'Long Text', 'Text Editor', 'Markdown Editor', 'HTML Editor', 'Code', 'HTML', 'Geolocation',
  'Attach', 'Attach Image', 'Signature', 'Table', 'Table MultiSelect',
])
function isFullWidth(field) {
  if (WHOLE_ROW_TYPES.has(field.fieldtype)) return true
  if (field.fieldtype === 'Select') {
    const options = (field.options || '').split('\n').map((o) => o.trim()).filter(Boolean)
    return options.length > 4 || options.some((o) => o.length > 40)
  }
  return false
}

// Same depends_on convention as DynamicField.vue's own fields, applied at
// the Section Break level - a section with no condition always shows
// (evaluateDependsOn's own no-expression fallback).
function isSectionVisible(section) {
  return evaluateDependsOn(section.dependsOn, props.values)
}
</script>

<style scoped>
/* Two columns (one on a phone): the questions line up in the same columns in every section. */
.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.25rem 1.5rem;
  align-items: start;
}
/* two columns from tablet width up; one on a phone */
@media (min-width: 640px) {
  .form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.form-grid > :deep(.form-full),
.form-grid > .form-full {
  grid-column: 1 / -1;
}
</style>
