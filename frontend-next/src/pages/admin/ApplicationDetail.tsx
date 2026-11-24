import { useState } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowLeft, CheckCircle2, Plus, ShieldCheck, X } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TagInput } from "@/components/TagInput"
import { Skeleton } from "@/components/ui/skeleton"
import { api, ApiError } from "@/lib/api"
import type { AdmissionApplication, ProfessionalProfile } from "@/lib/types"

const DECISIONS = [
  { value: "under_review", label: "Move to under review" },
  { value: "assessment", label: "Request assessment" },
  { value: "approved", label: "Approve" },
  { value: "declined", label: "Decline" },
  { value: "revoked", label: "Revoke" },
]

export function AdminApplicationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const professionalId = id!
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [decision, setDecision] = useState("under_review")
  const [reason, setReason] = useState("")
  const [missingInfo, setMissingInfo] = useState<string[]>([])
  const [assessments, setAssessments] = useState<{ title: string; detail: string }[]>([])
  const [nextAction, setNextAction] = useState("")
  const [verifiedIndices, setVerifiedIndices] = useState<number[]>([])

  const application = useQuery({
    queryKey: ["application", professionalId],
    queryFn: () => api.get<AdmissionApplication>(`/professionals/${encodeURIComponent(professionalId)}/application`),
  })

  const profile = useQuery({
    queryKey: ["profile", professionalId],
    queryFn: async () => {
      try {
        return await api.get<ProfessionalProfile>(`/professionals/${encodeURIComponent(professionalId)}/profile`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  })

  const history = useQuery({
    queryKey: ["admission-history", professionalId],
    queryFn: () => api.get<{ action: string; reviewer: string; created_at: string }[]>(`/professionals/${encodeURIComponent(professionalId)}/admission-history`),
  })

  const submitReview = useMutation({
    mutationFn: () =>
      api.post(`/professionals/${encodeURIComponent(professionalId)}/review`, {
        status: decision,
        reason,
        missing_information: missingInfo,
        assessment_requests: assessments.filter((item) => item.title.trim()),
        next_action: nextAction,
        reviewed_profile_version: profile.data?.version,
        verified_evidence_indices: verifiedIndices,
      }),
    onSuccess: () => {
      toast.success("Review decision recorded")
      queryClient.invalidateQueries({ queryKey: ["admissions"] })
      queryClient.invalidateQueries({ queryKey: ["application", professionalId] })
      queryClient.invalidateQueries({ queryKey: ["admission-history", professionalId] })
      navigate("/admin/applications")
    },
    onError: (error) => toast.error((error as Error).message),
  })

  if (application.isLoading || profile.isLoading) {
    return (
      <AppShell title="Application">
        <Skeleton className="h-64" />
      </AppShell>
    )
  }

  return (
    <AppShell title={profile.data?.display_name || professionalId} description={professionalId}>
      <Link to="/admin/applications" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to applications
      </Link>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Profile</CardTitle>
              {application.data && (
                <Badge variant="secondary" className="capitalize">
                  {application.data.status.replace("_", " ")}
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {!profile.data ? (
                <p className="text-sm text-muted-foreground">No profile submitted yet.</p>
              ) : (
                <>
                  <div>
                    <p className="font-heading text-lg font-semibold text-foreground">{profile.data.display_name}</p>
                    <p className="text-sm text-muted-foreground">{profile.data.headline}</p>
                  </div>
                  {profile.data.bio && <p className="text-sm text-foreground">{profile.data.bio}</p>}
                  {profile.data.skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {profile.data.skills.map((skill) => (
                        <Badge key={skill} variant="outline">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {profile.data.availability && (
                    <p className="text-xs text-muted-foreground">Availability: {profile.data.availability}</p>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {profile.data && profile.data.evidence_references.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Evidence</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Select evidence you've independently verified. Required before approval.
                </p>
              </CardHeader>
              <CardContent className="space-y-2">
                {profile.data.evidence_references.map((item, index) => (
                  <label key={index} className="flex items-start gap-3 rounded-lg border border-border p-3">
                    <Checkbox
                      checked={verifiedIndices.includes(index)}
                      onCheckedChange={(checked) =>
                        setVerifiedIndices((current) => (checked ? [...current, index] : current.filter((value) => value !== index)))
                      }
                    />
                    <span className="flex-1">
                      <span className="block text-sm font-medium text-foreground">{item.label}</span>
                      <span className="block text-xs text-muted-foreground">{item.reference}</span>
                    </span>
                    <Badge variant={item.status === "reviewer verified" ? "secondary" : "outline"} className="shrink-0">
                      {item.status ?? "unverified"}
                    </Badge>
                  </label>
                ))}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">History</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {history.data?.length === 0 && <p className="text-sm text-muted-foreground">No decisions recorded yet.</p>}
              {history.data?.map((item, index) => (
                <div key={index} className="flex items-start gap-2.5 text-xs">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <div>
                    <p className="font-medium text-foreground">{item.action}</p>
                    <p className="text-muted-foreground">
                      {item.reviewer} · {new Date(item.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card className="sticky top-20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheck className="h-4 w-4 text-primary" /> Record a decision
              </CardTitle>
              <p className="text-xs text-muted-foreground">An independent reviewer — not the applicant — must make this decision.</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label>Decision</Label>
                <Select value={decision} onValueChange={setDecision}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DECISIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Reason</Label>
                <Textarea rows={3} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Required for approve, decline or revoke" />
              </div>

              <div className="space-y-1.5">
                <Label>Missing information</Label>
                <TagInput value={missingInfo} onChange={setMissingInfo} placeholder="e.g. Proof of prior work" />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label>Assessment requests</Label>
                  <Button type="button" variant="outline" size="sm" onClick={() => setAssessments((current) => [...current, { title: "", detail: "" }])}>
                    <Plus className="h-3 w-3" /> Add
                  </Button>
                </div>
                {assessments.map((item, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Input
                      placeholder="Assessment title"
                      value={item.title}
                      onChange={(event) =>
                        setAssessments((current) => current.map((row, i) => (i === index ? { ...row, title: event.target.value } : row)))
                      }
                    />
                    <button type="button" onClick={() => setAssessments((current) => current.filter((_, i) => i !== index))}>
                      <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="space-y-1.5">
                <Label>Next action for the applicant</Label>
                <Input value={nextAction} onChange={(event) => setNextAction(event.target.value)} placeholder="Optional" />
              </div>

              <Button className="w-full" disabled={submitReview.isPending} onClick={() => submitReview.mutate()}>
                <CheckCircle2 className="h-3.5 w-3.5" /> Submit decision
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
