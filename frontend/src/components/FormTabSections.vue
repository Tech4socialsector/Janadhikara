<template>
  <div class="space-y-6">
    <div v-for="(section, sIdx) in sections" :key="sIdx" v-show="isSectionVisible(section)">
      <h3 v-if="section.label" class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
        {{ section.label }}
      </h3>
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
        <div v-for="(column, cIdx) in section.columns" :key="cIdx" class="flex flex-1 flex-col gap-4">
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
defineEmits(['update:newDocName', 'address-resolved', 'pincode-resolved', 'location-resolved'])

// Same depends_on convention as DynamicField.vue's own fields, applied at
// the Section Break level - a section with no condition always shows
// (evaluateDependsOn's own no-expression fallback).
function isSectionVisible(section) {
  return evaluateDependsOn(section.dependsOn, props.values)
}
</script>
