import { apiFetch, apiUpload } from './client'

export function getTenant() {
  return apiFetch('/tenant')
}

export function updateTenant({ name, primaryColor, about }) {
  return apiFetch('/tenant', {
    method: 'PATCH',
    body: { name, primary_color: primaryColor || null, about: about || null },
  })
}

export function uploadLogo(file) {
  const formData = new FormData()
  formData.append('file', file)
  return apiUpload('/tenant/logo', formData)
}
