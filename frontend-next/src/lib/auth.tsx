import { createContext, useContext, useState, type ReactNode } from "react"
import { getSession, setSession, type Session } from "@/lib/api"

interface AuthContextValue {
  session: Session | null
  signIn: (session: Session) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setLocalSession] = useState<Session | null>(() => getSession())

  function signIn(next: Session) {
    setSession(next)
    setLocalSession(next)
  }

  function signOut() {
    setSession(null)
    setLocalSession(null)
  }

  return <AuthContext.Provider value={{ session, signIn, signOut }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
