// Child tables whose rows are made from another doctype's records: the roster of a household is filled in
// by the Individual Profiles (server side: sync_roster), so a row is opened, and a member added, from the profile.
export const PROFILE_ROWS = {
  'HYD Household Member': { doctype: 'HYD Individual Profile', link: 'individual_profile', parentField: 'household' },
}
