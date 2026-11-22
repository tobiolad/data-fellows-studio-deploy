#!/usr/bin/env bash
set -euo pipefail
operation="${1:?release operation required}"
group=rg-bizpilot-staging
app=ca-studio-staging
job=caj-studio-staging-migrate
registry=acrbizpilotstaging.azurecr.io
[[ "$(az account show --query id -o tsv)" == "${EXPECTED_SUBSCRIPTION:?}" ]]
resource() { az containerapp show -g "$group" -n "$app" -o json; }
require_digest() { [[ "$1" =~ ^sha256:[a-f0-9]{64}$ ]]; }
api_image() { require_digest "${API_DIGEST:?}" && printf '%s/studio/api@%s' "$registry" "$API_DIGEST"; }
web_image() { require_digest "${WEB_DIGEST:?}" && printf '%s/studio/web@%s' "$registry" "$WEB_DIGEST"; }
revision() {
  [[ "$1" == "$app"--* && "$1" =~ ^[a-z0-9-]+$ ]] || return 1
  az containerapp revision show -g "$group" -n "$app" --revision "$1" -o json
}
case "$operation" in
  preview)
    api="$(api_image)"; web="$(web_image)"
    # Emit only image changes. Environment variables, secret references and revision bodies stay private.
    current="$(resource)"
    jq -e '[.properties.template.containers[].name]|sort == ["api","web"]' <<<"$current" >/dev/null
    jq --arg api "$api" --arg web "$web" '[.properties.template.containers[] |
      {container:.name,current:.image,proposed:(if .name=="api" then $api else $web end)}]' <<<"$current"
    ;;
  migrate)
    image="$(api_image)"
    config="$(az containerapp job show -g "$group" -n "$job" -o json)"
    # Existing manual job, exact approved image and command, no overrides from dispatch.
    jq -e --arg image "$image" '.properties.configuration.triggerType=="Manual"
      and .properties.configuration.manualTriggerConfig.parallelism==1
      and (.properties.template.initContainers // [] | length)==0
      and (.properties.template.containers|length)==1
      and (.properties.template.containers[0] |
        .image==$image and .command==["python","-m","backend.migrate"] and ((.args // [])|length)==0)' <<<"$config" >/dev/null
    name="$(az containerapp job start -g "$group" -n "$job" --query name -o tsv)"
    [[ -n "$name" ]]
    for _ in $(seq 1 80); do
      state="$(az containerapp job execution show -g "$group" -n "$job" --job-execution-name "$name" --query properties.status -o tsv)"
      case "$state" in Succeeded) exit 0 ;; Failed|Stopped|Degraded) exit 1 ;; esac
      sleep 10
    done
    exit 1
    ;;
  verify)
    config="$(resource)"
    host="$(jq -er '.properties.configuration.ingress.fqdn' <<<"$config")"
    [[ "$host" == "${EXPECTED_STUDIO_HOST:?}" && "$host" =~ ^[a-z0-9.-]+$ ]]
    api="$(api_image)"; web="$(web_image)"
    live="$(jq -er '[.properties.configuration.ingress.traffic[]|select(.weight>0)] as $routes |
      if ($routes|length)==1 and $routes[0].weight==100 then
        (if $routes[0].latestRevision then .properties.latestReadyRevisionName else $routes[0].revisionName end)
      else error("Expected a single serving revision") end' <<<"$config")"
    jq -e --arg rev "$live" '[.properties.configuration.ingress.traffic[] | select(.weight>0)] |
      length==1 and .[0].weight==100 and (.[0].revisionName==$rev or .[0].latestRevision==true)' <<<"$config" >/dev/null
    revision "$live" | jq -e --arg api "$api" --arg web "$web" '
      .properties.healthState=="Healthy" and (.properties.template.containers|any(.name=="api" and .image==$api))
      and (.properties.template.containers|any(.name=="web" and .image==$web))' >/dev/null
    curl --proto '=https' --fail --silent --show-error --max-time 15 "https://$host/ready" |
      jq -e '.status=="ready" and .environment=="staging" and .persistence=="postgres" and .checks.schema_current==true' >/dev/null
    [[ "$(curl --proto '=https' --silent --show-error --max-time 15 -o /dev/null -w '%{http_code}' "https://$host/api/me")" == 401 ]]
    ;;
  rollback)
    config="$(resource)"
    [[ "${FROM_REVISION:?}" != "${TO_REVISION:?}" ]]
    jq -e --arg from "$FROM_REVISION" '.properties.configuration.activeRevisionsMode=="Multiple" and
      ([.properties.configuration.ingress.traffic[]|select(.weight>0)] |
       length==1 and .[0].weight==100 and .[0].revisionName==$from)' <<<"$config" >/dev/null
    revision "$FROM_REVISION" >/dev/null
    revision "$TO_REVISION" | jq -e '.properties.active==true and .properties.healthState=="Healthy"' >/dev/null
    az containerapp ingress traffic set -g "$group" -n "$app" --revision-weight "$TO_REVISION=100" "$FROM_REVISION=0" -o none
    resource | jq -e --arg to "$TO_REVISION" '[.properties.configuration.ingress.traffic[]|select(.weight>0)] |
      length==1 and .[0].weight==100 and .[0].revisionName==$to' >/dev/null
    ;;
  *) exit 2 ;;
esac
