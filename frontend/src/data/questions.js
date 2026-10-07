// Questions from the Question Bank, asked on a form without any field being added to its doctype.
// A question is shown like a field; its answer is one row in the record's "Question Answer" table.
// The rules here mirror janadhikara/questions.py (which checks them again when the record is saved).
import { reactive } from 'vue'
import { call } from 'frappe-ui'
import { localRows } from '@/data/offlinePack'

const cache = reactive({}) // doctype -> [question]
const loading = {}

export const questionsFor = (doctype) => cache[doctype] || []

// Natural order for numbers like 2, 10, 4.2
const byNumber = (a, b) => String(a.question_no).localeCompare(String(b.question_no), undefined, { numeric: true })

export async function loadQuestions(doctype) {
  if (!doctype) return []
  if (loading[doctype]) return loading[doctype]
  loading[doctype] = (async () => {
    let list = null
    try {
      const res = await call('janadhikara.questions.get_questions', { doctype })
      list = res?.message ?? res
    } catch {
      // No connection: the downloaded offline copy, if there is one.
      list = (await localRows('Question Bank', { for_doctype: doctype }))?.filter((q) => q.enabled !== 0) || []
    }
    cache[doctype] = (list || []).slice().sort(byNumber)
    delete loading[doctype]
    return cache[doctype]
  })()
  return loading[doctype]
}

export const answersMap = (rows) => Object.fromEntries((rows || []).map((r) => [r.question, r.answer || '']))

function compare(actual, operator, expected) {
  const text = actual == null ? '' : String(actual).trim()
  if (operator === 'is set') return !!text
  if (operator === 'is not set') return !text
  if (operator === 'contains') return text.split('\n').map((v) => v.trim()).includes(String(expected || '').trim())
  if (operator === '!=') return text !== (expected || '')
  return text === (expected || '')
}

// A condition on a field of this form's doctype. One on another doctype can't be checked here.
function fieldCondition(q, prefix, values, doctype) {
  const target = q[`${prefix}_doctype`]
  if (!target || target !== doctype) return true
  return compare(values?.[q[`${prefix}_field`]], q[`${prefix}_operator`] || '=', q[`${prefix}_value`])
}

export function isShown(q, values, answers, doctype) {
  if (!fieldCondition(q, 'show_if', values, doctype)) return false
  if (!fieldCondition(q, 'section_show_if', values, doctype)) return false
  if (q.section_depends_on_question && !compare(answers[q.section_depends_on_question], '=', q.section_depends_on_answer)) return false
  if (q.depends_on_question) {
    return compare(answers[q.depends_on_question], q.depends_on_operator || '=', q.depends_on_answer)
  }
  return true
}

// Mandatory questions that are shown and still unanswered: ["3. Monthly rent", ...]
export function missingAnswers(doctype, values) {
  const answers = answersMap(values?.question_answers)
  return questionsFor(doctype)
    .filter((q) => q.is_mandatory && isShown(q, values, answers, doctype) && !String(answers[q.name] || '').trim())
    .map((q) => `${q.question_no}. ${q.question}`)
}
