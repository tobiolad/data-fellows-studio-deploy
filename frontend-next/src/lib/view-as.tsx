import { createContext, useContext, useState, type ReactNode } from "react"
import type { Role } from "@/lib/types"

/** An admin previewing exactly what one client organization or one professional
 *  sees. Never set for a non-admin session, and never a way to act as them --
 *  every write the previewed screens can make still runs as the admin's own
 *  identity, so the server's own role and ownership checks decide what succeeds. */
export interface ViewAsTarget {
  role: Role
  targetId?: string
  targetLabel?: string
}

const STORAGE_KEY = "studio.viewAs"

function readStored(): ViewAsTarget | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ViewAsTarget) : null
  } catch {
    return null
  }
}

function writeStored(value: ViewAsTarget | null) {
  try {
    if (value) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Best-effort only; an admin preview not persisting across a reload is not a correctness issue.
  }
}

interface ViewAsContextValue {
  viewAs: ViewAsTarget | null
  setViewAs: (target: ViewAsTarget | null) => void
}

const ViewAsContext = createContext<ViewAsContextValue | null>(null)

export function ViewAsProvider({ children }: { children: ReactNode }) {
  const [viewAs, setViewAsState] = useState<ViewAsTarget | null>(() => readStored())

  function setViewAs(target: ViewAsTarget | null) {
    writeStored(target)
    setViewAsState(target)
  }

  return <ViewAsContext.Provider value={{ viewAs, setViewAs }}>{children}</ViewAsContext.Provider>
}

export function useViewAs() {
  const ctx = useContext(ViewAsContext)
  if (!ctx) throw new Error("useViewAs must be used within ViewAsProvider")
  return ctx
}

/** The role whose screens should render right now: the real session's role, unless
 *  an admin has an active preview, in which case the role being previewed. */
export function useEffectiveRole(sessionRole: Role): Role {
  const { viewAs } = useViewAs()
  if (sessionRole !== "admin") return sessionRole
  return viewAs?.role ?? "admin"
}
