import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { api, ApiError } from "@/lib/api"
import { googleRedirectUri, takeGoogleSignIn } from "@/lib/google-sign-in"
import type { GoogleSignInResponse } from "@/lib/types"

export function SsoCallbackPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get("code")
    const state = params.get("state")
    const start = takeGoogleSignIn(state)

    if (params.get("error")) {
      setError("Google sign-in was cancelled.")
      return
    }
    if (!code || !start) {
      setError("This sign-in link has expired. Please try again.")
      return
    }

    api
      .post<GoogleSignInResponse>("/auth/google", { code, redirect_uri: googleRedirectUri() })
      .then((body) => {
        if (body.pending || !body.role) {
          navigate("/pending-approval", { replace: true, state: { email: body.email, accessToken: body.access_token } })
          return
        }
        signIn({ actorId: body.actor_id, role: body.role, accessToken: body.access_token })
        navigate(`/${body.role}`, { replace: true })
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Google sign-in failed. Please try again.")
      })
    // Runs once: the one-time code and state are consumed on the first render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      {error ? (
        <>
          <p className="text-sm font-medium text-foreground">{error}</p>
          <button type="button" className="text-sm text-primary underline underline-offset-4" onClick={() => navigate("/sign-in", { replace: true })}>
            Back to sign in
          </button>
        </>
      ) : (
        <>
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Finishing sign-in with Google…</p>
        </>
      )}
    </div>
  )
}
