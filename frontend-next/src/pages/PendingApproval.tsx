import { useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { Building2, Check, Hourglass, Sparkles, Users } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { api, ApiError } from "@/lib/api"
import type { SignupIntent } from "@/lib/types"
import { cn } from "@/lib/utils"

const INTENT_OPTIONS: { intent: SignupIntent; label: string; icon: typeof Sparkles }[] = [
  { intent: "professional", label: "I want to apply as a professional", icon: Sparkles },
  { intent: "client", label: "I'm joining as a client", icon: Building2 },
  { intent: "team", label: "I'm joining my team", icon: Users },
]

/** A one-press hint, nothing more: it tags the pending account for whoever
 *  assigns roles ("Jordan says: applying as a professional") so they're not
 *  guessing from a bare email address. It grants no role by itself -- an
 *  admin still decides, same as before this existed. */
function WhatBringsYouHere({ accessToken }: { accessToken?: string }) {
  const [chosen, setChosen] = useState<SignupIntent | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!accessToken) return null

  async function choose(intent: SignupIntent) {
    setSaving(true)
    setError(null)
    try {
      await api.post("/accounts/me/signup-intent", { intent }, { headers: { Authorization: `Bearer studio:${accessToken}` } })
      setChosen(intent)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save that just now.")
    } finally {
      setSaving(false)
    }
  }

  if (chosen) {
    return (
      <p className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
        <Check className="h-4 w-4" /> Thanks — we'll let whoever sets up access know.
      </p>
    )
  }

  return (
    <div className="w-full space-y-2">
      <p className="text-center text-xs font-medium text-muted-foreground">What brings you here?</p>
      <div className="grid gap-2">
        {INTENT_OPTIONS.map(({ intent, label, icon: Icon }) => (
          <button
            key={intent}
            type="button"
            disabled={saving}
            onClick={() => choose(intent)}
            className={cn(
              "flex items-center gap-2.5 rounded-lg border border-border px-3.5 py-2.5 text-left text-sm text-foreground transition-colors",
              "hover:border-primary/40 hover:bg-primary/5 disabled:opacity-60",
            )}
          >
            <Icon className="h-4 w-4 shrink-0 text-primary" /> {label}
          </button>
        ))}
      </div>
      {error && <p className="text-center text-xs text-destructive">{error}</p>}
    </div>
  )
}

export function PendingApprovalPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as { email?: string; accessToken?: string } | null
  const email = state?.email

  return (
    <div className="relative flex min-h-svh items-center justify-center overflow-hidden bg-background px-4 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/15 via-background to-background"
      />
      <Card className="w-full max-w-md border-border/60 shadow-xl shadow-black/5">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Hourglass className="h-5 w-5" />
          </div>
          <CardTitle className="text-xl">Your account is set up</CardTitle>
          <CardDescription>
            {email ? <>Signed in as <span className="font-medium text-foreground">{email}</span>.</> : "You're signed in."}{" "}
            An admin still needs to assign your workspace role before you can get in.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4 pt-2">
          <WhatBringsYouHere accessToken={state?.accessToken} />
          <p className="text-center text-sm text-muted-foreground">
            This usually doesn't take long. Try signing in again once you've heard back, or check with whoever
            invited you to Data Fellows Studio.
          </p>
          <Button variant="outline" onClick={() => navigate("/sign-in", { replace: true })}>
            Back to sign in
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
