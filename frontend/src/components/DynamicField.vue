<template>
<template v-if="isVisible">
  <IndiaGeoField
    v-if="controlType === 'india-geo'"
    :field="effField"
    :model-value="modelValue"
    :disabled="isReadOnly"
    :filters="linkFilters"
    @update:model-value="$emit('update:modelValue', $event)"
  />

  <div v-else-if="controlType === 'geolocation'">
  <GeoLocationField
    :field="effField"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    @address-resolved="(text) => $emit('address-resolved', text)"
    @pincode-resolved="(text) => $emit('pincode-resolved', text)"
    @location-resolved="(point) => $emit('location-resolved', point)"
    @geo-changed="(value) => $emit('geo-changed', { fieldname: field.fieldname, value })"
  />
  </div>

  <div v-else-if="controlType === 'table-multiselect'">
    <TableMultiSelectField
      :field="effField"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>

  <DoctypeFieldPicker
    v-else-if="controlType === 'doctype-field'"
    :field="effField"
    :doctype="pickerDoctype"
    :fieldtypes="pickerFieldtypes"
    :disabled="isReadOnly"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
  />

  <div v-else-if="controlType === 'attach'">
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">{{ field.label }}</label>
    <div v-if="modelValue" class="flex items-center gap-3 rounded-lg border p-2 dark:border-gray-800">
      <img
        v-if="isImageField"
        :src="modelValue"
        class="h-12 w-12 flex-shrink-0 rounded object-cover"
      />
      <FeatherIcon v-else name="paperclip" class="h-5 w-5 flex-shrink-0 text-gray-400" />
      <a
        :href="safeFileUrl"
        target="_blank"
        rel="noopener"
        class="min-w-0 flex-1 truncate text-sm text-gray-700 hover:underline dark:text-gray-300"
      >
        {{ fileName }}
      </a>
      <Tooltip text="Remove file">
        <Button variant="ghost" size="sm" icon="x" tooltip="Clear" @click="$emit('update:modelValue', null)" />
      </Tooltip>
    </div>
    <FileUploader
      v-else
      :file-types="isImageField ? 'image/*' : undefined"
      :upload-args="{ doctype, docname, private: uploadsArePrivate }"
      @success="(file) => $emit('update:modelValue', file.file_url)"
    >
      <template #default="{ uploading, progress, openFileSelector }">
        <Button variant="outline" :loading="uploading" @click="openFileSelector">
          {{ uploading ? `Uploading ${progress}%` : `Attach ${isImageField ? 'Image' : 'File'}` }}
        </Button>
      </template>
    </FileUploader>
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>

  <!-- Question Bank display condition: the value to compare with is picked from the chosen
  field's own choices (a Select's options, Yes/No for a tick box, or a Link's records). -->
  <LinkField
    v-else-if="controlType === 'condition-value' && conditionField.fieldtype === 'Link'"
    :field="{ ...field, fieldtype: 'Link', options: conditionField.options }"
    :disabled="isReadOnly"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
  />
  <FormControl
    v-else-if="controlType === 'condition-value'"
    type="select"
    class="[&_[data-slot=trigger]]:w-full"
    :label="field.label"
    :required="!!isRequired"
    :disabled="isReadOnly"
    :options="conditionValueOptions"
    :description="`Pick one of ${conditionField.label || conditionField.fieldname}'s values.`"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
  />

  <FormControl
    v-else-if="controlType === 'select'"
    type="select"
    class="[&_[data-slot=trigger]]:w-full"
    :class="readOnlyClass"
    :label="field.label"
    :required="!!isRequired"
    :disabled="isReadOnly"
    :options="selectOptions"
    :description="selectDescription"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
  />
  <FormControl
    v-else-if="controlType === 'checkbox'"
    type="checkbox"
    :label="field.label"
    :disabled="isReadOnly"
    :description="field.description"
    :model-value="!!modelValue"
    @update:model-value="$emit('update:modelValue', $event ? 1 : 0)"
  />
  <!-- Pick several: a normal field (a dropdown that takes more than one value); kept one per line -->
  <div v-else-if="controlType === 'multi-choice'">
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">{{ field.label }}<span v-if="isRequired" class="text-red-500">*</span></label>
    <div class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white" role="group" :aria-label="field.label">
      <div class="grid gap-0.5 p-1.5 sm:grid-cols-2" :class="choiceOptions.length > 8 ? 'lg:grid-cols-3' : ''">
        <button
          v-for="o in choiceOptions"
          :key="o"
          type="button"
          :disabled="isReadOnly"
          :aria-pressed="chosenChoices.includes(o)"
          class="flex items-center gap-3 rounded-md px-2.5 py-2 text-left text-sm transition-colors focus:outline-none focus-visible:bg-surface-gray-2 disabled:cursor-not-allowed disabled:opacity-60"
          :class="chosenChoices.includes(o) ? 'bg-surface-gray-2 text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-1'"
          @click="toggleChoice(o)"
        >
          <span
            class="flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-[5px] border transition-colors"
            :class="chosenChoices.includes(o) ? 'border-gray-900 bg-gray-900 text-white dark:border-gray-100 dark:bg-gray-100 dark:text-gray-900' : 'border-outline-gray-3 bg-surface-white'"
          >
            <FeatherIcon v-if="chosenChoices.includes(o)" name="check" class="h-3 w-3" />
          </span>
          <span class="min-w-0 break-words" :class="chosenChoices.includes(o) ? 'font-medium' : ''">{{ o }}</span>
        </button>
      </div>
      <div class="flex items-center justify-between border-t border-outline-gray-1 bg-surface-gray-1 px-3.5 py-1.5 text-p-xs text-ink-gray-5">
        <span>{{ chosenChoices.length }} of {{ choiceOptions.length }} selected</span>
        <button
          v-if="chosenChoices.length && !isReadOnly"
          type="button"
          class="font-medium text-ink-gray-7 hover:text-ink-gray-9"
          @click="$emit('update:modelValue', '')"
        >
          Clear
        </button>
      </div>
    </div>
    <p v-if="field.description" class="mt-1.5 whitespace-pre-line text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>
  <div v-else-if="controlType === 'textarea'">
    <FormControl
      type="textarea"
      :class="readOnlyClass"
      :label="field.label"
      :required="!!isRequired"
      :disabled="isReadOnly"
      :description="field.description"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      @blur="touched = true"
    />
    <p v-if="touched && validationError" class="mt-1.5 text-xs text-red-500">{{ validationError }}</p>
  </div>

  <div v-else-if="controlType === 'rich-text'">
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">
      {{ field.label }}<span v-if="isRequired" class="text-red-500">*</span>
    </label>
    <TextEditor
      :content="modelValue || ''"
      :editable="!isReadOnly"
      :fixed-menu="!isReadOnly"
      editor-class="prose-sm max-w-none rounded-b-lg border border-t-0 border-gray-200 px-3 py-2 min-h-[8rem] dark:border-gray-700 dark:prose-invert"
      @change="$emit('update:modelValue', $event)"
    />
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>

  <div v-else-if="controlType === 'rating'" class="space-y-1.5">
    <label class="block text-sm text-gray-700 dark:text-gray-300">
      {{ field.label }}<span v-if="isRequired" class="text-red-500">*</span>
    </label>
    <Rating
      :model-value="ratingValue"
      :readonly="isReadOnly"
      @update:model-value="$emit('update:modelValue', $event / 5)"
    />
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>

  <div v-else-if="controlType === 'time'">
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">
      {{ field.label }}<span v-if="isRequired" class="text-red-500">*</span>
    </label>
    <TimePicker
      class="w-full"
      :class="readOnlyClass"
      :disabled="isReadOnly"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>

  <div v-else-if="controlType === 'duration'" class="space-y-1.5">
    <label class="block text-sm text-gray-700 dark:text-gray-300">
      {{ field.label }}<span v-if="isRequired" class="text-red-500">*</span>
    </label>
    <div class="grid grid-cols-4 gap-2">
      <div v-for="seg in durationSegments" :key="seg.key">
        <FormControl
          type="number"
          :label="seg.label"
          :disabled="isReadOnly"
          :model-value="seg.value"
          @update:model-value="setDurationSegment(seg.key, $event)"
        />
      </div>
    </div>
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>

  <div v-else-if="controlType === 'color'">
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">
      {{ field.label }}<span v-if="isRequired" class="text-red-500">*</span>
    </label>
    <div class="flex items-center gap-2">
      <input
        type="color"
        class="h-8 w-10 flex-shrink-0 cursor-pointer rounded border border-gray-200 bg-transparent p-0.5 disabled:cursor-not-allowed dark:border-gray-700"
        :disabled="isReadOnly"
        :value="modelValue || '#000000'"
        @input="$emit('update:modelValue', $event.target.value)"
      />
      <FormControl
        type="text"
        class="flex-1"
        :class="readOnlyClass"
        :disabled="isReadOnly"
        :model-value="modelValue"
        @update:model-value="$emit('update:modelValue', $event)"
      />
    </div>
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
  </div>

  <FormControl
    v-else-if="controlType === 'autocomplete'"
    type="autocomplete"
    :class="readOnlyClass"
    :label="field.label"
    :required="!!isRequired"
    :disabled="isReadOnly"
    :options="selectOptions"
    :description="field.description"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event?.value ?? $event)"
  />

  <div v-else-if="controlType === 'json'">
    <FormControl
      type="textarea"
      :class="[readOnlyClass, 'font-mono text-xs']"
      :label="field.label"
      :required="!!isRequired"
      :disabled="isReadOnly"
      :description="jsonError || field.description"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      @blur="touched = true"
    />
  </div>

  <LinkField
    v-else-if="controlType === 'dynamic-link'"
    :field="dynamicLinkField"
    :filters="linkFilters"
    :disabled="isReadOnly || !dynamicLinkDoctype"
    :class="readOnlyClass"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
  />

  <LinkField
    v-else-if="controlType === 'link'"
    :field="effField"
    :filters="linkFilters"
    :disabled="isReadOnly"
    :class="readOnlyClass"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template v-if="isUserLink && modelValue" #suffix>
      <UserLinkHoverCard :user="modelValue">
        <FeatherIcon name="user" class="h-4 w-4 text-gray-400" />
      </UserLinkHoverCard>
    </template>
  </LinkField>
  <div v-else-if="controlType === 'date' || controlType === 'datetime-local'">
    <label class="mb-1.5 block text-xs text-ink-gray-5">
      {{ field.label }}<span v-if="isRequired" class="text-red-500">*</span>
    </label>
    <component
      :is="controlType === 'date' ? DatePicker : DateTimePicker"
      :class="readOnlyClass"
      :format="controlType === 'date' ? 'DD MMM YYYY' : undefined"
      :disabled="isReadOnly"
      :model-value="modelValue || ''"
      placeholder="Select date"
      @update:model-value="$emit('update:modelValue', $event || null)"
      @blur="touched = true"
    />
    <p v-if="field.description" class="mt-1.5 text-p-xs text-ink-gray-5">{{ field.description }}</p>
    <p v-if="touched && validationError" class="mt-1.5 text-xs text-red-500">{{ validationError }}</p>
  </div>
  <div v-else>
    <FormControl
      :type="controlType"
      :class="readOnlyClass"
      :label="field.label"
      :required="!!isRequired"
      :disabled="isReadOnly"
      :description="linkDescription"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      @blur="touched = true"
    />
    <p v-if="touched && validationError" class="mt-1.5 text-xs text-red-500">{{ validationError }}</p>
  </div>
