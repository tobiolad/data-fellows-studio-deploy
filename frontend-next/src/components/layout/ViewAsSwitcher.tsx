import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Eye, EyeOff, ShieldCheck, Sparkles, Users } from "lucide-react"
import { useViewAs } from "@/lib/view-as"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { AdmissionListItem, Organization, Role } from "@/lib/types"

/** Lets an admin preview exactly what one client organization's portal, one
 *  professional's portal, or the reviewer workspace looks like. It only ever
 *  changes which screens render -- every request those screens make still
 *  runs as the admin's own identity, so nothing here grants new authority. */
export function ViewAsSwitcher() {
  const { viewAs, setViewAs } = useViewAs()
  const navigate = useNavigate()
  const [pickerRole, setPickerRole] = useState<"client" | "professional" | null>(null)

  const organizations = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<Organization[]>("/organizations"),
    enabled: pickerRole === "client",
  })
  const professionals = useQuery({
    queryKey: ["admissions", "approved"],
    queryFn: () => api.get<AdmissionListItem[]>("/professionals/admissions?status_filter=approved"),
    enabled: pickerRole === "professional",
  })

  function startPreview(role: Role, targetId?: string, targetLabel?: string) {
    setViewAs({ role, targetId, targetLabel })
    navigate(`/${role}`)
  }

  function exitPreview() {
    setViewAs(null)
    navigate("/admin")
  }

  if (viewAs) {
    return (
      <div className="flex items-center gap-1.5">
        <Badge variant="secondary" className="gap-1 border border-primary/30 bg-primary/10 text-primary">
          <Eye className="h-3 w-3" />
          Previewing: {viewAs.role}
          {viewAs.targetLabel ? ` — ${viewAs.targetLabel}` : ""}
        </Badge>
        <Button size="sm" variant="ghost" onClick={exitPreview}>
          <EyeOff className="h-3.5 w-3.5" /> Exit preview
        </Button>
      </div>
    )
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="sm" variant="outline">
            <Eye className="h-3.5 w-3.5" /> View as
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => setPickerRole("client")}>
            <Users className="h-3.5 w-3.5" /> A client
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setPickerRole("professional")}>
            <Sparkles className="h-3.5 w-3.5" /> A professional
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => startPreview("reviewer")}>
            <ShieldCheck className="h-3.5 w-3.5" /> The reviewer workspace
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={pickerRole === "client"} onOpenChange={(open) => !open && setPickerRole(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>View as which client?</DialogTitle>
            <DialogDescription>Shows exactly what that organization's client sees. You're still signed in as yourself.</DialogDescription>
          </DialogHeader>
          <Select onValueChange={(id) => startPreview("client", id, organizations.data?.find((o) => o.id === id)?.name)}>
            <SelectTrigger>
              <SelectValue placeholder="Choose an organization" />
            </SelectTrigger>
            <SelectContent>
              {organizations.data?.map((org) => (
                <SelectItem key={org.id} value={org.id}>
                  {org.name}
                </SelectItem>
              ))}
              {organizations.data?.length === 0 && <p className="px-3 py-2 text-xs text-muted-foreground">No organizations yet.</p>}
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPickerRole(null)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={pickerRole === "professional"} onOpenChange={(open) => !open && setPickerRole(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>View as which professional?</DialogTitle>
            <DialogDescription>Shows exactly what that professional sees. You're still signed in as yourself.</DialogDescription>
          </DialogHeader>
          <Select
            onValueChange={(id) =>
              startPreview("professional", id, professionals.data?.find((p) => p.professional_id === id)?.display_name)
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Choose a professional" />
            </SelectTrigger>
            <SelectContent>
              {professionals.data?.map((pro) => (
                <SelectItem key={pro.professional_id} value={pro.professional_id}>
                  {pro.display_name || pro.professional_id}
                </SelectItem>
              ))}
              {professionals.data?.length === 0 && <p className="px-3 py-2 text-xs text-muted-foreground">Nobody's been admitted yet.</p>}
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPickerRole(null)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
