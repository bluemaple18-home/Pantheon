#!/usr/bin/env bash
set -u

snapshot_name="${1:?snapshot name required}"
output_root="${2:?output root required}"
runtime_root="/Users/mattkuo/Documents/Pantheon-canary-runtime-v8"
actor_root="${runtime_root}/actor"
manifest="${runtime_root}/runtime-manifest.json"
queue_root="${runtime_root}/queue"
state_root="${runtime_root}/state"
transaction_root="${runtime_root}/transactions"
launch_root="/Users/mattkuo/Library/LaunchAgents"
stage_root="${launch_root}/.pantheon-four-lane-stage"
task_root="/Users/mattkuo/.codex/worktrees/6aacaadb-df6a-4dcf-b58e-5c51e2384677/Pantheon"
snapshot_root="${output_root}/${snapshot_name}"

labels=(
  com.pantheon.agy-content-publisher
  com.pantheon.agy-gemini-coordinator
  com.pantheon.agy-gemini-new
  com.pantheon.agy-gemini-rewrite
  com.pantheon.agy-gemini-i18n-new
  com.pantheon.agy-gemini-i18n-rewrite
  com.pantheon.content-capacity-guard
)

mkdir -p "${snapshot_root}/launchctl"

tree_manifest() {
  local root="$1"
  local output="$2"
  if [[ ! -e "${root}" ]]; then
    printf 'ABSENT\t%s\n' "${root}" > "${output}"
    return
  fi
  if [[ -f "${root}" ]]; then
    shasum -a 256 "${root}" > "${output}"
    return
  fi
  find "${root}" -type f -print0 \
    | sort -z \
    | xargs -0 shasum -a 256 > "${output}"
}

date -u +%Y-%m-%dT%H:%M:%SZ > "${snapshot_root}/timestamp.txt"
git -C "${actor_root}" rev-parse HEAD > "${snapshot_root}/actor-head.txt"
git -C "${actor_root}" status --porcelain=v1 --untracked-files=all > "${snapshot_root}/actor-status.txt"
git -C "${actor_root}" remote -v > "${snapshot_root}/actor-remotes.txt"
git -C "${actor_root}" show-ref > "${snapshot_root}/actor-git-refs.txt"
git -C "${task_root}" rev-parse HEAD > "${snapshot_root}/task-head.txt"
git -C "${task_root}" status --porcelain=v1 --untracked-files=all > "${snapshot_root}/task-status.txt"
git -C "${task_root}" show-ref > "${snapshot_root}/task-git-refs.txt"
git -C "${task_root}" rev-parse 'refs/tags/v0.3.370^{}' > "${snapshot_root}/release-tag-peeled.txt"

tree_manifest "${manifest}" "${snapshot_root}/manifest.sha256"
tree_manifest "${queue_root}" "${snapshot_root}/queue-tree.sha256"
tree_manifest "${state_root}" "${snapshot_root}/state-tree.sha256"
tree_manifest "${transaction_root}" "${snapshot_root}/transaction-tree.sha256"
tree_manifest "${state_root}/publisher.lock" "${snapshot_root}/publisher-lock.sha256"
tree_manifest "${stage_root}" "${snapshot_root}/stage-tree.sha256"

: > "${snapshot_root}/live-plists.sha256"
for label in "${labels[@]}"; do
  plist="${launch_root}/${label}.plist"
  if [[ -f "${plist}" ]]; then
    shasum -a 256 "${plist}" >> "${snapshot_root}/live-plists.sha256"
  else
    printf 'ABSENT\t%s\n' "${plist}" >> "${snapshot_root}/live-plists.sha256"
  fi
  launchctl print "gui/$(id -u)/${label}" > "${snapshot_root}/launchctl/${label}.txt" 2>&1 || true
done

jq '{schema_version,identity,manifest_digest,runtime_identity_digest,runtime_digest,config_version,generation,actor_root,queue_root,publisher_state_root,log_root,actor_head,python_executable,uv_executable}' \
  "${manifest}" > "${snapshot_root}/manifest-identity.json"

find "${state_root}" -maxdepth 1 -type f -name 'four-lane-activation-*.barrier' -print \
  | sort > "${snapshot_root}/barrier-paths.txt"
if [[ -s "${snapshot_root}/barrier-paths.txt" ]]; then
  while IFS= read -r barrier; do
    shasum -a 256 "${barrier}"
  done < "${snapshot_root}/barrier-paths.txt" > "${snapshot_root}/barriers.sha256"
else
  : > "${snapshot_root}/barriers.sha256"
fi

find "${snapshot_root}" -type f ! -name snapshot-digest.txt -print0 \
  | sort -z \
  | xargs -0 shasum -a 256 > "${snapshot_root}/snapshot-digest.txt"
