CREATE TABLE IF NOT EXISTS work_package_dependencies (
    work_package_id uuid NOT NULL REFERENCES work_packages(id) ON DELETE RESTRICT,
    depends_on_id uuid NOT NULL REFERENCES work_packages(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (work_package_id, depends_on_id),
    CHECK (work_package_id <> depends_on_id)
);

CREATE INDEX IF NOT EXISTS work_package_dependencies_parent_idx
    ON work_package_dependencies(depends_on_id);
