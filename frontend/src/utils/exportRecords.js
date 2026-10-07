import { toast } from 'frappe-ui'

// Download every record matching the list's filters (not only the page on screen) as CSV or Excel.
export async function exportRecords({ doctype, filters, fields, orderBy, format = 'csv', total }) {
  try {
    const params = new URLSearchParams({
      doctype,
      filters: JSON.stringify(filters || {}),
      fields: JSON.stringify(fields || ['name']),
      order_by: orderBy || '',
      file_format: format,
    })
    const response = await fetch(`/api/method/janadhikara.dashboard.export_records?${params}`, { credentials: 'same-origin' })
    if (!response.ok) throw new Error(response.status === 403 ? 'You are not allowed to export these records.' : 'The export failed.')
    const blob = await response.blob()
    const disposition = response.headers.get('content-disposition') || ''
    const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] || `${doctype.toLowerCase().replace(/ /g, '_')}.${format}`
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(link.href)
    toast.success(total != null ? `Exported ${total} record${total === 1 ? '' : 's'}` : 'Exported')
  } catch (error) {
    toast.error(error.message || 'The export failed.')
  }
}
