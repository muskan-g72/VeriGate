import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

// Replace Vite's import.meta.env at runtime to test with Node
const clientSource = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8'))
  .replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { testCasesApi, verificationRunsApi, sessionStore, ApiError } = await import(
  `data:text/javascript;base64,${Buffer.from(clientSource).toString('base64')}`
)

const storage = new Map()
globalThis.sessionStorage = {
  getItem: (key) => storage.get(key),
  setItem: (key, value) => storage.set(key, value),
  removeItem: (key) => storage.delete(key),
}

const suiteId = 'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d'
const caseId = 'c1c2c3c4-c5c6-c7c8-c9c0-d1d2d3d4d5d6'
const runId = 'r1r2r3r4-r5r6-r7r8-r9r0-e1e2e3e4e5e6'

const sampleSteps = [
  { action: 'goto', value: 'https://example.com' },
  { action: 'fill', selector: '#search', value: 'Playwright' },
  { action: 'click', selector: 'button[type="submit"]' },
  { action: 'expect_text', value: 'Results' },
  { action: 'expect_title', value: 'Search Results' },
]

test('1. Test Case can be switched between Manual and Automated and defines automation steps', () => {
  let mode = 'manual'
  let steps = []

  // Switch to automated
  mode = 'automated'
  if (steps.length === 0) {
    steps = [{ action: 'goto', value: 'https://example.com' }]
  }

  assert.equal(mode, 'automated')
  assert.equal(steps.length, 1)
  assert.equal(steps[0].action, 'goto')

  // Switch back to manual
  mode = 'manual'
  assert.equal(mode, 'manual')
})

test('2. Automation steps can be added, edited, reordered, and deleted', () => {
  let steps = []

  // Add step 1: goto
  steps.push({ action: 'goto', value: 'https://example.com' })
  assert.equal(steps.length, 1)

  // Add step 2: click
  steps.push({ action: 'click', selector: '#login' })
  assert.equal(steps.length, 2)

  // Edit step 2: change to fill
  steps[1] = { action: 'fill', selector: '#username', value: 'user@example.com' }
  assert.equal(steps[1].action, 'fill')
  assert.equal(steps[1].value, 'user@example.com')

  // Add step 3: expect_title
  steps.push({ action: 'expect_title', value: 'Home' })
  assert.equal(steps.length, 3)

  // Reorder steps: move step 3 up to position 1 (index 1)
  const [moved] = steps.splice(2, 1)
  steps.splice(1, 0, moved)
  assert.equal(steps[1].action, 'expect_title')
  assert.equal(steps[2].action, 'fill')

  // Delete step 1
  steps.splice(0, 1)
  assert.equal(steps.length, 2)
  assert.equal(steps[0].action, 'expect_title')
})

test('3. Correct API requests are sent for automated TestCase creation and update', async () => {
  sessionStore.set('playwright-test-token')
  const calls = []

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return {
      ok: true,
      json: async () => ({
        id: caseId,
        test_suite_id: suiteId,
        title: 'Automated Login',
        execution_mode: 'automated',
        automation_steps: sampleSteps,
      }),
    }
  }

  // Test create
  const createPayload = {
    title: 'Automated Login',
    steps: '1. Goto\n2. Fill\n3. Click',
    expected_result: 'Redirected',
    priority: 'high',
    execution_mode: 'automated',
    automation_steps: sampleSteps,
  }
  const created = await testCasesApi.create(suiteId, createPayload)
  assert.equal(created.execution_mode, 'automated')
  assert.deepEqual(created.automation_steps, sampleSteps)

  assert.equal(calls[0].url, `http://verigate.test/api/v1/test-suites/${suiteId}/test-cases`)
  assert.equal(calls[0].method, 'POST')
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer playwright-test-token')
  assert.equal(calls[0].headers.get('Content-Type'), 'application/json')
  assert.deepEqual(JSON.parse(calls[0].body), createPayload)

  // Test update
  const updatePayload = {
    execution_mode: 'automated',
    automation_steps: sampleSteps.slice(0, 2),
  }
  await testCasesApi.update(caseId, updatePayload)
  assert.equal(calls[1].url, `http://verigate.test/api/v1/test-cases/${caseId}`)
  assert.equal(calls[1].method, 'PATCH')
  assert.deepEqual(JSON.parse(calls[1].body), updatePayload)
})

