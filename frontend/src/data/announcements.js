import { useCall } from 'frappe-ui'

// Active announcements targeted at the logged-in user (by role, by specific
// user, or shown to everyone), already excluding ones they've dismissed -
// filtering happens server-side in janadhikara.api.get_active_announcements
// since the frontend never receives the user's raw role list.
//
// Shape: [{ name, title, message, announcement_type, dismissible }]
export const announcementsResource = useCall({
  url: '/api/v2/method/janadhikara.api.get_active_announcements',
  method: 'GET',
  cacheKey: 'janadhikara-active-announcements',
})

export function dismissAnnouncement(name) {
  // Optimistic local removal so the banner disappears immediately; the
  // server call records the dismissal so it stays gone on future loads.
  if (announcementsResource.data) {
    announcementsResource.data = announcementsResource.data.filter((a) => a.name !== name)
  }
  return useCall({
    url: '/api/v2/method/janadhikara.api.dismiss_announcement',
    method: 'POST',
    params: { name },
    immediate: true,
  })
}