</template>
</template>

<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { FormControl, FileUploader, Button, FeatherIcon, Tooltip, TextEditor, Rating, TimePicker, DatePicker, DateTimePicker } from 'frappe-ui'
import UserLinkHoverCard from '@/components/UserLinkHoverCard.vue'
// The map and the India states/districts pickers are only needed by a few forms: load them when first shown
const GeoLocationField = defineAsyncComponent(() => import('@/components/GeoLocationField.vue'))
const IndiaGeoField = defineAsyncComponent(() => import('@/components/IndiaGeoField.vue'))
import LinkField from '@/components/LinkField.vue'
import DoctypeFieldPicker from '@/components/DoctypeFieldPicker.vue'
import { fieldFunctionRegistryResource } from '@/data/fieldFunctionRegistry'
import TableMultiSelectField from '@/components/TableMultiSelectField.vue'
import { getValidatorForField } from '@/utils/validation'
import { evaluateDependsOn } from '@/utils/dependsOn'
import { loadDoctypeFields } from '@/data/doctypeMeta'

// Uploaded documents and photos hold personal data: they are private files (served only to a signed-in
// user). Only logos, which the sign-in page also shows, stay public.
const PUBLIC_UPLOAD_DOCTYPES = ['App Setting', 'Partner Details', 'User']

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: null },
  doctype: { type: String, default: null },
  docname: { type: String, default: null },
  // The other field values on the same document/row - only needed to
  // resolve a Link field's own link_filters (e.g. District filtered by
  // State), which reference sibling fields by name. Callers that render a
  // full form/row (DoctypeForm, ChildTable) pass their own `values`/
  // `editingRow`; nothing else in this component reads it.
  siblingValues: { type: Object, default: () => ({}) },
  // For a field inside a child-table row: the parent form's values, so a
  // picker can read a parent-level field (e.g. Target Doctype).
  parentValues: { type: Object, default: () => ({}) },
  // The whole row/form is being viewed, not edited (e.g. a unit that belongs to another worker).
  readOnly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'address-resolved', 'pincode-resolved', 'location-resolved', 'geo-changed'])

