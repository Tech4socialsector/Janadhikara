// The explanation shown when a worker ticks a DPDP consent box (Digital Personal Data Protection Act, 2023).
// The worker must confirm they explained it; cancelling un-ticks the box, so consent is never recorded by accident.

// Notice content follows the Digital Personal Data Protection Act, 2023 and the DPDP Rules, 2025
// (notified 13 November 2025): who is asking, what is collected, the specific purpose, how consent is
// withdrawn, the person's rights, and how to complain to the Data Protection Board of India.
const TITLE = 'Consent under the DPDP Act, 2023 and DPDP Rules, 2025'

const COMMON = [
  { icon: 'target', text: 'Why: only to help them get the schemes, documents and services they are entitled to - nothing else.' },
  { icon: 'users', text: 'Who sees it: only authorised staff of the partner organisation and the programme. It is not sold or shared for any other purpose.' },
  { icon: 'toggle-right', text: 'Free choice: giving consent is voluntary. They can say no and still receive other support.' },
  { icon: 'rotate-ccw', text: 'Withdrawal: they can withdraw consent at any time, as easily as it was given. After that, the record can no longer be changed and the data is erased once the purpose is over.' },
  { icon: 'clock', text: 'Retention: the data is kept only as long as it is needed for this purpose.' },
  { icon: 'user-check', text: 'Their rights: to see, correct, update or erase their data, to nominate a person to act for them, and to get their grievance answered. If it is not resolved, they can complain to the Data Protection Board of India.' },
]

export const HOUSEHOLD_NOTICE = {
  title: TITLE,
  intro: 'Before you record consent, explain the following to the respondent in a language they understand:',
  bullets: [
    { icon: 'file-text', text: 'What we collect: household and housing details, contact number, caste, health and entitlement information of the family.' },
    ...COMMON,
    { icon: 'shield', text: 'For a child (under 18) or a person who cannot decide for themselves, consent must come from the parent or lawful guardian.' },
  ],
  confirmLabel: 'I have explained this',
}

export const INDIVIDUAL_NOTICE = {
  title: TITLE,
  intro: 'Before you record consent, explain the following to the person (or their parent / lawful guardian) in a language they understand:',
  bullets: [
    { icon: 'file-text', text: 'What we collect: name, date of birth, contact number, education, work, health and disability details, identity documents and scheme entitlements.' },
    ...COMMON,
    { icon: 'shield', text: 'For a child (under 18) or a person with a disability, consent must come from the parent or lawful guardian. Children\'s data is never used for tracking or targeted advertising.' },
  ],
  confirmLabel: 'I have explained this',
}

// Today's date as YYYY-MM-DD (local time), for the consent date.
export function todayString() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// onFieldChange helper: ticking "consent_given" first shows the notice. The box stays un-ticked until the
// worker confirms they explained it; closing the notice any other way leaves it un-ticked.
let confirming = false
export function confirmConsent(fieldname, values, ctx, notice) {
  if (fieldname !== 'consent_given' || !Number(values.consent_given) || !ctx?.confirmNotice) return
  if (confirming) {
    confirming = false
    return
  }
  values.consent_given = 0
  setTimeout(() => {
    ctx.confirmNotice({
      ...notice,
      onConfirm: () => {
        confirming = true
        values.consent_given = 1
        values.consent_mode = values.consent_mode || 'Verbal (recorded)'
        values.consent_date = todayString()
      },
    })
  }, 0)
}
