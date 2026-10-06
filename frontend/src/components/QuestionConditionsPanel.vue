<template>
  <!-- Settings > Question Bank: a table of display rules ("Field -> Question"), each with a "..."
  menu, and a dialog to create or change one - the same layout as Helpdesk's Field Dependencies. -->
  <div>
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <h2 class="text-lg font-semibold text-ink-gray-9">Question Display Rules</h2>
        <p class="mt-1 text-sm text-ink-gray-6">
          Show a question, or a whole section, only when a field on the form has a certain value. For example, show
          "Monthly rent" only while House Ownership is Rented.
        </p>
      </div>
      <Button variant="solid" icon-left="plus" class="flex-shrink-0" @click="openDialog()">New</Button>
    </div>

    <div class="mt-5 w-full sm:w-64">
      <FormControl type="select" :options="formFilterOptions" v-model="formFilter" />
    </div>

    <div v-if="loading" class="mt-4 space-y-2">
      <div v-for="i in 3" :key="i" class="h-12 animate-pulse rounded-lg bg-surface-gray-2" />
    </div>

    <div v-else-if="!rows.length" class="mt-10 flex flex-col items-center gap-3 py-8 text-center">
      <span class="flex h-12 w-12 items-center justify-center rounded-full bg-surface-gray-2">
        <FeatherIcon name="git-branch" class="h-5 w-5 text-ink-gray-5" />
      </span>
      <p class="text-sm font-medium text-ink-gray-8">No display rules yet</p>
      <p class="max-w-xs text-sm text-ink-gray-5">Every question is currently shown on its form. Add a rule to show one only when it is needed.</p>
      <Button icon-left="plus" @click="openDialog()">Create a rule</Button>
    </div>

    <div v-else class="mt-2">
      <div class="grid grid-cols-[minmax(0,2fr)_minmax(0,1.3fr)_8rem_2rem] gap-3 border-b border-outline-gray-2 px-2 py-2 text-xs text-ink-gray-5 max-sm:hidden">
        <span>Name</span>
        <span>Shown only while</span>
        <span>Created by</span>
        <span />
      </div>
      <div
        v-for="r in rows"
        :key="r.id"
        class="group grid grid-cols-[minmax(0,1fr)_2rem] items-center gap-3 rounded-lg border-b border-outline-gray-1 px-2 py-3 last:border-b-0 hover:bg-surface-gray-1 sm:grid-cols-[minmax(0,2fr)_minmax(0,1.3fr)_8rem_2rem]"
      >
        <div class="min-w-0">
          <p class="flex items-center gap-1.5 text-sm text-ink-gray-9">
            <span class="truncate">{{ r.fieldLabel }}</span>
            <span class="text-ink-gray-4">→</span>
            <span class="truncate">{{ r.targetLabel }}</span>
          </p>
          <p class="mt-0.5 truncate text-xs text-ink-gray-5">{{ r.form }}<template v-if="r.kind === 'section'"> · whole section</template></p>
          <p class="mt-1 text-xs text-ink-gray-7 sm:hidden">{{ r.condition }}</p>
        </div>
        <p class="truncate text-sm text-ink-gray-7 max-sm:hidden">{{ r.condition }}</p>
        <div class="flex items-center gap-2 text-sm text-ink-gray-7 max-sm:hidden">
          <Avatar size="sm" :label="userLabel(r.owner)" />
          <span class="truncate">{{ userLabel(r.owner) }}</span>
        </div>
        <Dropdown :options="menuFor(r)" placement="bottom-end">
          <Button variant="ghost" size="sm" icon="more-horizontal" />
        </Dropdown>
      </div>
    </div>

    <!-- New / edit rule -->
    <Dialog v-model="showDialog" :options="{ size: 'xl', title: 'question-rule-dialog' }">
      <template #body>
        <div v-if="draft" class="p-5 sm:p-6">
          <h3 class="text-lg font-semibold text-ink-gray-9">{{ draft.editing ? 'Edit rule' : 'New rule' }}</h3>
          <p class="mt-1 text-sm text-ink-gray-5">Choose what to show or hide, and the field value that decides it.</p>

          <div class="mt-5 space-y-4">
            <FormControl type="select" label="Form" :options="dialogFormOptions" :disabled="draft.editing" v-model="draft.form" @update:model-value="onFormChange" />

            <div v-if="draft.form">
              <div class="mb-1.5 text-xs text-ink-gray-5">Applies to</div>
              <div class="inline-flex rounded-lg bg-surface-gray-3 p-0.5 text-sm">
                <button
                  v-for="opt in [{ value: 'question', label: 'A question' }, { value: 'section', label: 'A whole section' }]"
                  :key="opt.value"
                  type="button"
                  :disabled="draft.editing"
                  class="rounded-md px-3 py-1"
                  :class="draft.kind === opt.value ? 'bg-surface-base font-medium text-ink-gray-9 shadow-sm' : 'text-ink-gray-6'"
                  @click="draft.kind = opt.value; draft.target = ''"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <FormControl
              v-if="draft.form"
              type="select"
              :label="draft.kind === 'section' ? 'Section' : 'Question'"
              :options="targetOptions"
              :disabled="draft.editing"
              v-model="draft.target"
            />

            <template v-if="draft.target">
              <p class="pt-1 text-sm font-medium text-ink-gray-8">Show it only while</p>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="sm:col-span-2">
                  <DoctypeFieldPicker
                    :field="{ label: 'Field on this form' }"
                    :doctype="draft.form"
                    :model-value="draft.field"
                    @update:model-value="draft.field = $event; draft.value = ''"
                  />
                </div>
                <FormControl type="select" label="Condition" :options="operatorOptions" v-model="draft.operator" />
                <div v-if="needsValue">
                  <LinkField
                    v-if="chosen?.fieldtype === 'Link'"
                    :field="{ label: 'Value', fieldname: 'value', options: chosen.options }"
                    :model-value="draft.value"
                    @update:model-value="draft.value = $event || ''"
                  />
                  <FormControl v-else-if="valueChoices" type="select" label="Value" :options="valueChoices" v-model="draft.value" />
                  <FormControl v-else type="text" label="Value" placeholder="e.g. Rented" v-model="draft.value" />
                </div>
              </div>

              <p v-if="preview" class="flex items-start gap-1.5 rounded-lg bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-7">
                <FeatherIcon name="info" class="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-gray-5" />
                {{ preview }}
              </p>
            </template>
            <p v-if="error" class="text-sm text-ink-red-3">{{ error }}</p>
          </div>

          <div class="mt-6 flex justify-end gap-2">
            <Button @click="showDialog = false">Cancel</Button>
            <Button variant="solid" :loading="saving" :disabled="!canSave" @click="save()">{{ draft.editing ? 'Save' : 'Create' }}</Button>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { call, toast, Avatar, Button, Dialog, Dropdown, FormControl, FeatherIcon } from 'frappe-ui'
