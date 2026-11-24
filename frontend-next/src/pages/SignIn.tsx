import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Building2, ShieldCheck, Sparkles, Users } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { beginGoogleSignIn, googleSignInEnabled } from "@/lib/google-sign-in"
import type { Role } from "@/lib/types"
import { cn } from "@/lib/utils"

const ROLE_OPTIONS: { role: Role; label: string; description: string; icon: typeof Users; defaultActor: string }[] = [
  { role: "admin", label: "Internal admin", description: "Mission Control: engagements, delivery, AI oversight", icon: ShieldCheck, defaultActor: "admin-1" },
  { role: "client", label: "Client", description: "Track delivery, review decisions, approve work", icon: Building2, defaultActor: "client-1" },
  { role: "professional", label: "Professional", description: "Manage your application, assignments, deliverables", icon: Sparkles, defaultActor: "professional-1" },
  { role: "reviewer", label: "Reviewer", description: "Independent quality and admission review", icon: Users, defaultActor: "reviewer-1" },
]

export function SignInPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [selected, setSelected] = useState<Role>("professional")
  const [actorId, setActorId] = useState(ROLE_OPTIONS[2].defaultActor)

  function chooseRole(role: Role, defaultActor: string) {
    setSelected(role)
    setActorId(defaultActor)
  }

  function enter() {
    signIn({ actorId: actorId.trim() || "guest", role: selected })
    navigate(`/${selected}`)
  }

  return (
    <div className="relative flex min-h-svh items-center justify-center overflow-hidden bg-background px-4 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/15 via-background to-background"
      />
      <div className="w-full max-w-4xl">
        <div className="mb-10 flex flex-col items-center text-center">
          <img
            src="/data-fellows-mark.svg"
            alt="Data Fellows"
            className="mb-4 h-14 w-14 rounded-2xl shadow-lg shadow-primary/20"
          />
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-foreground">Data Fellows Studio</h1>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            The operating platform for engagements, delivery, AI execution and quality across Data Fellows.
          </p>
        </div>

        {googleSignInEnabled() ? (
          <Card className="border-border/60 shadow-xl shadow-black/5">
            <CardContent className="flex flex-col items-center gap-3 py-6 text-center">
              <Button size="lg" variant="outline" className="w-full max-w-xs gap-2 sm:w-auto" onClick={beginGoogleSignIn}>
                <GoogleIcon className="h-4 w-4" />
                Continue with Google
              </Button>
              <p className="text-xs text-muted-foreground">New here? Signing in creates your account; an admin assigns your role.</p>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-border/60 shadow-xl shadow-black/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-xl">Choose your workspace</CardTitle>
              <CardDescription>
                Production sign-in uses Google. This local environment uses a synthetic identity so you can preview
                every workspace without real credentials.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-4">
              <div className="grid gap-3 sm:grid-cols-2">
                {ROLE_OPTIONS.map(({ role, label, description, icon: Icon, defaultActor }) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => chooseRole(role, defaultActor)}
                    className={cn(
                      "group flex items-start gap-3 rounded-xl border p-4 text-left transition-all hover:border-primary/50 hover:shadow-md",
                      selected === role ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary/30" : "border-border bg-card",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                        selected === role ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground group-hover:text-foreground",
                      )}
                    >
                      <Icon className="h-[18px] w-[18px]" />
                    </span>
                    <span>
                      <span className="block text-sm font-medium text-foreground">{label}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">{description}</span>
                    </span>
                  </button>
                ))}
              </div>

              <div className="flex flex-col gap-2 border-t border-border pt-5 sm:flex-row sm:items-end sm:justify-between">
                <div className="w-full max-w-xs space-y-1.5">
                  <Label htmlFor="actor-id" className="text-xs text-muted-foreground">
                    Synthetic identity
                  </Label>
                  <Input id="actor-id" value={actorId} onChange={(event) => setActorId(event.target.value)} />
                </div>
                <Button size="lg" onClick={enter} className="w-full sm:w-auto">
                  Enter workspace
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

function GoogleIcon(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className={props.className}>
      <path fill="#4285F4" d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.47a5.53 5.53 0 0 1-2.4 3.63v3h3.88c2.27-2.09 3.57-5.17 3.57-8.82Z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.07 7.95-2.91l-3.88-3c-1.08.72-2.46 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.26v3.11A12 12 0 0 0 12 24Z" />
      <path fill="#FBBC05" d="M5.27 14.28A7.2 7.2 0 0 1 4.89 12c0-.79.14-1.56.38-2.28V6.61H1.26A12 12 0 0 0 0 12c0 1.94.46 3.77 1.26 5.39l4.01-3.11Z" />
      <path fill="#EA4335" d="M12 4.77c1.76 0 3.34.61 4.59 1.8l3.44-3.44C17.94 1.19 15.24 0 12 0 7.31 0 3.26 2.69 1.26 6.61l4.01 3.11C6.22 6.88 8.87 4.77 12 4.77Z" />
    </svg>
  )
}
