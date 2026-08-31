const PROJECT_KEY = 'verigate_selected_project'

export function chooseProject(projects) {
  const remembered = localStorage.getItem(PROJECT_KEY)
  return projects.some((project) => project.id === remembered) ? remembered : projects[0]?.id || ''
}

export function rememberProject(projectId) {
  if (projectId) localStorage.setItem(PROJECT_KEY, projectId)
  else localStorage.removeItem(PROJECT_KEY)
}
