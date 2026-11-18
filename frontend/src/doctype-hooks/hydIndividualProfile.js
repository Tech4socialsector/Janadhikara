// HYD Individual Profile: the age follows the date of birth, the person's ID and sex come from the household roster, and
// the signed-in worker is filled in. (The household's settlement and partner follow the chosen household on the server.)
import { call } from 'frappe-ui'
import { session } from '@/data/session'

// Age (completed years) follows the date of birth, as it does on the server.
function ageFromDob(dob) {
  const born = new Date(dob)
  if (!dob || Number.isNaN(born.getTime())) return null
  const now = new Date()
  let age = now.getFullYear() - born.getFullYear()
  if (now.getMonth() < born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() < born.getDate())) age -= 1
  return Math.max(0, age)
}

// The roster of the chosen household, kept while the form is open: [{ member_name, uin, gender }]
let roster = []
let rosterOf = ''
const SEX = { Male: 'Male', Female: 'Female', Other: 'Others' }

async function loadRoster(values) {
  if (!values.household || values.household === rosterOf) return
  rosterOf = values.household
  try {
    const res = await call('frappe.client.get', { doctype: 'HYD Household Profile', name: values.household })
    roster = (res?.message ?? res)?.household_roster || []
  } catch {
    roster = [] // offline or no access: the ID can be typed
  }
  matchRoster(values)
}

// When the name matches a roster member, take the member's ID (and sex) from the roster - only into empty fields.
function matchRoster(values) {
  const name = (values.member_name || '').trim().toLowerCase()
  if (!name) return
  const row = roster.find((r) => (r.member_name || '').trim().toLowerCase() === name)
  if (!row) return
  if (!values.individual_id && row.uin) values.individual_id = row.uin
  if (!values.sex && SEX[row.gender]) values.sex = SEX[row.gender]
}

export function onLoad(values) {
  rosterOf = ''
  roster = []
  if (!values.assigned_worker && session.user) values.assigned_worker = session.user
  if (values.date_of_birth) values.age = ageFromDob(values.date_of_birth)
  loadRoster(values)
}

export function onFieldChange(fieldname, values) {
  if (fieldname === 'date_of_birth') values.age = ageFromDob(values.date_of_birth)
  if (fieldname === 'household') loadRoster(values)
  if (fieldname === 'member_name') matchRoster(values)
}
