import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react'

const SUPPORTED_ACTIONS = [
  { value: 'goto', label: 'Navigate (goto)', description: 'Navigate to a target URL' },
  { value: 'click', label: 'Click element', description: 'Click an element by selector' },
  { value: 'fill', label: 'Fill input', description: 'Type a value into an input field' },
  { value: 'expect_text', label: 'Assert text', description: 'Wait for and assert text appears on the page' },
  { value: 'expect_title', label: 'Assert page title', description: 'Assert the exact browser page title' },
]

export function AutomationStepBuilder({ steps = [], onChange, disabled = false }) {
  function addStep() {
    const defaultAction = steps.length === 0 ? 'goto' : 'click'
    const newStep = defaultAction === 'goto'
      ? { action: 'goto', value: '' }
      : { action: 'click', selector: '' }
    onChange([...steps, newStep])
  }

  function updateStep(index, updates) {
    const next = steps.map((step, i) => {
      if (i !== index) return step
      const merged = { ...step, ...updates }
      // Clean up fields not relevant to the new action
      if (updates.action) {
        if (updates.action === 'goto') {
          return { action: 'goto', value: merged.value || '' }
        }
        if (updates.action === 'click') {
          return { action: 'click', selector: merged.selector || '' }
        }
        if (updates.action === 'fill') {
          return { action: 'fill', selector: merged.selector || '', value: merged.value || '' }
        }
        if (updates.action === 'expect_text') {
          return { action: 'expect_text', value: merged.value || '' }
        }
        if (updates.action === 'expect_title') {
          return { action: 'expect_title', value: merged.value || '' }
        }
      }
      return merged
    })
    onChange(next)
  }

  function removeStep(index) {
    onChange(steps.filter((_, i) => i !== index))
  }

  function moveStep(index, direction) {
    const targetIndex = index + direction
    if (targetIndex < 0 || targetIndex >= steps.length) return
    const next = [...steps]
    const [moved] = next.splice(index, 1)
    next.splice(targetIndex, 0, moved)
    onChange(next)
  }

  return (
    <div className="automation-builder" aria-label="Automation step builder">
      <div className="builder-header">
        <div>
          <span className="builder-title">Playwright Steps</span>
          <span className="builder-counter">{steps.length} {steps.length === 1 ? 'step' : 'steps'}</span>
        </div>
        <button
          type="button"
          className="secondary-button add-step-button"
          onClick={addStep}
          disabled={disabled}
        >
          <Plus size={14} />
          Add step
        </button>
      </div>

      {steps.length === 0 ? (
        <div className="builder-empty">
          <p>No automation steps defined. Add the first action to execute in the browser.</p>
          <button
            type="button"
            className="secondary-button"
            onClick={addStep}
            disabled={disabled}
          >
            <Plus size={14} /> Add first step
          </button>
        </div>
      ) : (
        <ol className="step-list">
          {steps.map((step, index) => (
            <li className="step-card" key={index}>
              <div className="step-card-header">
                <span className="step-index">Step {index + 1}</span>
                <div className="step-reorder-actions">
                  <button
                    type="button"
                    className="icon-action-btn"
                    onClick={() => moveStep(index, -1)}
                    disabled={disabled || index === 0}
                    aria-label={`Move step ${index + 1} up`}
                    title="Move step up"
                  >
                    <ArrowUp size={13} />
                  </button>
                  <button
                    type="button"
                    className="icon-action-btn"
                    onClick={() => moveStep(index, 1)}
                    disabled={disabled || index === steps.length - 1}
                    aria-label={`Move step ${index + 1} down`}
                    title="Move step down"
                  >
                    <ArrowDown size={13} />
                  </button>
                  <button
                    type="button"
                    className="icon-action-btn danger-btn"
                    onClick={() => removeStep(index)}
                    disabled={disabled}
                    aria-label={`Delete step ${index + 1}`}
                    title="Delete step"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              <div className="step-card-body">
                <div className="field">
                  <label htmlFor={`step-action-${index}`}>Action</label>
                  <select
                    id={`step-action-${index}`}
                    value={step.action}
                    disabled={disabled}
                    onChange={(e) => updateStep(index, { action: e.target.value })}
                  >
                    {SUPPORTED_ACTIONS.map((action) => (
                      <option key={action.value} value={action.value}>
                        {action.label}
                      </option>
                    ))}
                  </select>
                </div>

                {step.action === 'goto' && (
                  <div className="field">
                    <label htmlFor={`step-url-${index}`}>Target URL</label>
                    <input
                      id={`step-url-${index}`}
                      type="url"
                      value={step.value || ''}
                      disabled={disabled}
                      placeholder="https://example.com"
                      onChange={(e) => updateStep(index, { value: e.target.value })}
                      required
                    />
                  </div>
                )}

                {step.action === 'click' && (
                  <div className="field">
                    <label htmlFor={`step-selector-${index}`}>Target selector</label>
                    <input
                      id={`step-selector-${index}`}
                      type="text"
                      value={step.selector || ''}
                      disabled={disabled}
                      placeholder="button#submit, a.nav-link, or text=Sign In"
                      onChange={(e) => updateStep(index, { selector: e.target.value })}
                      required
                    />
                  </div>
                )}

                {step.action === 'fill' && (
                  <>
                    <div className="field">
                      <label htmlFor={`step-selector-${index}`}>Input selector</label>
                      <input
                        id={`step-selector-${index}`}
                        type="text"
                        value={step.selector || ''}
                        disabled={disabled}
                        placeholder="#username, input[type='email']"
                        onChange={(e) => updateStep(index, { selector: e.target.value })}
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`step-value-${index}`}>Value to fill</label>
                      <input
                        id={`step-value-${index}`}
                        type="text"
                        value={step.value || ''}
                        disabled={disabled}
                        placeholder="user@example.com"
                        onChange={(e) => updateStep(index, { value: e.target.value })}
                        required
                      />
                    </div>
                  </>
                )}

                {step.action === 'expect_text' && (
                  <div className="field">
                    <label htmlFor={`step-text-${index}`}>Expected text</label>
                    <input
                      id={`step-text-${index}`}
                      type="text"
                      value={step.value || ''}
                      disabled={disabled}
                      placeholder="Text expected to appear on the page"
                      onChange={(e) => updateStep(index, { value: e.target.value })}
                      required
                    />
                  </div>
                )}

                {step.action === 'expect_title' && (
                  <div className="field">
                    <label htmlFor={`step-title-${index}`}>Expected page title</label>
                    <input
                      id={`step-title-${index}`}
                      type="text"
                      value={step.value || ''}
                      disabled={disabled}
                      placeholder="Dashboard — VeriGate"
                      onChange={(e) => updateStep(index, { value: e.target.value })}
                      required
                    />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