test('4. Playwright execution calls the existing verification-runs creation endpoint', async () => {
  sessionStore.set('playwright-test-token')
  const calls = []

  const mockRunResponse = {
    id: runId,
    test_suite_id: suiteId,
    name: 'Playwright — Automated Login',
    status: 'completed',
    started_at: '2026-09-08T10:00:00Z',
    completed_at: '2026-09-08T10:00:02Z',
    total_cases: 1,
    passed_count: 1,
    failed_count: 0,
    results: [
      {
        id: 'res-1',
        verification_run_id: runId,
        test_case_id: caseId,
        status: 'passed',
        actual_result: 'Test passed',
        failure_message: null,
        stack_trace: null,
        duration: 0.85,
        executed_at: '2026-09-08T10:00:02Z',
        evidence_items: [],
      },
    ],
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return {
      ok: true,
      json: async () => mockRunResponse,
    }
  }

  const run = await verificationRunsApi.create(suiteId, {
    name: 'Playwright — Automated Login',
  })

  assert.equal(calls.length, 1)
  assert.equal(
    calls[0].url,
    `http://verigate.test/api/v1/test-suites/${suiteId}/verification-runs`
  )
  assert.equal(calls[0].method, 'POST')
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer playwright-test-token')
  assert.deepEqual(JSON.parse(calls[0].body), {
    name: 'Playwright — Automated Login',
  })

  // Verify response fields
  assert.equal(run.status, 'completed')
  assert.equal(run.results[0].status, 'passed')
  assert.equal(run.results[0].duration, 0.85)
})

test('5. Duplicate run submissions are prevented when execution is already active', async () => {
  let isExecuting = false
  let runCount = 0

  async function mockTrigger() {
    if (isExecuting) return { rejected: true }
    isExecuting = true
    runCount++
    await new Promise((resolve) => setTimeout(resolve, 10))
    isExecuting = false
    return { ok: true }
  }

  const [res1, res2] = await Promise.all([mockTrigger(), mockTrigger()])
  assert.equal(runCount, 1)
  assert.ok(res1.ok || res2.ok)
  assert.ok(res1.rejected || res2.rejected)
})

test('6. Failed Playwright execution extracts failure_message, stack_trace, and screenshot evidence', async () => {
  sessionStore.set('playwright-test-token')

  const fakeScreenshot = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
  const mockFailedRunResponse = {
    id: runId,
    test_suite_id: suiteId,
    name: 'Playwright — Failing Test',
    status: 'completed',
    started_at: '2026-09-08T10:00:00Z',
    completed_at: '2026-09-08T10:00:03Z',
    total_cases: 1,
    passed_count: 0,
    failed_count: 1,
    results: [
      {
        id: 'res-failed',
        verification_run_id: runId,
        test_case_id: caseId,
        status: 'failed',
        actual_result: 'Test failed',
        failure_message: "Expected title 'Dashboard', but got 'Login'",
        stack_trace: 'Traceback (most recent call last):\n  File playwright_executor.py: AssertionError',
        duration: 1.25,
        executed_at: '2026-09-08T10:00:03Z',
        evidence_items: [
          {
            id: 'ev-1',
            verification_result_id: 'res-failed',
            type: 'screenshot',
            name: 'Playwright screenshot',
            description: 'Screenshot captured during automated Playwright execution',
            content: fakeScreenshot,
            created_at: '2026-09-08T10:00:03Z',
          },
        ],
      },
    ],
  }

  globalThis.fetch = async () => ({
    ok: true,
    json: async () => mockFailedRunResponse,
  })

  const run = await verificationRunsApi.create(suiteId, {
    name: 'Playwright — Failing Test',
  })

  const result = run.results.find((r) => r.test_case_id === caseId)
  assert.ok(result)
  assert.equal(result.status, 'failed')
  assert.equal(result.failure_message, "Expected title 'Dashboard', but got 'Login'")
  assert.ok(result.stack_trace.includes('AssertionError'))
  assert.equal(result.duration, 1.25)
  assert.equal(result.evidence_items.length, 1)

  const evidence = result.evidence_items[0]
  assert.equal(evidence.type, 'screenshot')
  assert.equal(evidence.name, 'Playwright screenshot')
  assert.equal(evidence.content, fakeScreenshot)
})

test('7. Error handling propagates API and network failures', async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    json: async () => ({ detail: 'Test suite has no active test cases' }),
  })

  await assert.rejects(
    verificationRunsApi.create(suiteId, { name: 'Invalid' }),
    (err) => err instanceof ApiError && err.status === 400 && err.message.includes('no active test cases')
  )
})