import DoctypeFieldPicker from '@/components/DoctypeFieldPicker.vue'
import LinkField from '@/components/LinkField.vue'
import { loadDoctypeFields } from '@/data/doctypeMeta'
import { userLabel } from '@/utils/worklist'

defineProps({ entry: { type: Object, required: true } })
defineEmits(['close'])

// Stored as = / != / is set / is not set; shown in words.
const operatorOptions = [
  { label: 'is', value: '=' },
  { label: 'is not', value: '!=' },
  { label: 'has a value', value: 'is set' },
  { label: 'is empty', value: 'is not set' },
]
const OPERATOR_WORDS = Object.fromEntries(operatorOptions.map((o) => [o.value, o.label]))
const sentence = (operator, value) => {
  const needs = operator === '=' || operator === '!='
  return `${OPERATOR_WORDS[operator] || 'is'}${needs ? ` ${value}` : ''}`
}

const FIELDS = [
  'name', 'question_no', 'question', 'for_doctype', 'section_group', 'owner',
  'show_if_doctype', 'show_if_field', 'show_if_operator', 'show_if_value',
  'section_show_if_doctype', 'section_show_if_field', 'section_show_if_operator', 'section_show_if_value',
]
const questions = ref([])
const labels = ref({}) // form -> { fieldname: label }
const loading = ref(true)
const formFilter = ref('')

async function load() {
  const list = await call('frappe.client.get_list', {
    doctype: 'Question Bank',
    fields: FIELDS,
    order_by: 'for_doctype asc, question_no asc',
    limit_page_length: 2000,
  })
  questions.value = list || []
  const forms = [...new Set(questions.value.map((q) => q.for_doctype).filter(Boolean))]
  const entries = await Promise.all(
    forms.map(async (f) => [f, Object.fromEntries((await loadDoctypeFields(f)).map((x) => [x.fieldname, x.label || x.fieldname]))]),
  )
  labels.value = Object.fromEntries(entries)
  loading.value = false
}
load()

const forms = computed(() => [...new Set(questions.value.map((q) => q.for_doctype).filter(Boolean))])
const formFilterOptions = computed(() => [{ label: 'All forms', value: '' }, ...forms.value.map((f) => ({ label: f, value: f }))])
const dialogFormOptions = computed(() => [{ label: 'Choose a form', value: '' }, ...forms.value.map((f) => ({ label: f, value: f }))])
const labelOf = (form, fieldname) => labels.value[form]?.[fieldname] || fieldname
const questionTitle = (q) => `${q.question_no}. ${q.question}`

