export type User = { id: string; email: string; role: 'ADMIN'|'EDITOR'|'VIEWER'; workspace_id: string }
export type Document = { id: string; original_filename: string; status: string; file_size: number; error_message: string|null; created_at: string }
export type Citation = { source_id: string; document_name: string; page_number: number|null; section_title: string|null; excerpt: string }
export type Message = { id?: string; role: 'user'|'assistant'; content: string; citations: Citation[] }

export function csrf() { return decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('rag_csrf='))?.split('=').slice(1).join('=') || '') }
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch('/api/v1' + path, { credentials: 'same-origin', ...options, headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(options.method && options.method !== 'GET' ? { 'X-CSRF-Token': csrf() } : {}), ...options.headers } })
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || `Request failed (${response.status})`) }
  return response.status === 204 ? undefined as T : response.json()
}

export function upload(file: File, onProgress: (percent: number) => void): Promise<Document> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest(); xhr.open('POST', '/api/v1/documents/upload'); xhr.withCredentials = true
    xhr.setRequestHeader('X-CSRF-Token', csrf())
    xhr.upload.onprogress = event => { if (event.lengthComputable) onProgress(Math.round(event.loaded * 100 / event.total)) }
    xhr.onload = () => { try { const data = JSON.parse(xhr.responseText); if (xhr.status >= 200 && xhr.status < 300) resolve(data); else reject(new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || 'Upload failed')) } catch { reject(new Error('Upload failed')) } }
    xhr.onerror = () => reject(new Error('Network error'))
    const form = new FormData(); form.append('file', file); xhr.send(form)
  })
}
