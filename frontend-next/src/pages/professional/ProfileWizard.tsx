import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useForm, useFieldArray, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AnimatePresence, motion } from "framer-motion"
import { toast } from "sonner"
import {
  ArrowLeft,
  ArrowRight,
  Check,
  GraduationCap,
  Link2,
  Plus,
  Sparkles,
  Trash2,
  User,
} from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { TagInput } from "@/components/TagInput"
import { api, ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { useIsPreviewingProfessional, usePreviewedProfessionalId } from "@/lib/view-as"
import type { AdmissionApplication, ProfessionalProfile } from "@/lib/types"
import {
  EMPTY_PROFILE,
  STEP_FIELDS,
  profileFormSchema,
  type ProfileFormValues,
} from "@/lib/profile-schema"
import { cn } from "@/lib/utils"

const STEPS = [
  { title: "Basics", description: "Who you are", icon: User },
  { title: "Skills", description: "What you're great at", icon: Sparkles },
  { title: "Background", description: "Experience & education", icon: GraduationCap },
  { title: "Evidence", description: "Portfolio & proof of work", icon: Link2 },
  { title: "Review", description: "Submit for review", icon: Check },
]

function toFormValues(profile: ProfessionalProfile): ProfileFormValues {
  return {
    display_name: profile.display_name ?? "",
    headline: profile.headline ?? "",
    bio: profile.bio ?? "",
    availability: profile.availability ?? "",
    skills: profile.skills ?? [],
    specializations: profile.specializations ?? [],
    experience: (profile.experience ?? []).map((item) => ({
      role: item.role ?? "",
      organization: item.organization ?? "",
      start: item.start ?? "",
      end: item.end ?? "",
      summary: item.summary ?? "",
    })),
    education: (profile.education ?? []).map((item) => ({
      institution: item.institution ?? "",
      credential: item.credential ?? "",
      year: item.year ?? "",
    })),
    portfolio: (profile.portfolio ?? []).map((item) => ({ title: item.title ?? "", url: item.url ?? "" })),
    evidence_references: (profile.evidence_references ?? []).map((item) => ({
      label: item.label ?? "",
      reference: item.reference ?? "",
      classification: item.classification ?? "",
    })),
  }
}

export function ProfileWizardPage() {
  const { session } = useAuth()
  const actorId = usePreviewedProfessionalId(session!.actorId)
  const previewing = useIsPreviewingProfessional()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [step, setStep] = useState(0)

  const profileQuery = useQuery({
    queryKey: ["profile", actorId],
    queryFn: async () => {
      try {
        return await api.get<ProfessionalProfile>(`/professionals/${encodeURIComponent(actorId)}/profile`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  })

  const applicationQuery = useQuery({
    queryKey: ["application", actorId],
    queryFn: async () => {
      try {
        return await api.get<AdmissionApplication>(`/professionals/${encodeURIComponent(actorId)}/application`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  })

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: EMPTY_PROFILE,
    mode: "onTouched",
  })

  useEffect(() => {
    if (profileQuery.data) form.reset(toFormValues(profileQuery.data))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileQuery.data])

  const experience = useFieldArray({ control: form.control, name: "experience" })
  const education = useFieldArray({ control: form.control, name: "education" })
  const portfolio = useFieldArray({ control: form.control, name: "portfolio" })
  const evidence = useFieldArray({ control: form.control, name: "evidence_references" })

  const submit = useMutation({
    mutationFn: async (values: ProfileFormValues) => {
      // An application record must exist before the backend will accept a
      // profile write (persistence.py's upsert_professional_profile), so a
      // first-time applicant has to get one created first.
      if (!applicationQuery.data) {
        await api.post(`/professionals/${encodeURIComponent(actorId)}/application`)
      }
      await api.put(`/professionals/${encodeURIComponent(actorId)}/profile`, {
        ...values,
        expected_version: profileQuery.data?.version,
      })
    },
    onSuccess: () => {
      toast.success("Profile submitted for independent review")
      queryClient.invalidateQueries({ queryKey: ["profile", actorId] })
      queryClient.invalidateQueries({ queryKey: ["application", actorId] })
      navigate("/professional")
    },
    onError: (error) => toast.error((error as Error).message || "Couldn't submit your profile"),
  })

  const progress = useMemo(() => ((step + 1) / STEPS.length) * 100, [step])
  const values = form.watch()

  async function next() {
    const fields = STEP_FIELDS[step]
    const valid = fields.length === 0 || (await form.trigger(fields))
    if (valid) setStep((current) => Math.min(current + 1, STEPS.length - 1))
  }

  if (profileQuery.isLoading) {
    return (
      <AppShell title="Professional profile">
        <p className="text-sm text-muted-foreground">Loading your profile…</p>
      </AppShell>
    )
  }

  return (
    <AppShell title="Build your professional profile" description="A great profile is the fastest path to meaningful work.">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8">
          <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full bg-primary"
              initial={false}
              animate={{ width: `${progress}%` }}
              transition={{ type: "spring", stiffness: 200, damping: 30 }}
            />
          </div>
          <div className="flex justify-between">
            {STEPS.map((item, index) => {
              const Icon = item.icon
              const state = index < step ? "done" : index === step ? "active" : "upcoming"
              return (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => index <= step && setStep(index)}
                  disabled={index > step}
                  className="flex flex-col items-center gap-1.5 text-center"
                >
                  <span
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-medium transition-colors",
                      state === "done" && "border-primary bg-primary text-primary-foreground",
                      state === "active" && "border-primary text-primary",
                      state === "upcoming" && "border-border text-muted-foreground",
                    )}
                  >
                    {state === "done" ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                  </span>
                  <span className={cn("hidden text-[11px] font-medium sm:block", state === "upcoming" ? "text-muted-foreground" : "text-foreground")}>
                    {item.title}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <Card className="overflow-hidden">
          <CardContent className="p-6 sm:p-8">
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.2 }}
              >
                <h2 className="font-heading text-xl font-semibold text-foreground">{STEPS[step].title}</h2>
                <p className="mb-6 text-sm text-muted-foreground">{STEPS[step].description}</p>

                {step === 0 && (
                  <div className="space-y-5">
                    <div className="space-y-1.5">
                      <Label htmlFor="display_name">Full name</Label>
                      <Input id="display_name" {...form.register("display_name")} placeholder="Jordan Reyes" />
                      {form.formState.errors.display_name && (
                        <p className="text-xs text-destructive">{form.formState.errors.display_name.message}</p>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="headline">Headline</Label>
                      <Input id="headline" {...form.register("headline")} placeholder="Senior automation engineer" />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="bio">About you</Label>
                      <Textarea id="bio" rows={4} {...form.register("bio")} placeholder="What kind of problems do you love solving?" />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="availability">Availability</Label>
                      <Input id="availability" {...form.register("availability")} placeholder="20 hrs/week" />
                    </div>
                  </div>
                )}

                {step === 1 && (
                  <div className="space-y-5">
                    <div className="space-y-1.5">
                      <Label>Skills</Label>
                      <Controller
                        control={form.control}
                        name="skills"
                        render={({ field }) => <TagInput value={field.value} onChange={field.onChange} placeholder="Type a skill and press Enter" />}
                      />
                      {form.formState.errors.skills && <p className="text-xs text-destructive">{form.formState.errors.skills.message}</p>}
                    </div>
                    <div className="space-y-1.5">
                      <Label>Specializations</Label>
                      <Controller
                        control={form.control}
                        name="specializations"
                        render={({ field }) => <TagInput value={field.value ?? []} onChange={field.onChange} placeholder="e.g. Data Engineering" />}
                      />
                    </div>
                  </div>
                )}

                {step === 2 && (
                  <div className="space-y-8">
                    <div>
                      <div className="mb-3 flex items-center justify-between">
                        <Label className="text-sm">Experience</Label>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => experience.append({ role: "", organization: "", start: "", end: "", summary: "" })}
                        >
                          <Plus className="h-3.5 w-3.5" /> Add
                        </Button>
                      </div>
                      <div className="space-y-3">
                        {experience.fields.map((field, index) => (
                          <div key={field.id} className="relative rounded-lg border border-border p-4">
                            <button
                              type="button"
                              onClick={() => experience.remove(index)}
                              className="absolute right-3 top-3 text-muted-foreground hover:text-destructive"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                            <div className="grid gap-3 pr-6 sm:grid-cols-2">
                              <Input placeholder="Role" {...form.register(`experience.${index}.role`)} />
                              <Input placeholder="Organization" {...form.register(`experience.${index}.organization`)} />
                              <Input placeholder="Start (e.g. 2022)" {...form.register(`experience.${index}.start`)} />
                              <Input placeholder="End (or Present)" {...form.register(`experience.${index}.end`)} />
                            </div>
                            <Textarea
                              className="mt-3"
                              rows={2}
                              placeholder="What did you own or deliver?"
                              {...form.register(`experience.${index}.summary`)}
                            />
                          </div>
                        ))}
                        {experience.fields.length === 0 && (
                          <p className="text-sm text-muted-foreground">No experience added yet — optional, but it helps reviewers.</p>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="mb-3 flex items-center justify-between">
                        <Label className="text-sm">Education</Label>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => education.append({ institution: "", credential: "", year: "" })}
                        >
                          <Plus className="h-3.5 w-3.5" /> Add
                        </Button>
                      </div>
                      <div className="space-y-3">
                        {education.fields.map((field, index) => (
                          <div key={field.id} className="relative rounded-lg border border-border p-4">
                            <button
                              type="button"
                              onClick={() => education.remove(index)}
                              className="absolute right-3 top-3 text-muted-foreground hover:text-destructive"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                            <div className="grid gap-3 pr-6 sm:grid-cols-3">
                              <Input placeholder="Institution" {...form.register(`education.${index}.institution`)} />
                              <Input placeholder="Credential" {...form.register(`education.${index}.credential`)} />
                              <Input placeholder="Year" {...form.register(`education.${index}.year`)} />
                            </div>
                          </div>
                        ))}
                        {education.fields.length === 0 && <p className="text-sm text-muted-foreground">No education added yet — optional.</p>}
                      </div>
                    </div>
                  </div>
                )}

                {step === 3 && (
                  <div className="space-y-8">
                    <div>
                      <div className="mb-3 flex items-center justify-between">
                        <Label className="text-sm">Portfolio</Label>
                        <Button type="button" variant="outline" size="sm" onClick={() => portfolio.append({ title: "", url: "" })}>
                          <Plus className="h-3.5 w-3.5" /> Add
                        </Button>
                      </div>
                      <div className="space-y-3">
                        {portfolio.fields.map((field, index) => (
                          <div key={field.id} className="relative grid gap-3 rounded-lg border border-border p-4 pr-10 sm:grid-cols-2">
                            <button
                              type="button"
                              onClick={() => portfolio.remove(index)}
                              className="absolute right-3 top-3 text-muted-foreground hover:text-destructive"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                            <Input placeholder="Title" {...form.register(`portfolio.${index}.title`)} />
                            <Input placeholder="Link" {...form.register(`portfolio.${index}.url`)} />
                          </div>
                        ))}
                        {portfolio.fields.length === 0 && <p className="text-sm text-muted-foreground">No portfolio items yet — optional.</p>}
                      </div>
                    </div>

                    <div>
                      <div className="mb-1 flex items-center justify-between">
                        <Label className="text-sm">Evidence for review</Label>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => evidence.append({ label: "", reference: "", classification: "" })}
                        >
                          <Plus className="h-3.5 w-3.5" /> Add
                        </Button>
                      </div>
                      <p className="mb-3 text-xs text-muted-foreground">
                        A reviewer verifies these before approval. References use a private storage scheme — never a public link.
                      </p>
                      <div className="space-y-3">
                        {evidence.fields.map((field, index) => (
                          <div key={field.id} className="relative rounded-lg border border-border p-4 pr-10">
                            <button
                              type="button"
                              onClick={() => evidence.remove(index)}
                              className="absolute right-3 top-3 text-muted-foreground hover:text-destructive"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                            <div className="grid gap-3 sm:grid-cols-2">
                              <Input placeholder="Label (e.g. Case study)" {...form.register(`evidence_references.${index}.label`)} />
                              <Input placeholder="private://evidence/…" {...form.register(`evidence_references.${index}.reference`)} />
                            </div>
                            {form.formState.errors.evidence_references?.[index]?.reference && (
                              <p className="mt-1.5 text-xs text-destructive">
                                {form.formState.errors.evidence_references[index]?.reference?.message}
                              </p>
                            )}
                          </div>
                        ))}
                        {evidence.fields.length === 0 && <p className="text-sm text-muted-foreground">No evidence added yet — optional.</p>}
                      </div>
                    </div>
                  </div>
                )}

                {step === 4 && (
                  <div className="space-y-5">
                    <div className="rounded-lg border border-border p-4">
                      <p className="font-heading text-base font-semibold text-foreground">{values.display_name || "Your name"}</p>
                      <p className="text-sm text-muted-foreground">{values.headline}</p>
                      {values.skills.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {values.skills.map((skill) => (
                            <span key={skill} className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                              {skill}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
                      <div>
                        <dt className="text-xs text-muted-foreground">Experience</dt>
                        <dd className="font-medium text-foreground">{values.experience?.length ?? 0}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">Education</dt>
                        <dd className="font-medium text-foreground">{values.education?.length ?? 0}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">Portfolio</dt>
                        <dd className="font-medium text-foreground">{values.portfolio?.length ?? 0}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">Evidence</dt>
                        <dd className="font-medium text-foreground">{values.evidence_references?.length ?? 0}</dd>
                      </div>
                    </dl>
                    <p className="text-sm text-muted-foreground">
                      Submitting sends your profile to an independent reviewer. You can keep editing afterwards — any
                      changes mark your evidence as unverified again until it's reviewed.
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </CardContent>

          <div className="flex items-center justify-between border-t border-border bg-muted/30 px-6 py-4 sm:px-8">
            <Button type="button" variant="ghost" onClick={() => setStep((current) => Math.max(current - 1, 0))} disabled={step === 0}>
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button type="button" onClick={next}>
                Continue <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            ) : (
              <Button type="button" onClick={form.handleSubmit((values) => submit.mutate(values))} disabled={previewing || submit.isPending}>
                {previewing ? "Previewing — read only" : submit.isPending ? "Submitting…" : "Submit for review"}
              </Button>
            )}
          </div>
        </Card>
      </div>
    </AppShell>
  )
}
