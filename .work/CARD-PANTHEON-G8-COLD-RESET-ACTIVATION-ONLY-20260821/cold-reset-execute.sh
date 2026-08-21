#!/usr/bin/env bash
set -euo pipefail

ACTOR="/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor"
RUNTIME="/Users/mattkuo/Documents/Pantheon-canary-runtime-v8"
LAUNCH_DIR="/Users/mattkuo/Library/LaunchAgents"
STAGE="${LAUNCH_DIR}/.pantheon-four-lane-stage"
EVIDENCE="/Users/mattkuo/.codex/worktrees/6a6a/Pantheon/.work/CARD-PANTHEON-G8-COLD-RESET-ACTIVATION-ONLY-20260821"
BACKUP="${EVIDENCE}/backup-20260821T005814Z"
PYTHON="/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12"
MANIFEST="${RUNTIME}/runtime-manifest.json"
DIGEST="e3c393bb18a55eba1c8c6cb9e92abfb63b4241936dc78772bfaa5ec952177d32"
IDENTITY_DIGEST="db8c1691bb5433b23a4803743782d686d8779ef4fec5d5b7d1cb9e038092999e"
GENERATION="g17-c05929f2a7-20260821T827804Z"
HEAD="c05929f2a7dac86e94aaeaa5ab6c5455892f5f77"
EXACT_RUN="auto-i18n-en-614aa4dc3542ab2c5637"
UID_VALUE="501"
LABELS=(
  com.pantheon.agy-content-publisher
  com.pantheon.agy-gemini-coordinator
  com.pantheon.agy-gemini-new
  com.pantheon.agy-gemini-rewrite
  com.pantheon.agy-gemini-i18n-new
  com.pantheon.agy-gemini-i18n-rewrite
  com.pantheon.content-capacity-guard
)

mkdir -p "${BACKUP}/copied-live" "${BACKUP}/moved-live" \
  "${BACKUP}/failed-new" "${BACKUP}/launchctl-before" \
  "${BACKUP}/launchctl-after" "${BACKUP}/rollback"

tree_digest() {
  find "$1" -type f -print0 | sort -z | xargs -0 shasum -a 256 \
    | shasum -a 256 | awk '{print $1}'
}

snapshot_protected() {
  local output="$1"
  local refs
  refs="$(git -C "${ACTOR}" show-ref | shasum -a 256 | awk '{print $1}')"
  printf '{\n' > "${output}"
  printf '  "queue": "%s",\n' "$(tree_digest "${RUNTIME}/queue")" >> "${output}"
  printf '  "state": "%s",\n' "$(tree_digest "${RUNTIME}/state")" >> "${output}"
  printf '  "transactions": "%s",\n' "$(tree_digest "${RUNTIME}/transactions")" >> "${output}"
  printf '  "public_artifacts": "%s",\n' "$(tree_digest "${ACTOR}/app/web/static")" >> "${output}"
  printf '  "manifest": "%s",\n' "$(shasum -a 256 "${MANIFEST}" | awk '{print $1}')" >> "${output}"
  printf '  "actor_refs": "%s",\n' "${refs}" >> "${output}"
  printf '  "queue_run_count": %s,\n' "$(find "${RUNTIME}/queue/runs" -maxdepth 1 -type f -name '*.json' | wc -l | tr -d ' ')" >> "${output}"
  printf '  "exact_run_directory_count": %s,\n' "$(find "${RUNTIME}/queue" -type d -name "${EXACT_RUN}" | wc -l | tr -d ' ')" >> "${output}"
  printf '  "transaction_directory_count": %s\n' "$(find "${RUNTIME}/transactions" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" >> "${output}"
  printf '}\n' >> "${output}"
}

