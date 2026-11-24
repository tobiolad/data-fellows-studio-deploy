import type { ReactNode } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import type { Role } from "@/lib/types"

export function RequireAuth({ role, children }: { role: Role; children: ReactNode }) {
  const { session } = useAuth()
  if (!session) return <Navigate to="/sign-in" replace />
  if (session.role !== role) return <Navigate to={`/${session.role}`} replace />
  return <>{children}</>
}
