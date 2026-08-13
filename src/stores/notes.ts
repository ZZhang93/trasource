import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import { api } from '@/api/client'

export interface Note {
  id: number
  project_name: string
  title: string
  content_md: string
  tags: string
  created_at: string
  updated_at: string
}

export interface NoteSaveData {
  title?: string
  content_md?: string
  tags?: string
}

export interface NoteSaveResult {
  note: Note
  noteId: number
  revision: number
}

export const useNotesStore = defineStore('notes', () => {
  const notes = ref<Note[]>([])
  const currentNote = ref<Note | null>(null)
  const loading = ref(false)
  const saveCounts = reactive(new Map<number, number>())
  const saveQueues = new Map<number, Promise<void>>()
  const saving = computed(() => saveCounts.size > 0)

  function setSavePending(id: number, delta: number) {
    const next = (saveCounts.get(id) || 0) + delta
    if (next > 0) saveCounts.set(id, next)
    else saveCounts.delete(id)
  }

  function isNoteSaving(id?: number | null): boolean {
    return id != null && (saveCounts.get(id) || 0) > 0
  }

  async function fetchNotes(projectName?: string) {
    loading.value = true
    try {
      const path = projectName
        ? `/api/notes?project_name=${encodeURIComponent(projectName)}`
        : '/api/notes'
      notes.value = await api.get<Note[]>(path)
    } finally {
      loading.value = false
    }
  }

  async function createNote(data: {
    title: string
    content_md?: string
    project_name?: string
    tags?: string
  }): Promise<Note> {
    const note = await api.post<Note>('/api/notes', data)
    notes.value.unshift(note)
    currentNote.value = note
    return note
  }

  /**
   * Serialize writes per note. A slow response can no longer arrive after a
   * newer write and roll the server (or the local list) back to stale data.
   * The caller-provided revision is echoed back so the editor can decide
   * whether the response still represents its current buffer.
   */
  async function saveNote(
    id: number,
    data: NoteSaveData,
    revision = 0,
  ): Promise<NoteSaveResult> {
    const previous = saveQueues.get(id) || Promise.resolve()
    setSavePending(id, 1)

    const operation = previous
      .catch(() => undefined)
      .then(async () => {
        const updated = await api.put<Note>(`/api/notes/${id}`, data)
        const idx = notes.value.findIndex(n => n.id === id)
        if (idx >= 0) notes.value[idx] = updated

        // Mutate the existing object instead of replacing the ref. Replacing
        // it would wake NotesView's selection watcher and overwrite text typed
        // while this request was in flight.
        if (currentNote.value?.id === id) {
          Object.assign(currentNote.value, updated)
        }
        return updated
      })

    const queueTail = operation.then(() => undefined, () => undefined)
    saveQueues.set(id, queueTail)

    try {
      const note = await operation
      return { note, noteId: id, revision }
    } finally {
      setSavePending(id, -1)
      if (saveQueues.get(id) === queueTail) saveQueues.delete(id)
    }
  }

  async function flushNoteSaves(id?: number) {
    if (id != null) {
      await saveQueues.get(id)
      return
    }
    await Promise.all([...saveQueues.values()])
  }

  async function deleteNote(id: number) {
    await flushNoteSaves(id)
    await api.delete(`/api/notes/${id}`)
    notes.value = notes.value.filter(n => n.id !== id)
    if (currentNote.value?.id === id) currentNote.value = null
  }

  return {
    notes, currentNote, loading, saving,
    fetchNotes, createNote, saveNote, flushNoteSaves, isNoteSaving, deleteNote,
  }
})
