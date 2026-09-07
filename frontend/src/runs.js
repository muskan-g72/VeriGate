export const runStatuses = ['pending', 'in_progress', 'completed']

// Each project/suite is read once per load. Filters reuse this snapshot.
export async function loadRuns({ listProjects, listSuites, listRuns }, onStage = () => {}) {
  onStage('projects')
  const projects = await listProjects()
  const failures = []
  async function readBranch(read, context) {
    try { return await read() }
    catch (error) {
      if (error.code === 'unauthorized') throw error
      failures.push({ ...context, message: error.message })
      return []
    }
  }
  onStage('suites')
  const suites = (await Promise.all(projects.map(async (project) => {
    const items = await readBranch(() => listSuites(project.id), { projectId: project.id, label: `${project.name}: test suites` })
    return items.map((suite) => ({ ...suite, project_id: project.id, project_name: project.name }))
  }))).flat()
  onStage('runs')
  const runs = (await Promise.all(suites.map(async (suite) => {
    const items = await readBranch(() => listRuns(suite.id), { projectId: suite.project_id, suiteId: suite.id, label: `${suite.project_name} / ${suite.name}: runs` })
    return items.map((run) => ({ ...run, project_id: suite.project_id, project_name: suite.project_name, test_suite_id: suite.id, suite_name: suite.name }))
  }))).flat()
  return { projects, suites, runs, failures }
}

export function filterRuns(runs, { projectId = '', status = '', search = '', sort = 'newest' } = {}) {
  const query = search.trim().toLowerCase()
  return runs.filter((run) => (!projectId || run.project_id === projectId)
    && (!status || run.status === status)
    && (!query || run.name.toLowerCase().includes(query) || run.suite_name.toLowerCase().includes(query)))
    .sort((a, b) => {
      const difference = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      return (sort === 'oldest' ? difference : -difference) || a.id.localeCompare(b.id)
    })
}

export function summarizeRuns(runs) {
  return runs.reduce((counts, run) => {
    counts.total += 1
    if (runStatuses.includes(run.status)) counts[run.status] += 1
    return counts
  }, { total: 0, pending: 0, in_progress: 0, completed: 0 })
}

export function runsEmptyState(data, projectId = '') {
  if (!data.projects.length) return 'projects'
  if (data.failures.some((failure) => !projectId || failure.projectId === projectId)) return 'incomplete'
  if (!data.suites.some((suite) => !projectId || suite.project_id === projectId)) return 'suites'
  if (!data.runs.some((run) => !projectId || run.project_id === projectId)) return 'runs'
  return 'filtered'
}
