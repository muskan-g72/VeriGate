import { authApi } from '../api/client'

export function OAuthButtons({ disabled = false }) {
  const continueWith = (provider) => window.location.assign(authApi.oauthLoginUrl(provider))
  return <div className="oauth-buttons"><button type="button" className="secondary-button" disabled={disabled} onClick={() => continueWith('google')}>Continue with Google</button><button type="button" className="secondary-button" disabled={disabled} onClick={() => continueWith('github')}>Continue with GitHub</button></div>
}
