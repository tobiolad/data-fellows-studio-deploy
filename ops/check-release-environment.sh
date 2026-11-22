#!/usr/bin/env bash
# This job runs outside the named environment, before any federated login or protected job.
set -euo pipefail
[[ "$GITHUB_REF" == refs/heads/main && "$GITHUB_EVENT_NAME" == workflow_dispatch ]]
case "$1" in
  azure-inventory|studio-build|studio-preview|studio-migrate|studio-verify|studio-rollback) ;;
  *) exit 1 ;;
esac
protection="$(gh api "repos/$GITHUB_REPOSITORY/environments/$1")"
jq -e '.protection_rules | any(.type=="required_reviewers" and (.reviewers|length)>0 and .prevent_self_review==true)' <<<"$protection" >/dev/null
jq -e '.deployment_branch_policy.custom_branch_policies == true' <<<"$protection" >/dev/null
# Require a single exact main branch rule. Tags, wildcards and alternate branches fail closed.
gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/environments/$1/deployment-branch-policies?per_page=100" |
    jq -e '[.[].branch_policies[] | [.type,.name]] == [["branch","main"]]' >/dev/null
