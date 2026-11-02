const roles = ['owner', 'manager', 'qa_lead', 'tester', 'developer', 'viewer']

const capabilities = [
  ['View project data', ['owner', 'manager', 'qa_lead', 'tester', 'developer', 'viewer']],
  ['Run verifications', ['owner', 'manager', 'qa_lead', 'tester']],
  ['Manage test cases and suites', ['owner', 'manager', 'qa_lead']],
  ['Manage project settings', ['owner', 'manager']],
  ['Manage project members', ['owner', 'manager']],
]

export function RoleCapabilitiesPage() {
  return (
    <main className="library-page">
      <section className="library-heading">
        <div>
          <p className="eyebrow">Workspace governance</p>
          <h2>Role capabilities</h2>
          <p>These project permissions are enforced for every API action.</p>
        </div>
      </section>
      <section className="report-panel capability-matrix">
        <div className="capability-table" role="table">
          <div className="capability-row capability-header" role="row">
            <span>Capability</span>
            {roles.map((role) => <span key={role}>{role.replace('_', ' ')}</span>)}
          </div>
          {capabilities.map(([capability, allowed]) => (
            <div className="capability-row" role="row" key={capability}>
              <strong>{capability}</strong>
              {roles.map((role) => <span key={role} aria-label={`${role}: ${allowed.includes(role) ? 'allowed' : 'not allowed'}`}>{allowed.includes(role) ? '✓' : '—'}</span>)}
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
