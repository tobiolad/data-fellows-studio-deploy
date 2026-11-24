import { z } from "zod"

export const basicsSchema = z.object({
  display_name: z.string().min(2, "Enter your full name").max(160),
  headline: z.string().max(240).optional().default(""),
  bio: z.string().max(4000).optional().default(""),
  availability: z.string().max(120).optional().default(""),
})

export const skillsSchema = z.object({
  skills: z.array(z.string().min(1)).min(1, "Add at least one skill"),
  specializations: z.array(z.string().min(1)).max(20).default([]),
})

export const experienceItemSchema = z.object({
  role: z.string().min(1, "Role is required"),
  organization: z.string().min(1, "Organization is required"),
  start: z.string().optional().default(""),
  end: z.string().optional().default(""),
  summary: z.string().max(1000).optional().default(""),
})

export const educationItemSchema = z.object({
  institution: z.string().min(1, "Institution is required"),
  credential: z.string().optional().default(""),
  year: z.string().optional().default(""),
})

export const backgroundSchema = z.object({
  experience: z.array(experienceItemSchema).default([]),
  education: z.array(educationItemSchema).default([]),
})

export const portfolioItemSchema = z.object({
  title: z.string().min(1, "Title is required"),
  url: z.string().max(2048).optional().default(""),
})

export const evidenceItemSchema = z.object({
  label: z.string().min(1, "Label is required"),
  reference: z
    .string()
    .min(1, "Reference is required")
    .refine((value) => /^(private|quarantine|pending):\/\/\S+/.test(value), {
      message: "Use a private://, quarantine:// or pending:// reference",
    }),
  classification: z.string().optional().default(""),
})

export const portfolioSchema = z.object({
  portfolio: z.array(portfolioItemSchema).default([]),
  evidence_references: z.array(evidenceItemSchema).default([]),
})

export const profileFormSchema = basicsSchema.merge(skillsSchema).merge(backgroundSchema).merge(portfolioSchema)

export type ProfileFormValues = z.input<typeof profileFormSchema>

export const STEP_FIELDS: Record<number, (keyof ProfileFormValues)[]> = {
  0: ["display_name", "headline", "bio", "availability"],
  1: ["skills", "specializations"],
  2: ["experience", "education"],
  3: ["portfolio", "evidence_references"],
  4: [],
}

export const EMPTY_PROFILE: ProfileFormValues = {
  display_name: "",
  headline: "",
  bio: "",
  availability: "",
  skills: [],
  specializations: [],
  experience: [],
  education: [],
  portfolio: [],
  evidence_references: [],
}
