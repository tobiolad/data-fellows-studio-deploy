#!/usr/bin/env bash
# Local CLI fixtures for the release commands. This test has no cloud dependency.
set -euo pipefail
export EXPECTED_SUBSCRIPTION=synthetic EXPECTED_STUDIO_HOST=studio.example
export API_DIGEST="sha256:$(printf 'a%.0s' {1..64})" WEB_DIGEST="sha256:$(printf 'b%.0s' {1..64})"
export FROM_REVISION=ca-studio-staging--one TO_REVISION=ca-studio-staging--two
fixture_dir="$(mktemp -d)"
export fixture_dir
trap 'rm -rf "$fixture_dir"' EXIT
export api="acrbizpilotstaging.azurecr.io/studio/api@$API_DIGEST" web="acrbizpilotstaging.azurecr.io/studio/web@$WEB_DIGEST"
export source_revision="$FROM_REVISION" health=Healthy job_env=staging anonymous=401 protected=true
az() {
    case "$1 $2 ${3:-}" in
        "account show "*) echo "$EXPECTED_SUBSCRIPTION" ;;
        "containerapp show "*)
            jq -n --arg rev "$source_revision" --arg api "$api" --arg web "$web" '{properties:{
              configuration:{ingress:{fqdn:"studio.example",traffic:[{revisionName:$rev,weight:100}]},activeRevisionsMode:"Multiple"},
              template:{containers:[{name:"api",image:$api},{name:"web",image:$web}]}}}' ;;
        "containerapp revision show")
            jq -n --arg health "$health" --arg api "$api" --arg web "$web" '{properties:{active:true,healthState:$health,
              template:{containers:[{name:"api",image:$api},{name:"web",image:$web}]}}}' ;;
        "containerapp job show")
            jq -n --arg api "$api" --arg env "$job_env" '{properties:{configuration:{triggerType:"Manual",manualTriggerConfig:{parallelism:1}},
              template:{containers:[{image:$api,command:["python","-m","backend.migrate"],env:[
                {name:"STUDIO_ENV",value:$env},{name:"STUDIO_DATABASE_URL",secretRef:"studio-migration-dsn"}]}]}}}' ;;
        "containerapp job start") echo start >>"$fixture_dir/jobs"; echo fixture ;;
        "containerapp job execution") echo Succeeded ;;
        "containerapp ingress traffic") source_revision="$TO_REVISION"; echo traffic >>"$fixture_dir/traffic" ;;
        *) return 1 ;;
    esac
}
curl() {
    case "$*" in
        */ready) echo '{"status":"ready","environment":"staging","persistence":"postgres","checks":{"schema_current":true}}' ;;
        */api/me) echo "$anonymous" ;;
        *) return 1 ;;
    esac
}
gh() {
    case "$*" in
        *branches/main*) echo "$protected" ;;
        *deployment-branch-policies*) echo '[{"branch_policies":[{"type":"branch","name":"main"}]}]' ;;
        *environments/studio-build*) echo '{"protection_rules":[{"type":"required_reviewers","reviewers":[1],"prevent_self_review":true}],"deployment_branch_policy":{"custom_branch_policies":true}}' ;;
        *) return 1 ;;
    esac
}
export -f az curl gh
deny() { if "$@" > /dev/null 2>&1; then echo "Expected rejection of $*" >&2; exit 1; fi; }
export GITHUB_REF=refs/heads/main GITHUB_EVENT_NAME=workflow_dispatch GITHUB_REPOSITORY=example/studio
ops/check-release-environment.sh studio-build
protected=false deny ops/check-release-environment.sh studio-build
ops/staging-release.sh preview > /dev/null
API_DIGEST=latest deny ops/staging-release.sh preview
ops/staging-release.sh migrate
job_env=development deny ops/staging-release.sh migrate
[[ "$(wc -l <"$fixture_dir/jobs")" == 1 ]]
ops/staging-release.sh verify
anonymous=200 deny ops/staging-release.sh verify
ops/staging-release.sh rollback
health=Degraded deny ops/staging-release.sh rollback
source_revision="$TO_REVISION" deny ops/staging-release.sh rollback
[[ "$(wc -l <"$fixture_dir/traffic")" == 1 ]]
echo 'Passed protected-environment, preview, migration, verification and rollback CLI fixtures.'
