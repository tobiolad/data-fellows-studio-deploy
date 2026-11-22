-- Keep legacy decision provenance intact. Assign a policy version to new events only.
CREATE VIEW studio_current_assignments AS
SELECT a.*, w.project_id, p.engagement_id, e.organization_id
FROM assignments a
JOIN professional_admissions admission ON admission.professional_id = a.professional_id
JOIN work_packages w ON w.id = a.work_package_id
JOIN projects p ON p.id = w.project_id
JOIN engagements e ON e.id = p.engagement_id
JOIN memberships m ON m.organization_id = e.organization_id AND m.actor_id = a.professional_id
                 AND m.role = 'professional' AND m.revoked_at IS NULL
WHERE admission.status = 'approved' AND a.status IN ('accepted', 'invited')
  AND (a.expires_at IS NULL OR a.expires_at > now());

CREATE FUNCTION studio_preserve_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Studio audit history is append-only';
END;
$$;
CREATE TRIGGER preserve_audit BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_events
FOR EACH STATEMENT EXECUTE FUNCTION studio_preserve_audit();