// Frappe's own DocField `depends_on` convention (see utils/dependsOn.js) -
// a field with one is only rendered while its condition holds. `values`
// itself is siblingValues since this field's own current value is one of
// the things a later field's condition might read (e.g. Q19.1 depending
// on Q19's own answer, not just a field elsewhere on the form).
// `parent` in a child row's depends_on (e.g. "eval:parent.has_intervention_units")
// is the parent form's values - same as Frappe desk.
const uploadsArePrivate = computed(() => !PUBLIC_UPLOAD_DOCTYPES.includes(props.doctype))
// Only a stored file or a web address may become a link (never a javascript: value typed through the API)
const safeFileUrl = computed(() =>
  /^(\/files\/|\/private\/files\/|https?:\/\/)/.test(String(props.modelValue || '')) ? props.modelValue : '#',
)
const isVisible = computed(() => evaluateDependsOn(props.field.depends_on, props.siblingValues, props.parentValues))
// Mandatory, or mandatory only while its `mandatory_depends_on` holds - shown with the red * either way
const isRequired = computed(
  () =>
    !!props.field.reqd ||
    (!!props.field.mandatory_depends_on && !!evaluateDependsOn(props.field.mandatory_depends_on, props.siblingValues, props.parentValues))
)
const effField = computed(() => ({ ...props.field, reqd: isRequired.value ? 1 : 0 }))