// One row per question rule, and one per section rule (a section rule is stored on every question in
// the section, so the section is listed once).
const rows = computed(() => {
  const out = []
  const seenSections = new Set()
  for (const q of questions.value) {
    if (formFilter.value && q.for_doctype !== formFilter.value) continue
    if (q.show_if_doctype) {
      out.push({
        id: `q:${q.name}`, kind: 'question', form: q.for_doctype, owner: q.owner, target: q.name,
        field: q.show_if_field, operator: q.show_if_operator || '=', value: q.show_if_value || '',
        fieldLabel: labelOf(q.for_doctype, q.show_if_field), targetLabel: questionTitle(q),
        condition: sentence(q.show_if_operator || '=', q.show_if_value),
      })
    }
    const key = `${q.for_doctype}:${q.section_group}`
    if (q.section_show_if_doctype && q.section_group && !seenSections.has(key)) {
      seenSections.add(key)
      out.push({
        id: `s:${key}`, kind: 'section', form: q.for_doctype, owner: q.owner, target: q.section_group,
        field: q.section_show_if_field, operator: q.section_show_if_operator || '=', value: q.section_show_if_value || '',
        fieldLabel: labelOf(q.for_doctype, q.section_show_if_field), targetLabel: `Section: ${q.section_group}`,
        condition: sentence(q.section_show_if_operator || '=', q.section_show_if_value),
      })
    }
  }
  return out
})

const menuFor = (r) => [
  { label: 'Edit', icon: 'edit-2', onClick: () => openDialog(r) },
  { label: 'Remove', icon: 'trash-2', theme: 'red', onClick: () => remove(r) },
]

// ---- dialog ---------------------------------------------------------------
const showDialog = ref(false)
const draft = ref(null)
const saving = ref(false)
const error = ref('')
const dialogFields = ref([])

function openDialog(row) {
  error.value = ''
  draft.value = row
    ? { editing: true, kind: row.kind, form: row.form, target: row.target, field: row.field, operator: row.operator, value: row.value }
    : { editing: false, kind: 'question', form: formFilter.value, target: '', field: '', operator: '=', value: '' }
  showDialog.value = true
}
const onFormChange = () => {
  draft.value.target = ''
  draft.value.field = ''
  draft.value.value = ''
}
watch(
  () => draft.value?.form,
  async (form) => {
    dialogFields.value = form ? await loadDoctypeFields(form) : []
  },
  { immediate: true },
)

const targetOptions = computed(() => {
  const inForm = questions.value.filter((q) => q.for_doctype === draft.value?.form)
  const blank = { label: draft.value.kind === 'section' ? 'Choose a section' : 'Choose a question', value: '' }
  if (draft.value.kind === 'section') {
    return [blank, ...[...new Set(inForm.map((q) => q.section_group).filter(Boolean))].map((s) => ({ label: s, value: s }))]
  }
  return [blank, ...inForm.map((q) => ({ label: questionTitle(q), value: q.name }))]
})
const chosen = computed(() => dialogFields.value.find((f) => f.fieldname === draft.value?.field) || null)
const needsValue = computed(() => !!draft.value?.field && ['=', '!='].includes(draft.value.operator))
// A Select's own options, or Yes/No for a tick box; null for anything free-form.
const valueChoices = computed(() => {
  const f = chosen.value
  if (f?.fieldtype === 'Check') return [{ label: 'Ticked (Yes)', value: '1' }, { label: 'Not ticked (No)', value: '0' }]
  if (f?.fieldtype === 'Select') return (f.options || '').split('\n').map((v) => v.trim()).filter(Boolean).map((v) => ({ label: v, value: v }))
  return null
})
const canSave = computed(() => !!draft.value?.target && !!draft.value?.field && (!needsValue.value || !!String(draft.value.value).trim()))
const preview = computed(() => {
  const d = draft.value
  if (!d?.field || !canSave.value) return ''
  const what = d.kind === 'section' ? `The section "${d.target}" is` : 'This question is'
  return `${what} shown only while ${labelOf(d.form, d.field)} ${sentence(d.operator, d.value)}. Otherwise it is hidden.`
})

// A section rule is saved on one of its questions; Question Bank copies it to the rest of the section.
const carrier = (kind, form, target) =>
  kind === 'section' ? questions.value.find((q) => q.for_doctype === form && q.section_group === target)?.name : target

async function write(kind, form, target, values) {
  const p = kind === 'section' ? 'section_show_if' : 'show_if'
  const fieldname = Object.fromEntries(Object.entries(values).map(([k, v]) => [`${p}_${k}`, v]))
  await call('frappe.client.set_value', { doctype: 'Question Bank', name: carrier(kind, form, target), fieldname })
}
const errorText = (err) => err?.messages?.[0]?.replace(/<[^>]+>/g, '') || err?.message || 'Something went wrong.'

async function save() {
  const d = draft.value
  saving.value = true
  error.value = ''
  try {
    await write(d.kind, d.form, d.target, {
      doctype: d.form, field: d.field, operator: d.operator, value: needsValue.value ? String(d.value).trim() : '',
    })
    toast.success('Rule saved')
    showDialog.value = false
    await load()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    saving.value = false
  }
}

async function remove(r) {
  try {
    await write(r.kind, r.form, r.target, { doctype: '', field: '', operator: '=', value: '' })
    toast.success('Rule removed')
    await load()
  } catch (err) {
    toast.error(errorText(err))
  }
}
</script>

<style>
/* This dialog opens over the Settings dialog (z-index 1050 - see SettingsDialog.vue). */
[data-dialog='question-rule-dialog'].dialog-overlay {
  z-index: 1060;
}
</style>