rollback_once() {
  set +e
  printf '%s\n' "rollback-started" > "${EVIDENCE}/rollback-status.txt"
  for label in "${LABELS[@]}"; do
    /bin/launchctl bootout "gui/${UID_VALUE}/${label}" \
      > "${BACKUP}/rollback/${label}.bootout.stdout" \
      2> "${BACKUP}/rollback/${label}.bootout.stderr"
    printf '%s\n' "$?" > "${BACKUP}/rollback/${label}.bootout.exit"
  done
  for label in "${LABELS[@]}"; do
    live="${LAUNCH_DIR}/${label}.plist"
    old="${BACKUP}/moved-live/${label}.plist"
    if [[ -f "${live}" ]]; then
      mv "${live}" "${BACKUP}/failed-new/${label}.plist"
    fi
    if [[ -f "${old}" ]]; then
      mv "${old}" "${live}"
    else
      cp -p "${BACKUP}/copied-live/${label}.plist" "${live}"
    fi
  done
  for label in "${LABELS[@]}"; do
    /bin/launchctl bootstrap "gui/${UID_VALUE}" "${LAUNCH_DIR}/${label}.plist" \
      > "${BACKUP}/rollback/${label}.bootstrap.stdout" \
      2> "${BACKUP}/rollback/${label}.bootstrap.stderr"
    printf '%s\n' "$?" > "${BACKUP}/rollback/${label}.bootstrap.exit"
  done
  printf '%s\n' "rollback-complete" > "${EVIDENCE}/rollback-status.txt"
  set -e
}

if [[ "$(git -C "${ACTOR}" rev-parse HEAD)" != "${HEAD}" \
  || -n "$(git -C "${ACTOR}" status --porcelain=v1)" \
  || "$(cat "${STAGE}/manifest-digest")" != "${DIGEST}" \
  || "$(cat "${STAGE}/generation")" != "${GENERATION}" \
  || "$(cat "${STAGE}/publisher-exact-run-id")" != "${EXACT_RUN}" \
  || "$(find "${STAGE}" -maxdepth 1 -type f -name '*.plist' | wc -l | tr -d ' ')" != "7" ]]; then
  printf '%s\n' "BLOCKED / NO RESET" > "${EVIDENCE}/terminal-state.txt"
  exit 10
fi

snapshot_protected "${EVIDENCE}/before-protected.json"
for label in "${LABELS[@]}"; do
  live="${LAUNCH_DIR}/${label}.plist"
  [[ -f "${live}" ]] || { printf '%s\n' "BLOCKED / NO RESET" > "${EVIDENCE}/terminal-state.txt"; exit 11; }
  cp -p "${live}" "${BACKUP}/copied-live/${label}.plist"
  /bin/launchctl print "gui/${UID_VALUE}/${label}" \
    > "${BACKUP}/launchctl-before/${label}.txt" 2>&1
done
shasum -a 256 "${BACKUP}/copied-live/"*.plist > "${EVIDENCE}/before-live-sha256.txt"

bootout_failed=0
for label in "${LABELS[@]}"; do
  set +e
  /bin/launchctl bootout "gui/${UID_VALUE}/${label}" \
    > "${EVIDENCE}/${label}.bootout.stdout" \
    2> "${EVIDENCE}/${label}.bootout.stderr"
  code="$?"
  set -e
  printf '%s\n' "${code}" > "${EVIDENCE}/${label}.bootout.exit"
  if [[ "${code}" != "0" ]] \
    && ! grep -Eq 'Could not find service|No such process' "${EVIDENCE}/${label}.bootout.stderr"; then
    bootout_failed=1
  fi
done
if [[ "${bootout_failed}" == "1" ]]; then
  rollback_once
  printf '%s\n' "BLOCKED / ROLLED BACK" > "${EVIDENCE}/terminal-state.txt"
  exit 20
fi

for label in "${LABELS[@]}"; do
  mv "${LAUNCH_DIR}/${label}.plist" "${BACKUP}/moved-live/${label}.plist"
done

set +e
env \
  TMPDIR=/private/tmp \
  PANTHEON_USER_HOME_DIR=/Users/mattkuo \
  PANTHEON_PYTHON_PATH="${PYTHON}" \
  PANTHEON_RUNTIME_MANIFEST_FILE="${MANIFEST}" \
  PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST="${DIGEST}" \
  bash "${ACTOR}/scripts/install_agy_gemini_coordinator_launchd.sh" --activate-only \
  > "${EVIDENCE}/activation.stdout" \
  2> "${EVIDENCE}/activation.stderr"
activation_code="$?"
set -e
printf '%s\n' "${activation_code}" > "${EVIDENCE}/activation.exit"
if [[ "${activation_code}" != "0" ]]; then
  rollback_once
  printf '%s\n' "BLOCKED / ROLLED BACK" > "${EVIDENCE}/terminal-state.txt"
  exit 21