// A Data field whose `options` names one of these renders as a plain
// searchable dropdown backed by a free India states/districts dataset
// (see IndiaGeoField.vue) instead of the fieldtype's own default plain-
// text control. This reuses `options` the exact same way a Link field
// already does (naming what the field's value is drawn from) rather than
// hardcoding specific fieldnames - any Data field on any doctype can opt
// into this control just by declaring the right `options` value in its
// own DocField definition, the same as declaring a Link field's linked
// doctype.
const INDIA_GEO_OPTIONS = new Set(['india_state', 'india_district'])

// Fields that pick one of another doctype's fields (Field Function Mapping's
// trigger/target/input field) - keyed by fieldname, each naming the sibling
// (or, inside a child row, parent) field that holds the doctype to list.
// Only applies to Autocomplete/Data fields, and only when that doctype field
// is actually on the same form, so the same fieldnames elsewhere are
// unaffected.
const DOCTYPE_FIELD_SOURCES = {
  trigger_field: 'target_doctype',
  target_field: 'target_doctype',
  input_field: 'target_doctype',
  policy_field: 'target_doctype',
  // Question Bank: the field a question / section's display condition looks at.
  show_if_field: 'show_if_doctype',
  section_show_if_field: 'section_show_if_doctype',
}
const pickerDoctype = computed(() => {
  const source = DOCTYPE_FIELD_SOURCES[props.field.fieldname]
  if (!source) return undefined
  return props.siblingValues?.[source] ?? props.parentValues?.[source] ?? null
})
// Field types the chosen function accepts for this picker (trigger/also-uses
// field only - a target field can be any type the output fits, which the
// server validates per row). Null until the registry has loaded, or when the
// function isn't chosen yet, so nothing is hidden prematurely.
const pickerFieldtypes = computed(() => {
  const fnName = props.siblingValues?.function_name ?? props.parentValues?.function_name
  const func = fieldFunctionRegistryResource.data?.[fnName]
  if (!func) return null
  if (props.field.fieldname === 'trigger_field') return func.trigger_fieldtypes || null
  if (props.field.fieldname === 'input_field') return func.input_fieldtypes || null
  return null
})
const doctypeFieldSource = computed(() => {
  if (!['Autocomplete', 'Data'].includes(props.field.fieldtype)) return false
  const source = DOCTYPE_FIELD_SOURCES[props.field.fieldname]
  if (!source) return false
  return source in (props.siblingValues || {}) || source in (props.parentValues || {}) || pickerDoctype.value !== undefined
})

