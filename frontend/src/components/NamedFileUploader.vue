<script>
// frappe-ui's FileUploader for photos, with two additions:
//  - the chosen file is stored under `fileName` (its extension kept), e.g. SET0013-19Nov.jpg;
//  - with no connection the photo is kept on the phone (see data/offlinePhoto.js) instead of failing.
// It emits `success` with { file_url } either way: a stored file's link, or the photo kept on the phone.
import { FileUploader, FileUploadHandler } from 'frappe-ui'
import { uploadOrKeep } from '@/data/offlinePhoto'

export function renameFile(file, fileName) {
  if (!fileName || !file) return file
  const dot = file.name.lastIndexOf('.')
  const ext = dot > 0 ? file.name.slice(dot).toLowerCase() : '.jpg'
  return new File([file], `${fileName}${ext}`, { type: file.type, lastModified: file.lastModified })
}

export default {
  name: 'NamedFileUploader',
  extends: FileUploader,
  props: {
    fileName: { type: String, default: null },
  },
  methods: {
    async uploadFile(file) {
      this.error = null
      this.uploaded = 0
      this.total = 0
      this.uploading = true
      try {
        const fileUrl = await uploadOrKeep(renameFile(file, this.fileName), (named) => {
          const uploader = new FileUploadHandler()
          uploader.on('progress', (data) => {
            this.uploaded = data.uploaded
            this.total = data.total
          })
          return uploader.upload(named, this.uploadArgs || {})
        })
        this.finishedUploading = true
        this.$emit('success', { file_url: fileUrl })
      } catch (error) {
        this.error = error?.message || 'Error Uploading File'
      } finally {
        this.uploading = false
      }
    },
  },
}
</script>
