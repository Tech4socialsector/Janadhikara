// Individual Profile: ticking "Consent Given" first shows what the person is
// agreeing to (DPDP Act, 2023). The worker must confirm they explained it;
// cancelling un-ticks the box, so consent is never recorded by accident.

const NOTICE = {
  title: 'Consent under the DPDP Act',
  intro: 'Before you record consent, explain the following to the person (or their guardian) in a language they understand:',
  bullets: [
    { icon: 'file-text', text: 'What we collect: their entitlement details (schemes, cards) and identity documents, only for this programme.' },
    { icon: 'target', text: 'Why: to help them get the schemes, documents and services they are entitled to - nothing else.' },
    { icon: 'users', text: 'Who sees it: only authorised staff of the partner organisation and the programme. It is not sold or shared for any other purpose.' },
    { icon: 'toggle-right', text: 'It is optional: they can say no, and still receive other support.' },
    { icon: 'rotate-ccw', text: 'They can withdraw consent at any time. After that, these details cannot be added or changed.' },
    { icon: 'user-check', text: 'They can ask to see, correct or erase their data, and can complain to the Data Protection Board of India.' },
    { icon: 'shield', text: 'For a child or a person with a disability, consent must come from the parent or lawful guardian.' },
  ],
  confirmLabel: 'I have explained this',
}

export function onFieldChange(fieldname, values, ctx) {
  if (fieldname !== 'consent_given' || !values.consent_given || !ctx.confirmNotice) return
  ctx.confirmNotice({
    ...NOTICE,
    onCancel: () => {
      values.consent_given = 0
    },
  })
}