watch(doctypeFieldSource, (isPicker) => {
  if (isPicker && !fieldFunctionRegistryResource.data && !fieldFunctionRegistryResource.loading) {
    fieldFunctionRegistryResource.fetch()
  }
}, { immediate: true })

// Question Bank "Display depends on" (and the section version): the Condition and Value fields
// know which field was picked above them, so they can speak plainly and offer real choices.
//   Condition: "is" / "is not" / "has a value" / "is empty"  (stored as = / != / is set / is not set)
//   Value:     House Ownership is a Select -> a dropdown of Owned, Rented, ...
//   Summary:   "This question is shown only while House Ownership is Rented."
const CONDITION_FIELDS = {
  show_if_operator: ['show_if', 'operator'],
  show_if_value: ['show_if', 'value'],
  section_show_if_operator: ['section_show_if', 'operator'],
  section_show_if_value: ['section_show_if', 'value'],
}
const OPERATOR_LABELS = { '=': 'is', '!=': 'is not', 'is set': 'has a value', 'is not set': 'is empty' }
const conditionPart = computed(() => {
  const part = CONDITION_FIELDS[props.field.fieldname]
  return part && `${part[0]}_doctype` in (props.siblingValues || {}) ? part : null
})
const conditionField = ref(null)
watch(
  () => {
    const part = conditionPart.value
    return part && [props.siblingValues[`${part[0]}_doctype`], props.siblingValues[`${part[0]}_field`]]
  },
  async (target) => {
    conditionField.value = null
    if (!target?.[0] || !target?.[1]) return
    const fields = await loadDoctypeFields(target[0])
    conditionField.value = fields.find((f) => f.fieldname === target[1]) || null
  },
  { immediate: true },
)
const conditionValueOptions = computed(() => {
  const f = conditionField.value
  if (f?.fieldtype === 'Check') {
    return [{ label: 'Select option', value: '' }, { label: 'Ticked (Yes)', value: '1' }, { label: 'Not ticked (No)', value: '0' }]
  }
  const opts = (f?.options || '').split('\n').map((v) => v.trim()).filter(Boolean).map((v) => ({ label: v, value: v }))
  return [{ label: 'Select option', value: '' }, ...opts]
})
const conditionSummary = computed(() => {
  const part = conditionPart.value
  const f = conditionField.value
  if (!part || part[1] !== 'operator' || !f) return null
  const op = props.siblingValues[`${part[0]}_operator`] || '='
  const value = props.siblingValues[`${part[0]}_value`]
  const needsValue = op === '=' || op === '!='
  if (needsValue && !value) return null
  const shown = part[0] === 'section_show_if' ? 'This whole section is shown' : 'This question is shown'
  return `${shown} only while ${f.label || f.fieldname} ${OPERATOR_LABELS[op]}${needsValue ? ` ${value}` : ''}.`
})
const selectDescription = computed(() => conditionSummary.value || props.field.description)

