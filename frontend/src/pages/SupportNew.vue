<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-semibold text-ink-gray-9 sm:text-xl">{{ t('New ticket') }}</h1>
        <p class="mt-0.5 text-sm text-ink-gray-5">{{ t('Tell the team what you need. You will be notified when they reply.') }}</p>
      </template>
      <template #actions>
        <div class="hidden items-center gap-2 sm:flex">
          <Button variant="subtle" @click="router.push({ name: 'SupportDesk' })">{{ t('Cancel') }}</Button>
          <Button variant="solid" :loading="saving" @click="submit">{{ t('Submit ticket') }}</Button>
        </div>
      </template>
    </PageHeader>

    <form class="mx-auto max-w-3xl space-y-5 pb-6" @submit.prevent="submit">
      <!-- What is it about: four big tiles that are easy to tap -->
      <fieldset>
        <legend class="mb-2 text-sm font-medium text-ink-gray-7">{{ t('What is this about?') }}</legend>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <button
            v-for="kind in kinds"
            :key="kind.value"
            type="button"
            class="flex min-h-[4.5rem] flex-col items-start gap-1.5 rounded-xl border p-3 text-left transition-colors"
            :class="form.ticket_type === kind.value ? 'border-ink-gray-9 bg-surface-gray-2 ring-1 ring-ink-gray-9' : 'hover:bg-surface-gray-1 dark:border-gray-700'"
            :aria-pressed="form.ticket_type === kind.value"
            @click="form.ticket_type = kind.value"
          >
            <FeatherIcon :name="kind.icon" class="h-5 w-5 text-ink-gray-7" />
            <span class="text-sm font-medium leading-tight text-ink-gray-9">{{ t(kind.value) }}</span>
          </button>
        </div>
      </fieldset>

      <FormControl v-model="form.subject" type="text" :label="t('Subject')" :placeholder="t('A short summary')" required />
      <div>
        <FormControl v-model="form.description" type="textarea" :rows="6" :label="t('Describe it')" :placeholder="hint" required />
        <p class="mt-1 text-xs text-ink-gray-5">{{ hint }}</p>
      </div>

      <fieldset>
        <legend class="mb-2 text-sm font-medium text-ink-gray-7">{{ t('Priority') }}</legend>
        <div class="grid grid-cols-4 gap-1 rounded-lg bg-surface-gray-2 p-1">
          <button v-for="p in supportOptions?.priorities || []" :key="p" type="button" class="rounded-md px-2 py-2 text-sm transition-colors" :class="form.priority === p ? 'bg-surface-white font-medium text-ink-gray-9 shadow-sm' : 'text-ink-gray-6'" :aria-pressed="form.priority === p" @click="form.priority = p">{{ t(p) }}</button>
        </div>
      </fieldset>

      <div class="grid gap-4 sm:grid-cols-2">
        <FormControl v-model="form.reference_doctype" type="select" class="[&_[data-slot=trigger]]:w-full" :label="t('Which form? (optional)')" :options="formOptions" />
        <FormControl v-model="form.reference_record" type="text" :label="t('Record ID (optional)')" :placeholder="t('For example HYD-HH0001')" :disabled="!form.reference_doctype" />
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-ink-gray-7">{{ t('Screenshot or file (optional)') }}</label>
        <label class="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed px-4 py-3 text-sm text-ink-gray-6 hover:bg-surface-gray-1 dark:border-gray-700">
          <FeatherIcon name="paperclip" class="h-5 w-5 flex-shrink-0" />
          <span class="min-w-0 flex-1 truncate">{{ file ? file.name : t('Tap to choose a file') }}</span>
          <button v-if="file" type="button" class="text-ink-gray-5 hover:text-ink-gray-8" :aria-label="t('Remove')" @click.prevent="file = null"><FeatherIcon name="x" class="h-4 w-4" /></button>
          <input type="file" accept="image/*,.pdf,.xlsx,.docx" class="sr-only" @change="file = $event.target.files[0] || null" />
        </label>
      </div>

      <ErrorMessage v-if="error" :message="error" />
    </form>

    <!-- On a phone the actions stay in reach at the bottom -->
    <div class="sticky bottom-[calc(var(--mobile-nav-h,56px)-5rem)] z-10 -mx-4 -mb-[calc(5rem-var(--mobile-nav-h,56px))] flex gap-2 border-t bg-surface-white px-4 py-3 dark:border-gray-800 sm:hidden">
      <Button class="flex-1" size="md" variant="subtle" @click="router.push({ name: 'SupportDesk' })">{{ t('Cancel') }}</Button>
      <Button class="flex-[2]" size="md" variant="solid" :loading="saving" @click="submit">{{ t('Submit ticket') }}</Button>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, FormControl, ErrorMessage, FeatherIcon, toast } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import { createTicket, loadSupportOptions, supportOptions, uploadAttachment } from '@/data/support'
import { flatModuleItems } from '@/data/modules'
import { setPageTitle } from '@/data/pageTitle'
import { t } from '@/utils/translate'

setPageTitle('New ticket')
const router = useRouter()
const form = reactive({ ticket_type: 'Question', priority: 'Medium', subject: '', description: '', reference_doctype: '', reference_record: '' })
const file = ref(null)
const saving = ref(false)
const error = ref('')

const HINTS = {
  'Change Request': 'What should change, on which form, and why it is needed.',
  'New Implementation': 'What you want built, who will use it and what it should record.',
  'Bug / Issue': 'What you did, what you expected and what happened instead.',
  Question: 'What you would like to know.',
}
const hint = computed(() => t(HINTS[form.ticket_type] || ''))
const kinds = [
  { value: 'Change Request', icon: 'edit-3' },
  { value: 'New Implementation', icon: 'plus-square' },
  { value: 'Bug / Issue', icon: 'alert-triangle' },
  { value: 'Question', icon: 'help-circle' },
]
const formOptions = computed(() => [
  { label: t('Not about a form'), value: '' },
  ...flatModuleItems.value.filter((i) => i.doctype_name).map((i) => ({ label: i.label || i.doctype_name, value: i.doctype_name })),
])

async function submit() {
  error.value = ''
  if (!form.subject.trim() || !form.description.trim()) {
    error.value = t('Add a subject and a description.')
    return
  }
  saving.value = true
  try {
    const attachment = file.value ? await uploadAttachment(file.value) : null
    const created = await createTicket({ ...form, attachment })
    toast.success(t('Ticket raised'))
    router.replace({ name: 'SupportTicket', params: { name: created.name } })
  } catch (e) {
    error.value = String(e?.messages?.[0] || e?.message || t('The ticket could not be raised.')).replace(/<[^>]+>/g, '')
  } finally {
    saving.value = false
  }
}
onMounted(loadSupportOptions)
</script>
