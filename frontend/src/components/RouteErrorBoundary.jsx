import { Component } from 'react'

export class RouteErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <main className="library-page">
          <section className="projects-state projects-state--error" role="alert">
            <h2>Unable to display this page</h2>
            <p>Something went wrong while rendering this view. Try again or return to your workspace.</p>
            <div className="heading-actions">
              <button className="secondary-button" onClick={() => this.setState({ error: null })}>Try again</button>
              <a className="secondary-button" href="/app">Return to workspace</a>
            </div>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}
