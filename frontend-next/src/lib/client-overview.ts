import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { useViewAs } from "@/lib/view-as"
import type { ClientOverview } from "@/lib/types"

/** Every client page reads this. When an admin is previewing a specific
 *  organization, it reads that organization instead of "my own membership" --
 *  the same query key so React Query treats a preview switch like any other
 *  parameter change, not a different screen. */
export function useClientOverview() {
  const { viewAs } = useViewAs()
  const previewOrgId = viewAs?.role === "client" ? viewAs.targetId : undefined

  return useQuery({
    queryKey: ["client-overview", previewOrgId ?? "self"],
    queryFn: () =>
      api.get<ClientOverview>(previewOrgId ? `/client/overview?organization_id=${encodeURIComponent(previewOrgId)}` : "/client/overview"),
  })
}

export function clientOverviewQueryKey(previewOrgId?: string) {
  return ["client-overview", previewOrgId ?? "self"]
}
