"""Minimum admission requirements shared by both storage adapters."""


QUALIFICATION_POLICY_VERSION = "studio-admission-v1"


def check_approval(application, profile, review, professional_id, reviewer):
    if reviewer == professional_id:
        raise ValueError("An independent reviewer must make the admission decision")
    if application["status"] not in {"under_review", "assessment"}:
        raise ValueError("Begin an admission review before approving the application")
    if any(record.get(key) for record in (application, review)
           for key in ("missing_information", "assessment_requests")):
        raise ValueError("Resolve outstanding information and assessment requests before approval")
    if not profile or review.get("reviewed_profile_version") != profile.get("version"):
        raise ValueError("Review the current profile and confirm its qualifications and evidence")
    if not any(skill.strip() for skill in profile["skills"]):
        raise ValueError("At least one professional skill is required")
    if not any(ref.get("label", "").strip() and ref.get("reference", "").startswith("private://")
               and ref["reference"][10:].strip("/") for ref in profile["evidence_references"]):
        raise ValueError("A labeled private evidence reference is required for review")