const controlType = computed(() => {
  if (doctypeFieldSource.value) return 'doctype-field'
  if (conditionPart.value?.[1] === 'value' && ['Select', 'Check', 'Link'].includes(conditionField.value?.fieldtype)) {
    return 'condition-value'
  }
  if (props.field.fieldtype === 'Data' && INDIA_GEO_OPTIONS.has(props.field.options)) {
    return 'india-geo'
  }
  switch (props.field.fieldtype) {
    case 'Select':
      return 'select'
    case 'Check':
      return 'checkbox'
    case 'Small Text':
      // A Small Text with several choices listed in its Options is a "pick all that apply" question.
      if ((props.field.options || '').includes('\n')) return 'multi-choice'
      return 'textarea'
    case 'Text':
    case 'Long Text':
    case 'Code':
    case 'Markdown Editor':
      return 'textarea'
    case 'Text Editor':
    case 'HTML Editor':
      return 'rich-text'
    case 'Int':
    case 'Long Int':
    case 'Float':
    case 'Currency':
    case 'Percent':
      return 'number'
    case 'Date':
      return 'date'
    case 'Datetime':
      return 'datetime-local'
    case 'Time':
      return 'time'
    case 'Duration':
      return 'duration'
    case 'Rating':
      return 'rating'
    case 'Color':
      return 'color'
    case 'Password':
      return 'password'
    case 'Phone':
      return 'tel'
    case 'Attach':
    case 'Attach Image':
      return 'attach'
    case 'Geolocation':
      return 'geolocation'
    case 'Table MultiSelect':
      return 'table-multiselect'
    case 'Link':
      return 'link'
    case 'Dynamic Link':
      return 'dynamic-link'
    case 'Autocomplete':
      return 'autocomplete'
    case 'JSON':
      return 'json'
    default:
      return 'text'
  }
})

const isImageField = computed(() => props.field.fieldtype === 'Attach Image')
const isUserLink = computed(() => props.field.fieldtype === 'Link' && props.field.options === 'User')

// Rating stores/reads a 0-1 fraction (e.g. 0.6 for 3/5 stars) - Frappe
// desk's own Rating control does the same 5-star-scale conversion under
// the hood. frappe-ui's Rating component itself works in whole stars
// (0-5, via rating_from), so the conversion happens at this boundary
// rather than changing what's actually stored, keeping the stored value
// compatible with however a real Frappe desk form would read/write it.
const ratingValue = computed(() => Math.round((props.modelValue || 0) * 5))

// Duration is stored as a single integer count of seconds (confirmed in
// frappe/utils/data.py's format_duration) - segmented into Days/Hours/
// Min/Sec here only for editing, matching Frappe desk's own Duration
// control's segmented input, then recombined back to one integer on
// every keystroke so the stored value is always the same shape a real
// Frappe form would write.
const DURATION_UNITS = [
  { key: 'days', label: 'Days', seconds: 86400 },
  { key: 'hours', label: 'Hours', seconds: 3600 },
  { key: 'minutes', label: 'Min', seconds: 60 },
  { key: 'seconds', label: 'Sec', seconds: 1 },
]
function segmentsFromTotal(totalSeconds) {
  let remaining = Math.max(0, Number(totalSeconds) || 0)
  return DURATION_UNITS.map((unit) => {
    const value = Math.floor(remaining / unit.seconds)
    remaining -= value * unit.seconds
    return { ...unit, value }
  })
}
const durationSegments = computed(() => segmentsFromTotal(props.modelValue))

