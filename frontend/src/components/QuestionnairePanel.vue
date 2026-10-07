<template>
  <!-- The questions asked on this form. They look like fields, but nothing is added to the
  doctype: each answer is kept as a row in the record's Question Answer table. -->
  <div>
    <div v-if="loadingQuestions" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-14 animate-pulse rounded-lg bg-surface-gray-2" />
    </div>

    <div v-else-if="!groups.length && !hasTabbed" class="text-sm text-ink-gray-5">
      No questions to answer here{{ questions.length ? ' right now.' : ' yet.' }}
    </div>

    <div v-else-if="groups.length" class="space-y-5">
      <section v-for="group in groups" :key="group.name">
        <h3 v-if="group.name" class="mb-3 text-base font-medium text-ink-gray-9">{{ group.name }}</h3>
        <div class="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <div v-for="q in group.items" :key="q.name" :class="isWide(q) ? 'sm:col-span-2' : ''">
            <label class="mb-1.5 block text-sm text-ink-gray-7">
              <span class="text-ink-gray-5">{{ q.question_no }}.</span> {{ q.question }}<span v-if="q.is_mandatory" class="text-red-500"> *</span>
            </label>
            <p v-if="q.description" class="mb-1.5 whitespace-pre-line text-p-xs text-ink-gray-5">{{ q.description }}</p>

            <!-- Pick several: a dropdown that takes more than one value -->
            <MultiSelect
              v-if="q.answer_type === 'Multi-select'"
              class="w-full [&_button]:w-full"
              :model-value="chosen(q)"
              :options="optionsOf(q).map((o) => ({ label: o, value: o }))"
              placeholder="Select options"
              @update:model-value="(value) => setAnswer(q, (value || []).join('\n'))"
            />

            <FormControl
              v-else-if="q.answer_type === 'Select' || q.answer_type === 'Yes / No'"
              type="select"
              class="[&_[data-slot=trigger]]:w-full"
              :options="selectOptions(q)"
              :model-value="answers[q.name] || ''"
              @update:model-value="setAnswer(q, $event)"
            />
            <!-- A place: "latitude, longitude" - typed, or taken from this device -->
            <div v-else-if="q.answer_type === 'Location'" class="flex items-center gap-2">
              <FormControl class="min-w-0 flex-1" type="text" placeholder="latitude, longitude" :model-value="answers[q.name] || ''" @update:model-value="setAnswer(q, $event)" />
              <Button icon-left="map-pin" :loading="locating === q.name" @click="useMyLocation(q)">My location</Button>
            </div>

            <!-- A photo: only its address is kept with the record -->
            <div v-else-if="q.answer_type === 'Photo'" class="flex items-center gap-3">
              <img v-if="answers[q.name]" :src="answers[q.name]" alt="" class="h-16 w-16 rounded-lg border border-outline-gray-1 object-cover" />
              <FileUploader file-types="image/*" :upload-args="{ private: true }" @success="(file) => setAnswer(q, file.file_url)">
                <template #default="{ uploading, progress, openFileSelector }">
                  <Button icon-left="camera" :loading="uploading" @click="openFileSelector">
                    {{ uploading ? `Uploading ${progress}%` : answers[q.name] ? 'Replace photo' : 'Add photo' }}
                  </Button>
                </template>
              </FileUploader>
              <Button v-if="answers[q.name]" variant="ghost" icon="x" tooltip="Remove photo" aria-label="Remove photo" @click="setAnswer(q, '')" />
            </div>

            <FormControl
              v-else-if="q.answer_type === 'Long Text'"
              type="textarea"
              :rows="3"
              :model-value="answers[q.name] || ''"
              @update:model-value="setAnswer(q, $event)"
            />
            <DatePicker
              v-else-if="q.answer_type === 'Date'"
              format="DD MMM YYYY"
              :model-value="answers[q.name] || ''"
              @update:model-value="setAnswer(q, $event)"
            />
            <FormControl
              v-else
              :type="q.answer_type === 'Number' ? 'number' : q.answer_type === 'Date' ? 'date' : 'text'"
              :model-value="answers[q.name] || ''"
              @update:model-value="setAnswer(q, $event)"
            />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Button, FileUploader, FormControl, DatePicker, MultiSelect, toast } from 'frappe-ui'
import { loadQuestions, questionsFor, answersMap, isShown } from '@/data/questions'

const props = defineProps({
  doctype: { type: String, required: true },
  modelValue: { type: Array, default: () => [] }, // the Question Answer rows
  parentValues: { type: Object, default: () => ({}) }, // the record being edited
  tab: { type: String, default: '' }, // show only this form tab's questions
})
const emit = defineEmits(['update:modelValue'])

const questions = computed(() => questionsFor(props.doctype))
const loadingQuestions = computed(() => !questions.value.length && !loaded.value)
const loaded = ref(false)
onMounted(async () => {
  await loadQuestions(props.doctype)
  loaded.value = true
})

const answers = computed(() => answersMap(props.modelValue))
const visible = computed(() => questions.value.filter((q) => isShown(q, props.parentValues, answers.value, props.doctype)))

// Questions put in a tab are shown on that tab of the form (see DoctypeForm), so this panel shows
// either one tab's questions (`tab` given) or the ones that are not in any tab.
const inTab = (q) => (props.tab ? q.tab_group === props.tab : !q.tab_group)
const hasTabbed = computed(() => !props.tab && questions.value.some((q) => q.tab_group))

// One block per section, in question-number order; individual questions (no section) first.
const groups = computed(() => {
  const map = new Map([['', []]])
  for (const q of visible.value.filter(inTab)) {
    const key = q.section_group || ''
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(q)
  }
  return [...map.entries()].filter(([, items]) => items.length).map(([name, items]) => ({ name, items }))
})

const isWide = (q) => ['Long Text', 'Location', 'Photo'].includes(q.answer_type)
const optionsOf = (q) => (q.options || '').split('\n').map((o) => o.trim()).filter(Boolean)
const selectOptions = (q) => [
  { label: '', value: '' },
  ...(q.answer_type === 'Yes / No' ? ['Yes', 'No'] : optionsOf(q)).map((o) => ({ label: o, value: o })),
]
const chosen = (q) => (answers.value[q.name] || '').split('\n').map((v) => v.trim()).filter(Boolean)

const locating = ref(null)
function useMyLocation(q) {
  if (!navigator.geolocation) return toast.error('This device cannot give its location.')
  locating.value = q.name
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      setAnswer(q, `${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)}`)
      locating.value = null
    },
    () => {
      toast.error('Could not get the location - allow location access and try again.')
      locating.value = null
    },
    { enableHighAccuracy: true, timeout: 15000 },
  )
}

// Writes the answer into the table: a row per answered question, none for blanks.
function setAnswer(q, value) {
  const text = value == null ? '' : String(value)
  const rows = (props.modelValue || []).filter((r) => r.question !== q.name)
  if (text.trim()) {
    rows.push({
      question: q.name,
      question_no: q.question_no,
      question_text: q.question,
      answer_type: q.answer_type,
      section_group: q.section_group || null,
      answer: text,
    })
  }
  emit('update:modelValue', rows)
}

// A question that stops being shown (its condition changed) loses its answer.
watch(
  visible,
  (shown) => {
    const keep = new Set(shown.map((q) => q.name))
    const rows = (props.modelValue || []).filter((r) => keep.has(r.question))
    if (rows.length !== (props.modelValue || []).length) emit('update:modelValue', rows)
  },
  { deep: false },
)
</script>