fi

aggregate_args=()
for label in "${LABELS[@]}"; do
  aggregate_args+=(--plist "${LAUNCH_DIR}/${label}.plist")
done
"${PYTHON}" -m scripts.pantheon_content_runtime_manifest aggregate \
  --manifest "${MANIFEST}" --expected-digest "${DIGEST}" \
  --activation-mode activation-only "${aggregate_args[@]}" \
  > "${EVIDENCE}/aggregate.json"
"${PYTHON}" -m scripts.pantheon_content_runtime_manifest barrier-validate \
  --barrier "${RUNTIME}/state/four-lane-activation-${GENERATION}.barrier" \
  --manifest "${MANIFEST}" --expected-digest "${DIGEST}" \
  > "${EVIDENCE}/barrier.json"

post_failed=0
for label in "${LABELS[@]}"; do
  set +e
  /bin/launchctl print "gui/${UID_VALUE}/${label}" \
    > "${BACKUP}/launchctl-after/${label}.txt" 2>&1
  code="$?"
  set -e
  if [[ "${code}" != "0" ]] \
    || grep -q 'state = running' "${BACKUP}/launchctl-after/${label}.txt" \
    || grep -q '^[[:space:]]*pid = ' "${BACKUP}/launchctl-after/${label}.txt"; then
    post_failed=1
  fi
done

set +e
"${PYTHON}" -c '
import plistlib, sys
from pathlib import Path
launch = Path(sys.argv[1]); digest, identity, generation, head = sys.argv[2:6]
labels = sys.argv[6:]
for label in labels:
    with (launch / f"{label}.plist").open("rb") as stream:
        payload = plistlib.load(stream)
    env = payload.get("EnvironmentVariables", {})
    args = payload.get("ProgramArguments", [])
    separator = args.index("--")
    assert payload.get("Label") == label
    assert env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST") == digest
    assert env.get("PANTHEON_RUNTIME_IDENTITY_DIGEST") == identity
    assert env.get("PANTHEON_RUNTIME_GENERATION") == generation
    assert env.get("PANTHEON_RUNTIME_ACTOR_HEAD") == head
    assert args[:separator].count("--activation-only") == 1
    assert "--activation-only" not in args[separator + 1:]
' "${LAUNCH_DIR}" "${DIGEST}" "${IDENTITY_DIGEST}" "${GENERATION}" "${HEAD}" "${LABELS[@]}" \
  > "${EVIDENCE}/live-identity.stdout" 2> "${EVIDENCE}/live-identity.stderr"
identity_code="$?"
set -e
if [[ "${identity_code}" != "0" ]]; then
  post_failed=1
fi

snapshot_protected "${EVIDENCE}/after-protected.json"
if ! cmp -s "${EVIDENCE}/before-protected.json" "${EVIDENCE}/after-protected.json"; then
  post_failed=1
fi
if [[ "${post_failed}" == "1" ]]; then
  rollback_once
  printf '%s\n' "BLOCKED / ROLLED BACK" > "${EVIDENCE}/terminal-state.txt"
  exit 22
fi

shasum -a 256 "${LAUNCH_DIR}/"com.pantheon.agy-content-publisher.plist \
  "${LAUNCH_DIR}/"com.pantheon.agy-gemini-coordinator.plist \
  "${LAUNCH_DIR}/"com.pantheon.agy-gemini-new.plist \
  "${LAUNCH_DIR}/"com.pantheon.agy-gemini-rewrite.plist \
  "${LAUNCH_DIR}/"com.pantheon.agy-gemini-i18n-new.plist \
  "${LAUNCH_DIR}/"com.pantheon.agy-gemini-i18n-rewrite.plist \
  "${LAUNCH_DIR}/"com.pantheon.content-capacity-guard.plist \
  > "${EVIDENCE}/after-live-sha256.txt"
printf '%s\n' "REBUILT / NO CANARY" > "${EVIDENCE}/terminal-state.txt"
printf '%s\n' "cold-reset-calls=1" "activation-calls=1" \
  "publisher-child-invocations=0" "canary-calls=0" "retry-calls=0" \
  > "${EVIDENCE}/exact-counts.txt"
