<template>
  <div class="space-y-6 [&_input:not([type=checkbox]):not([type=radio])]:h-8 [&_[data-slot=trigger]]:h-8 [&_[data-slot=trigger]]:w-full [&_select]:h-8">
    <div v-for="(section, sIdx) in laidOut" :key="sIdx" v-show="isSectionVisible(section)">
      <h3 v-if="section.label" class="text-base font-medium text-gray-700 dark:text-gray-300" :class="section.description ? 'mb-1' : 'mb-3'">
        {{ section.label }}
      </h3>
      <p v-if="section.description" class="mb-3 text-p-xs text-ink-gray-5">{{ section.description }}</p>
      <div class="flex flex-col gap-4 sm:flex-row sm:gap-6">
        <div v-if="sIdx === 0 && showNameField" class="flex-1">
          <FormControl
            type="text"
            label="Name"
            required
            :disabled="!isNew"
            :model-value="isNew ? newDocName : name"
            @update:model-value="$emit('update:newDocName', $event)"
          />
        </div>
        <div v-for="(column, cIdx) in section.visibleColumns" :key="cIdx" class="flex min-w-0 flex-1 basis-0 flex-col gap-4">
          <div v-for="field in column" :key="field.fieldname">
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

// Conditional questions (e.g. a "Please specify" box) leave empty gaps when they're hidden. A section
// where something is hidden is laid out again from what is visible: the questions are put in question-number
// order (an unnumbered one stays with the numbered question before it) and split evenly into two columns,
// or one when there is only a little to show. A section with nothing hidden keeps the layout it was designed with.
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
    const all = section.columns.flat()
    const visible = all.filter((f) => evaluateDependsOn(f.depends_on, props.values))
    if (visible.length === all.length) return { ...section, visibleColumns: section.columns }
    let lastKey = null
    const keyed = visible.map((field, order) => {
      lastKey = numberOf(field.label) || lastKey
      return { field, order, key: lastKey }
    })
    keyed.sort((a, b) => (a.key && b.key ? compareNumbers(a.key, b.key) : 0) || a.order - b.order)
    const fields = keyed.map((k) => k.field)
    if (fields.length < 2 || section.columns.length < 2) return { ...section, visibleColumns: [fields] }
    const half = Math.ceil(fields.length / 2)
    return { ...section, visibleColumns: [fields.slice(0, half), fields.slice(half)] }
  })
)

// Same depends_on convention as DynamicField.vue's own fields, applied at
// the Section Break level - a section with no condition always shows
// (evaluateDependsOn's own no-expression fallback).
function isSectionVisible(section) {
  return evaluateDependsOn(section.dependsOn, props.values)
}
</script>
