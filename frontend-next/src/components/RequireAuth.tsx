import type { ReactNode } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import { useEffectiveRole } from "@/lib/view-as"
import type { Role } from "@/lib/types"

export function RequireAuth({ role, children }: { role: Role; children: ReactNode }) {
  const { session } = useAuth()
  // Called unconditionally: hooks can't follow the early return below.
  const effectiveRole = useEffectiveRole(session?.role ?? "admin")
  if (!session) return <Navigate to="/sign-in" replace />
  if (effectiveRole !== role) return <Navigate to={`/${effectiveRole}`} replace />
  return <>{children}</>
}
