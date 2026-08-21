#!/usr/bin/env bash
set -euo pipefail

EVIDENCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME=/Users/mattkuo/Documents/Pantheon-canary-runtime-v8
ACTOR="${RUNTIME}/actor"
MANIFEST="${RUNTIME}/runtime-manifest.json"
QUEUE="${RUNTIME}/queue"
STATE="${RUNTIME}/state"
PYTHON=/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12
LAUNCH_DIR=/Users/mattkuo/Library/LaunchAgents
DIGEST=e3c393bb18a55eba1c8c6cb9e92abfb63b4241936dc78772bfaa5ec952177d32
HEAD=c05929f2a7dac86e94aaeaa5ab6c5455892f5f77
IDENTITY=db8c1691bb5433b23a4803743782d686d8779ef4fec5d5b7d1cb9e038092999e
GENERATION=g17-c05929f2a7-20260821T827804Z
RUN=auto-i18n-en-614aa4dc3542ab2c5637
LABELS=(
  com.pantheon.agy-content-publisher
  com.pantheon.agy-gemini-coordinator
  com.pantheon.agy-gemini-new
  com.pantheon.agy-gemini-rewrite
  com.pantheon.agy-gemini-i18n-new
  com.pantheon.agy-gemini-i18n-rewrite
  com.pantheon.content-capacity-guard
)

test "$(git -C "${ACTOR}" rev-parse HEAD)" = "${HEAD}"
test "$(git -C "${ACTOR}" ls-remote origin refs/heads/main | awk '{print $1}')" = "${HEAD}"
test -z "$(git -C "${ACTOR}" status --porcelain=v1)"
test "$(git -C "${ACTOR}" rev-parse "${HEAD}^{commit}")" = "${HEAD}"

test "$("${PYTHON}" -m scripts.pantheon_content_runtime_manifest field --manifest "${MANIFEST}" --expected-digest "${DIGEST}" --name actor_head)" = "${HEAD}"
test "$("${PYTHON}" -m scripts.pantheon_content_runtime_manifest field --manifest "${MANIFEST}" --expected-digest "${DIGEST}" --name runtime_identity_digest)" = "${IDENTITY}"
test "$("${PYTHON}" -m scripts.pantheon_content_runtime_manifest field --manifest "${MANIFEST}" --expected-digest "${DIGEST}" --name generation)" = "${GENERATION}"

aggregate_args=()
for label in "${LABELS[@]}"; do
  aggregate_args+=(--plist "${LAUNCH_DIR}/${label}.plist")
done
(
  cd "${ACTOR}"
  "${PYTHON}" -m scripts.pantheon_content_runtime_manifest aggregate \
    --manifest "${MANIFEST}" --expected-digest "${DIGEST}" \
    --activation-mode activation-only "${aggregate_args[@]}"
) > "${EVIDENCE}/live-aggregate-before.json"

mkdir -p "${EVIDENCE}/launchctl-before"
for label in "${LABELS[@]}"; do
  /bin/launchctl print "gui/$(id -u)/${label}" > "${EVIDENCE}/launchctl-before/${label}.txt"
  ! rg -q 'state = running|^[[:space:]]*pid = ' "${EVIDENCE}/launchctl-before/${label}.txt"
done

queue_count="$(find "${QUEUE}/runs" -mindepth 1 -maxdepth 1 -type f -name '*.json' | wc -l | tr -d ' ')"
exact_count="$(find "${QUEUE}" -type d -name "${RUN}" | wc -l | tr -d ' ')"
test "${queue_count}" = 140
test "${exact_count}" = 1
exact_path="$(find "${QUEUE}" -type d -name "${RUN}" -print)"
test -n "${exact_path}"
test "$(find "${exact_path}" -type f | wc -l | tr -d ' ')" -gt 0

PANTHEON_USER_HOME_DIR=/Users/mattkuo \
PANTHEON_PYTHON_PATH="${PYTHON}" \
PANTHEON_RUNTIME_MANIFEST_FILE="${MANIFEST}" \
PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST="${DIGEST}" \
/bin/bash "${ACTOR}/scripts/install_pantheon_content_capacity_guard_launchd.sh" --preflight \
  > "${EVIDENCE}/capacity-before.json"
rg -q '"status"[[:space:]]*:[[:space:]]*"PASS"' "${EVIDENCE}/capacity-before.json"

git -C "${ACTOR}" rev-parse HEAD > "${EVIDENCE}/actor-head-before.txt"
git -C "${ACTOR}" status --porcelain=v1 > "${EVIDENCE}/actor-status-before.txt"
git -C "${ACTOR}" ls-remote origin refs/heads/main | awk '{print $1}' > "${EVIDENCE}/origin-main-before.txt"
git -C "${ACTOR}" tag --list | sort > "${EVIDENCE}/tags-before.txt"
git -C "${ACTOR}" ls-remote --tags origin > "${EVIDENCE}/origin-tags-before.txt"
find "${QUEUE}" -type f -print | sort > "${EVIDENCE}/queue-before.txt"
find "${STATE}" -mindepth 1 -maxdepth 1 -print | sort > "${EVIDENCE}/state-before.txt"
find "${STATE}" -mindepth 1 -maxdepth 1 -type d -name 'transaction-*' -print | sort > "${EVIDENCE}/transactions-before.txt"
shasum -a 256 "${STATE}/ledger.json" > "${EVIDENCE}/ledger-before.sha256"
cp "${STATE}/ledger.json" "${EVIDENCE}/ledger-before.json"
find "${ACTOR}/app/web" -type f -print0 | sort -z | xargs -0 shasum -a 256 > "${EVIDENCE}/public-content-before.sha256"

printf '%s\n' \
  "queue_run_count=${queue_count}" \
  "exact_run_count=${exact_count}" \
  "exact_run_path=${exact_path}" \
  "capacity=PASS" \
  "actor_clean=true" \
  > "${EVIDENCE}/preflight-summary.txt"
