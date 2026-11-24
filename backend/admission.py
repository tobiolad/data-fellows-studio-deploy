"""Minimum admission requirements shared by both storage adapters."""


import hashlib
import json

QUALIFICATION_POLICY_VERSION = "studio-admission-v2"


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
    refs = profile["evidence_references"]
    indices = review.get("verified_evidence_indices", [])
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("Verify at least one distinct evidence reference before approval")
    attested = []
    for index in indices:
        if index < 0 or index >= len(refs):
            raise ValueError("Evidence selection does not match the reviewed profile")
        ref = refs[index]
        if not ref.get("label", "").strip() or not ref.get("reference", "").startswith("private://") or not ref["reference"][10:].strip("/ "):
            raise ValueError("Only labeled private evidence can be verified")
        attested.append({"label": ref["label"], "reference_sha256": reference_hash(ref)})
    return attested


def evidence_status(profile, attestations):
    """Attach only staff-recorded attestations for this exact profile version."""
    verified = {item["reference_sha256"] for event in attestations
                if event.get("reviewed_profile_version") == profile["version"]
                for item in event.get("verified_evidence", [])}
    return [{**ref, "status": "reviewer verified" if reference_hash(ref) in verified else "unverified"}
            for ref in profile.get("evidence_references", [])]


def reference_hash(ref):
    value = json.dumps([ref.get("label"), ref.get("reference")], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()
