// A photo taken with no connection can't be uploaded. It is kept in the form itself as a data URL
// (data:image/jpeg;base64,...), so it is saved on the phone with the record (encrypted, like the rest of
// it) and goes up with the record when it is synced; the server turns it into a stored file then
// (janadhikara/photo_names.py). It is made smaller first, so a record with several photos stays light.
import { serverReachable, workOffline } from '@/data/connection'
import { isNetworkError } from '@/data/offlineQueue'

const MAX_SIDE = 1600
const QUALITY = 0.8

export const isDevicePhoto = (value) => typeof value === 'string' && value.startsWith('data:image/')

export async function photoToDataUrl(file) {
  const url = URL.createObjectURL(file)
  try {
    const img = await new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = reject
      image.src = url
    })
    const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(img.naturalWidth * scale)
    canvas.height = Math.round(img.naturalHeight * scale)
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', QUALITY)
  } finally {
    URL.revokeObjectURL(url)
  }
}

// Upload the photo, or - with no (usable) connection - keep it on the phone.
// Returns what the field should hold: the stored file's link, or the photo itself.
export async function uploadOrKeep(file, upload) {
  if (workOffline()) return photoToDataUrl(file)
  try {
    return (await upload(file)).file_url
  } catch (error) {
    if (isNetworkError(error) || !(await serverReachable(3000))) return photoToDataUrl(file)
    throw error
  }
}
