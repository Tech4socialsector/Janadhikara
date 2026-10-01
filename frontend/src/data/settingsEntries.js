import { useCall } from 'frappe-ui'

// Settings dialog entries the logged-in user's role permissions allow,
// resolved server-side (janadhikara.api.get_settings_entries) so the dialog
// never shows a tab the user can't actually open.
//
// Shape: [{ key, doctype, label, group, icon, description, is_single,
//           can_write, can_create, desk_route, count }]
export const settingsEntriesResource = useCall({
  url: '/api/v2/method/janadhikara.api.get_settings_entries',
  method: 'GET',
  cacheKey: 'janadhikara-settings-entries',
})

export function findSettingsEntryByRoute(routeSlug) {
  return (settingsEntriesResource.data || []).find((e) => e.desk_route === routeSlug)
}
