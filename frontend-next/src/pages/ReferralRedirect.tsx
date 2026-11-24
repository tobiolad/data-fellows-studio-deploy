import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Sparkles } from "lucide-react"

export function ReferralRedirectPage() {
  const { code } = useParams<{ code: string }>()
  const [status, setStatus] = useState<"recording" | "done" | "error">("recording")

  useEffect(() => {
    if (!code) return
    fetch(`/api/referral-links/${encodeURIComponent(code)}/visit`, { method: "POST" })
      .then((response) => setStatus(response.ok ? "done" : "error"))
      .catch(() => setStatus("error"))
  }, [code])

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
        <Sparkles className="h-5 w-5" />
      </div>
      <h1 className="font-heading text-xl font-semibold text-foreground">Welcome to Data Fellows</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        {status === "error"
          ? "This referral link isn't active, but we'd still love to hear from you."
          : "A member of our team will follow up shortly. In the meantime, feel free to reach out directly."}
      </p>
    </div>
  )
}