// Reads props.modelValue directly (via segmentsFromTotal), not the
// durationSegments computed above, and only once per call - filling in
// the other three segments' current values from that single fresh read.
// Deriving them from durationSegments.value instead used to reuse the
// same stale snapshot across several rapid segment edits in the same
// render tick (confirmed live: scripted Days/Hours/Min/Sec updates fired
// back-to-back landed as just "Sec=4", each earlier segment's emit
// overwritten because the next call's `durationSegments.value` hadn't
// picked up the previous emit's new modelValue yet) - a real risk for any
// user tabbing through the four inputs quickly, not just a scripted
// test's speed.
function setDurationSegment(key, rawValue) {
  const value = Math.max(0, Number(rawValue) || 0)
  const current = segmentsFromTotal(props.modelValue)
  const totalSeconds = DURATION_UNITS.reduce((sum, unit) => {
    const segValue = unit.key === key ? value : current.find((s) => s.key === unit.key).value
    return sum + segValue * unit.seconds
  }, 0)
  emit('update:modelValue', totalSeconds)
}

// A JSON field stores its value as a plain string (the raw JSON text, not
// a parsed object - same as how Frappe desk's own Code/JSON control
// works), so the textarea binds directly to it with no
// serialize/deserialize step. This only checks the text is parseable
// JSON and surfaces that as the field's description (replacing whatever
// static description it had) - not a full schema validator, just "is
// this valid JSON at all" the same sanity check Desk's own Code field
// gives for a JSON-fieldtype field.
const jsonError = computed(() => {
  const value = props.modelValue
  if (!value) return ''
  try {
    JSON.parse(value)
    return ''
  } catch (e) {
    return `Invalid JSON: ${e.message}`
  }
})

// Dynamic Link's `options` isn't a doctype name (unlike a plain Link) -
// it names another field on this same document that itself holds the
// target doctype (Frappe's own "Dynamic Link" convention, e.g.
// reference_doctype naming the doctype and reference_name being the
// Dynamic Link field pointing into it). Resolved here from
// siblingValues - the exact same "read a sibling field's live value"
// mechanism link_filters' eval:doc.X already uses below - and handed to
// LinkField as a synthetic field object with that resolved doctype as
// its `options`, so LinkField itself needs no Dynamic-Link-specific
// branch; it only ever deals in plain Link fields.
const dynamicLinkDoctype = computed(() => props.siblingValues[props.field.options])
const dynamicLinkField = computed(() => ({ ...props.field, options: dynamicLinkDoctype.value }))

// FormControl/Combobox's own `disabled` prop applies frappe-ui's built-in
// disabled variant (bg-surface-gray-1, border-transparent, muted text) on
// every control type (TextInput, Select, Combobox all do this the same
// way), matching Frappe desk's own `.like-disabled-input` convention.
// Desk's own page canvas is white, so that gray fill reads clearly there -
// this app's page background (AppLayout.vue's bg-gray-50) is the *same*
// gray, so a disabled field with no border became nearly indistinguishable
// from the page around it. A thin border - not needed in Desk, needed
// here - keeps every disabled control visible without otherwise changing
// frappe-ui's disabled look. `[data-slot=trigger]` (no tag restriction)
// covers both Select's own trigger (a <button>) and LinkField.vue's
// Combobox trigger (a plain element in its "input" trigger mode, not a
// button), which reads this same class off its own wrapper div.
const choiceOptions = computed(() => (props.field.options || '').split('\n').map((o) => o.trim()).filter(Boolean))
const toggleChoice = (o) => {
  const cur = chosenChoices.value
  const next = cur.includes(o) ? cur.filter((v) => v !== o) : choiceOptions.value.filter((v) => v === o || cur.includes(v))
  emit('update:modelValue', next.join('\n'))
}
const chosenChoices = computed(() => String(props.modelValue || '').split('\n').map((v) => v.trim()).filter(Boolean))

const isReadOnly = computed(() => !!props.field.read_only || props.readOnly)
const readOnlyClass = computed(() =>
  isReadOnly.value
    ? '[&_input]:border [&_input]:border-gray-200 [&_textarea]:border [&_textarea]:border-gray-200 [&_[data-slot=trigger]]:border [&_[data-slot=trigger]]:border-gray-200 dark:[&_input]:border-gray-700 dark:[&_textarea]:border-gray-700 dark:[&_[data-slot=trigger]]:border-gray-700'
    : '',
)

