import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'

export interface Project {
  name: string
  description: string
  created_at: string
  updated_at: string
  file_count: number
  record_count: number
  files: string[]
  shared_files: string[]
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProjectName = ref<string>('')
  const loading = ref(false)

  const currentProject = computed(() =>
    projects.value.find(p => p.name === currentProjectName.value) || null
  )

  async function fetchProjects() {
    loading.value = true
    try {
      const data = await api.get<Project[]>('/api/projects')
      projects.value = data
      // 自动选择第一个项目
      if (!currentProjectName.value && data.length > 0) {
        currentProjectName.value = data[0].name
      }
    } catch (e) {
      console.error('Failed to fetch projects:', e)
    } finally {
      loading.value = false
    }
  }

  async function createProject(name: string, description: string = '') {
    const project = await api.post<Project>('/api/projects', { name, description })
    projects.value.unshift(project)
    currentProjectName.value = project.name
    return project
  }

  async function deleteProject(name: string) {
    await api.delete(`/api/projects/${encodeURIComponent(name)}`)
    projects.value = projects.value.filter(p => p.name !== name)
    if (currentProjectName.value === name) {
      currentProjectName.value = projects.value[0]?.name || ''
    }
  }

  function selectProject(name: string) {
    currentProjectName.value = name
  }

  return {
    projects,
    currentProjectName,
    currentProject,
    loading,
    fetchProjects,
    createProject,
    deleteProject,
    selectProject,
  }
})
