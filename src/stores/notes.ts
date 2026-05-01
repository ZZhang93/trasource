import { defineStore } from 'pinia'
import { ref } from 'vue'
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

export const useNotesStore = defineStore('notes', () => {
  const notes = ref<Note[]>([])
  const currentNote = ref<Note | null>(null)
  const loading = ref(false)
  const saving = ref(false)

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

  async function saveNote(id: number, data: {
    title?: string
    content_md?: string
    tags?: string
  }): Promise<Note> {
    saving.value = true
    try {
      const updated = await api.put<Note>(`/api/notes/${id}`, data)
      const idx = notes.value.findIndex(n => n.id === id)
      if (idx >= 0) notes.value[idx] = updated
      if (currentNote.value?.id === id) currentNote.value = updated
      return updated
    } finally {
      saving.value = false
    }
  }

  async function deleteNote(id: number) {
    await api.delete(`/api/notes/${id}`)
    notes.value = notes.value.filter(n => n.id !== id)
    if (currentNote.value?.id === id) currentNote.value = null
  }

  return {
    notes, currentNote, loading, saving,
    fetchNotes, createNote, saveNote, deleteNote,
  }
})