const fileName = computed(() => {
  if (!props.modelValue) return ''
  try {
    return decodeURIComponent(props.modelValue.split('/').pop())
  } catch {
    return props.modelValue.split('/').pop()
  }
})

// A leading blank line in a Select field's options (Frappe's own doctype-
// editor convention for "this field can be cleared/left unset") used to
// only add a blank/"Select option" entry when the field's own `options`
// string happened to start with one - a per-field, per-doctype-author
// choice, not something every Select actually had. Now unconditional
// (always unshifted, dedup'd against a hand-authored blank line so it
// never appears twice) - every Select gets a real way back to "no
// value", including a required one (an empty selection just can't be
// *saved*; the field itself can still always be cleared while editing,
// same as a Link field's own "-" option below and IndiaGeoField's).
const selectOptions = computed(() => {
  const raw = props.field.options || ''
  const lines = raw.split('\n').map((v) => v.trim())
  const opts = lines.filter(Boolean).map((v) => ({ label: OPERATOR_LABELS[v] && conditionPart.value ? OPERATOR_LABELS[v] : v, value: v }))
  opts.unshift({ label: 'Select option', value: '' })
  return opts
})

// A "Links to ..." hint in the description used to be the whole story for
// Link fields (a plain text input, no picker at all) - LinkField.vue now
// gives them a real dropdown, but the hint still adds useful context there
// too. This is a fallback only: a field with its own real `description`
// (e.g. Data Collector's "Set automatically to whoever creates this
// record.") always wins, since that's more useful than a generic "Links
// to <doctype>" note - and using field.options here (the actual linked
// doctype, e.g. "User") rather than field.label avoids a misleading hint
// like "Links to Data Collector" for a field whose label was renamed away
// from its linked doctype's name.
const linkDescription = computed(() => {
  if (props.field.description) return props.field.description
  if (props.field.fieldtype === 'Link' && props.field.options) {
    return `Links to ${props.field.options}`
  }
  return undefined
})

// link_filters is Frappe's own standard DocField property (set via the
// DocType editor's "Filters" UI on a Link field) - a JSON string of
// [linkDoctype, fieldname, operator, value] tuples, where `value` can be
// "eval:doc.<fieldname>" to reference a sibling field on the same
// document/row (e.g. District's state filter). Resolving it here means the
// filter definition stays in the doctype JSON (portable to real Desk too)
// rather than being hardcoded per-field in this component.
const linkFilters = computed(() => {
  if (!props.field.link_filters) return {}
  let tuples
  try {
    tuples = JSON.parse(props.field.link_filters)
  } catch {
    return {}
  }
  const result = {}
  for (const [, fieldname, operator, rawValue] of tuples) {
    let value = rawValue
    if (typeof value === 'string' && value.startsWith('eval:doc.')) {
      value = props.siblingValues[value.slice('eval:doc.'.length)]
    } else if (typeof value === 'string' && value.startsWith('eval:parent.')) {
      // A reference to the parent form (e.g. a worker row's link to its
      // settlement's partner). If the parent value isn't set yet, filter to
      // nothing rather than dropping the filter and listing every record.
      value = props.parentValues?.[value.slice('eval:parent.'.length)] || '\u0000none'
    }
    result[fieldname] = operator === '=' ? value : [operator, value]
  }
  return result
})

// Format validators (phone/email/pincode/etc. - see utils/validation.js)
// are matched generically by fieldname convention rather than per-doctype
// wiring, so every doctype's phone_no/phone_number field gets the same
// check for free. Shown only after the field has actually been blurred at
// least once (`touched`) - surfacing "Phone number must be exactly 10
// digits" before the user has typed anything would just be noise.
const validator = getValidatorForField(props.field)
const touched = ref(false)
const validationError = computed(() => (validator ? validator(props.modelValue) : ''))
</script>
