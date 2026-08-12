#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ACTION="${1:---install}"
USER_NAME="$(id -un)"
USER_ID="$(id -u)"
USER_HOME_DIR="${PANTHEON_USER_HOME_DIR:-}"
if [[ -z "${USER_HOME_DIR}" ]]; then
  USER_HOME_DIR="$(dscl . -read "/Users/${USER_NAME}" NFSHomeDirectory | awk '{print $2}')"
fi
if [[ "${USER_HOME_DIR}" != /* ]]; then
  echo "Pantheon user home 必須使用 absolute path。" >&2
  exit 1
fi
PYTHON_PATH="${PANTHEON_PYTHON_PATH:-${REPO_ROOT}/.venv/bin/python}"
RUNTIME_MANIFEST_FILE="${PANTHEON_RUNTIME_MANIFEST_FILE:-${REPO_ROOT}/.work/pantheon-content-runtime-manifest.json}"
EXPECTED_RUNTIME_MANIFEST_DIGEST="${PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST:-}"
AGY_CLI_PATH="${AGY_GEMINI_CLI_PATH:-${USER_HOME_DIR}/.antigravity/bin/agy-1.1.3}"
PRODUCTION_POOL_FILE="${AGY_GEMINI_CREDENTIAL_POOL_FILE:-}"
WRITER_MODEL="${AGY_WRITER_MODEL:-}"
REVIEWER_MODEL="${AGY_REVIEWER_MODEL:-}"
NEW_ONLY="${AGY_GEMINI_NEW_ONLY:-0}"
RATE_LIMIT_COOLDOWN_SECONDS="${AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS:-300}"
GSC_COPY_ROOT="${PANTHEON_GSC_COPY_ROOT:-${REPO_ROOT}/.work/gsc-copy}"
LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin}"
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-coordinator.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example"
LANE_TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-gemini-lane.plist.example"
TEMP_PLIST=""
LANE_TEMP_PLISTS=()
LANE_TARGET_PLISTS=()
ACTIVATION_BARRIER=""
STAGE_DIR="${LAUNCH_AGENTS_DIR}/.pantheon-four-lane-stage"

cleanup() {
  local RETURN_CODE="$?"
  if [[ -n "${TEMP_PLIST}" ]]; then
    rm -f "${TEMP_PLIST}"
  fi
  if (( ${#LANE_TEMP_PLISTS[@]} > 0 )); then
    for LANE_TEMP_PLIST in "${LANE_TEMP_PLISTS[@]}"; do
      rm -f "${LANE_TEMP_PLIST}"
    done
  fi
  return "${RETURN_CODE}"
}
trap cleanup EXIT

if [[ "${ACTION}" != "--install" && "${ACTION}" != "--preflight" \
  && "${ACTION}" != "--activate" ]]; then
  echo "用法：scripts/install_agy_gemini_coordinator_launchd.sh [--preflight|--install|--activate]" >&2
  exit 2
fi
if [[ ! -x "${PYTHON_PATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
  exit 1
fi
if [[ ! -x "${AGY_CLI_PATH}" ]]; then
  echo "找不到 Gemini CLI：${AGY_CLI_PATH}" >&2
  exit 1
fi
if [[ -n "${WRITER_MODEL}" && ! "${WRITER_MODEL}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "AGY_WRITER_MODEL 只能使用 model identifier 安全字元。" >&2
  exit 1
fi
if [[ -n "${REVIEWER_MODEL}" && ! "${REVIEWER_MODEL}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "AGY_REVIEWER_MODEL 只能使用 model identifier 安全字元。" >&2
  exit 1
fi
if [[ "${NEW_ONLY}" != "0" && "${NEW_ONLY}" != "1" ]]; then
  echo "AGY_GEMINI_NEW_ONLY 只能是 0 或 1。" >&2
  exit 1
fi
if [[ "${NEW_ONLY}" == "1" ]]; then
  echo "四軌 recovery 禁止 new-only；請改用獨立 maintenance 入口。" >&2
  exit 1
fi
if [[ -n "${PRODUCTION_POOL_FILE}" && "${PRODUCTION_POOL_FILE}" != /* ]]; then
  echo "Production Gemini credential pool 必須使用 absolute path。" >&2
  exit 1
fi
if [[ -n "${AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE:-}" \
  && "${AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE}" != /* ]]; then
  echo "Production Gemini allocator state path 必須使用 absolute path。" >&2
  exit 1
fi
if [[ ! "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "缺少 exact runtime manifest expected digest。" >&2
  exit 1
fi
(
  cd "${REPO_ROOT}"
  "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest validate \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}"
) >/dev/null
manifest_field() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest field \
      --manifest "${RUNTIME_MANIFEST_FILE}" \
      --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" --name "$1"
  )
}
optional_manifest_field() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest field \
      --manifest "${RUNTIME_MANIFEST_FILE}" \
      --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" --name "$1" --optional
  )
}
ACTOR_ROOT="$(manifest_field actor_root)"
QUEUE_ROOT="$(manifest_field queue_root)"
CONTENT_PUBLISHER_ROOT="$(manifest_field publisher_state_root)"
LOG_DIR="$(manifest_field log_root)"
RUNTIME_MANIFEST_DIGEST="$(manifest_field manifest_digest)"
RUNTIME_IDENTITY="$(manifest_field identity)"
RUNTIME_IDENTITY_DIGEST="$(manifest_field runtime_identity_digest)"
RUNTIME_CODE_DIGEST="$(manifest_field runtime_digest)"
RUNTIME_CONFIG_VERSION="$(manifest_field config_version)"
RUNTIME_GENERATION="$(manifest_field generation)"
RUNTIME_ACTOR_HEAD="$(optional_manifest_field actor_head)"
RUNTIME_PYTHON_EXECUTABLE="$(optional_manifest_field python_executable)"
add_hardened_runtime_identity() {
  local PLIST_PATH="$1"
  if [[ -n "${RUNTIME_ACTOR_HEAD}" ]]; then
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_ACTOR_HEAD string ${RUNTIME_ACTOR_HEAD}" "${PLIST_PATH}"
  fi
  if [[ -n "${RUNTIME_PYTHON_EXECUTABLE}" ]]; then
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_PYTHON_EXECUTABLE string ${RUNTIME_PYTHON_EXECUTABLE}" "${PLIST_PATH}"
  fi
}
ACTIVATION_BARRIER="${CONTENT_PUBLISHER_ROOT}/four-lane-activation-${RUNTIME_GENERATION}.barrier"
READY_ROOT="${STAGE_DIR}/readiness/${RUNTIME_GENERATION}"
PRODUCTION_STATE_FILE="${AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE:-${QUEUE_ROOT}/production-credential-pool-state.json}"
if [[ "${ACTOR_ROOT}" != "${REPO_ROOT}" ]]; then
  echo "runtime manifest actor root 與 coordinator installer 不一致。" >&2
  exit 1
fi
for LEGACY_QUEUE_ROOT in "${AGY_GEMINI_QUEUE_ROOT:-}" "${PANTHEON_GEMINI_QUEUE_ROOT:-}"; do
  if [[ -n "${LEGACY_QUEUE_ROOT}" && "${LEGACY_QUEUE_ROOT}" != "${QUEUE_ROOT}" ]]; then
    echo "runtime manifest queue root 與 legacy override 不一致。" >&2
    exit 1
  fi
done
if [[ -n "${PANTHEON_CONTENT_PUBLISHER_ROOT:-}" \
  && "${PANTHEON_CONTENT_PUBLISHER_ROOT}" != "${CONTENT_PUBLISHER_ROOT}" ]]; then
  echo "runtime manifest publisher state root 與 legacy override 不一致。" >&2
  exit 1
fi
if [[ ! "${RATE_LIMIT_COOLDOWN_SECONDS}" =~ ^[1-9][0-9]{0,3}$ ]] \
  || (( 10#${RATE_LIMIT_COOLDOWN_SECONDS} > 3600 )); then
  echo "AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS 必須介於 1 與 3600。" >&2
  exit 1
fi
if [[ "${QUEUE_ROOT}" != /* || "${GSC_COPY_ROOT}" != /* || "${CONTENT_PUBLISHER_ROOT}" != /* ]]; then
  echo "Pantheon queue、GSC copy 與 publisher state root 必須使用 absolute path。" >&2
  exit 1
fi
if [[ -n "${PRODUCTION_POOL_FILE}" ]]; then
  if [[ "${PRODUCTION_POOL_FILE}" != /* ]]; then
    echo "Production Gemini credential pool 必須使用 absolute path。" >&2
    exit 1
  fi
  if [[ "${PRODUCTION_STATE_FILE}" != /* ]]; then
    echo "Production Gemini allocator state path 必須使用 absolute path。" >&2
    exit 1
  fi
  if ! (
    cd "${REPO_ROOT}"
    "${PYTHON_PATH}" -m scripts.agy_gemini_runner \
      --queue-root "${QUEUE_ROOT}" \
      validate-production-installation \
      --pool-file "${PRODUCTION_POOL_FILE}" \
      --state-file "${PRODUCTION_STATE_FILE}"
  ) >/dev/null; then
    echo "Production Gemini pool/allocator metadata 驗證失敗。" >&2
    exit 1
  fi
fi
if launchctl print "gui/${USER_ID}/com.pantheon.agy-gemini-runner" >/dev/null 2>&1; then
  echo "偵測到舊版 standalone runner；請先停止 com.pantheon.agy-gemini-runner，避免兩個服務競爭 queue。" >&2
  exit 1
fi

TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-gemini-coordinator.XXXXXX")"
cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:5 ${ACTIVATION_BARRIER}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:7 ${RUNTIME_MANIFEST_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:9 ${RUNTIME_MANIFEST_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${READY_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:17 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:21 ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:23 ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:25 ${GSC_COPY_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:28 ${CONTENT_PUBLISHER_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:30 ${GSC_COPY_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_CLI ${AGY_CLI_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_NEW_ONLY ${NEW_ONLY}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS ${RATE_LIMIT_COOLDOWN_SECONDS}" "${TEMP_PLIST}"
if [[ -n "${PRODUCTION_POOL_FILE}" ]]; then
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_FILE string ${PRODUCTION_POOL_FILE}" "${TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE string ${PRODUCTION_STATE_FILE}" "${TEMP_PLIST}"
fi
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST_DIGEST ${RUNTIME_MANIFEST_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST ${RUNTIME_MANIFEST_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY_DIGEST ${RUNTIME_IDENTITY_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_CODE_DIGEST ${RUNTIME_CODE_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_CONFIG_VERSION ${RUNTIME_CONFIG_VERSION}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_GENERATION ${RUNTIME_GENERATION}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY ${RUNTIME_IDENTITY}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_ACTOR_ROOT ${ACTOR_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_QUEUE_ROOT ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT ${CONTENT_PUBLISHER_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_LOG_ROOT ${LOG_DIR}" "${TEMP_PLIST}"
add_hardened_runtime_identity "${TEMP_PLIST}"
if [[ -n "${WRITER_MODEL}" ]]; then
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_WRITER_MODEL string ${WRITER_MODEL}" "${TEMP_PLIST}"
fi
if [[ -n "${REVIEWER_MODEL}" ]]; then
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_REVIEWER_MODEL string ${REVIEWER_MODEL}" "${TEMP_PLIST}"
fi
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/agy-gemini-coordinator.stdout.log" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/agy-gemini-coordinator.stderr.log" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null

for LANE in new rewrite i18n-new i18n-rewrite; do
  LANE_LABEL="com.pantheon.agy-gemini-${LANE}"
  LANE_TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-gemini-${LANE}.XXXXXX")"
  LANE_TEMP_PLISTS+=("${LANE_TEMP_PLIST}")
  LANE_TARGET_PLISTS+=("${LAUNCH_AGENTS_DIR}/${LANE_LABEL}.plist")
  cp "${LANE_TEMPLATE_PLIST}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :Label ${LANE_LABEL}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:5 ${ACTIVATION_BARRIER}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:7 ${RUNTIME_MANIFEST_DIGEST}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:9 ${RUNTIME_MANIFEST_FILE}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:11 ${LANE_LABEL}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${READY_ROOT}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:17 ${PYTHON_PATH}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:21 ${QUEUE_ROOT}/lanes/${LANE}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:23 ${LANE}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_CLI ${AGY_CLI_PATH}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_NEW_ONLY ${NEW_ONLY}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS ${RATE_LIMIT_COOLDOWN_SECONDS}" "${LANE_TEMP_PLIST}"
  if [[ -n "${PRODUCTION_POOL_FILE}" ]]; then
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_FILE string ${PRODUCTION_POOL_FILE}" "${LANE_TEMP_PLIST}"
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE string ${PRODUCTION_STATE_FILE}" "${LANE_TEMP_PLIST}"
  fi
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST_DIGEST ${RUNTIME_MANIFEST_DIGEST}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST ${RUNTIME_MANIFEST_FILE}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_SERVICE_LABEL ${LANE_LABEL}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY_DIGEST ${RUNTIME_IDENTITY_DIGEST}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_CODE_DIGEST ${RUNTIME_CODE_DIGEST}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_CONFIG_VERSION ${RUNTIME_CONFIG_VERSION}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_GENERATION ${RUNTIME_GENERATION}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY ${RUNTIME_IDENTITY}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_ACTOR_ROOT ${ACTOR_ROOT}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_QUEUE_ROOT ${QUEUE_ROOT}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT ${CONTENT_PUBLISHER_ROOT}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_LOG_ROOT ${LOG_DIR}" "${LANE_TEMP_PLIST}"
  add_hardened_runtime_identity "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/agy-gemini-${LANE}.stdout.log" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/agy-gemini-${LANE}.stderr.log" "${LANE_TEMP_PLIST}"
  plutil -lint "${LANE_TEMP_PLIST}" >/dev/null
done

if [[ "${ACTION}" == "--preflight" ]]; then
  echo "Pantheon Gemini coordinator 與四條 lane runner preflight 通過。"
  exit 0
fi

COORDINATOR_LABELS=(
  "com.pantheon.agy-gemini-coordinator"
  "com.pantheon.agy-gemini-new"
  "com.pantheon.agy-gemini-rewrite"
  "com.pantheon.agy-gemini-i18n-new"
  "com.pantheon.agy-gemini-i18n-rewrite"
)
TEMP_PLISTS=("${TEMP_PLIST}" "${LANE_TEMP_PLISTS[@]}")
LABELS=(
  "${COORDINATOR_LABELS[@]}"
  "com.pantheon.agy-content-publisher"
  "com.pantheon.content-capacity-guard"
)
TARGET_PLISTS=(
  "${TARGET_PLIST}"
  "${LANE_TARGET_PLISTS[@]}"
  "${LAUNCH_AGENTS_DIR}/com.pantheon.agy-content-publisher.plist"
  "${LAUNCH_AGENTS_DIR}/com.pantheon.content-capacity-guard.plist"
)
STAGED_PLISTS=()
for LABEL in "${LABELS[@]}"; do
  STAGED_PLISTS+=("${STAGE_DIR}/${LABEL}.plist")
done

if [[ "${ACTION}" == "--install" ]]; then
  mkdir -p "${STAGE_DIR}"
  rm -f "${STAGE_DIR}/failure-receipt.json"
  for INDEX in 0 1 2 3 4; do
    install -m 600 "${TEMP_PLISTS[${INDEX}]}" "${STAGED_PLISTS[${INDEX}]}"
  done
  printf '%s\n' "${RUNTIME_MANIFEST_DIGEST}" > "${STAGE_DIR}/manifest-digest"
  printf '%s\n' "${RUNTIME_GENERATION}" > "${STAGE_DIR}/generation"
  echo "Pantheon Gemini coordinator 與四條 lane plist 已寫入 private stage；尚未 activation。"
  exit 0
fi

if [[ ! -d "${STAGE_DIR}" \
  || "$(cat "${STAGE_DIR}/manifest-digest" 2>/dev/null || true)" != "${RUNTIME_MANIFEST_DIGEST}" \
  || "$(cat "${STAGE_DIR}/generation" 2>/dev/null || true)" != "${RUNTIME_GENERATION}" ]]; then
  echo "找不到 matching aggregate stage receipt，拒絕 activation。" >&2
  exit 1
fi
AGGREGATE_ARGS=()
for STAGED_PLIST in "${STAGED_PLISTS[@]}"; do
  AGGREGATE_ARGS+=(--plist "${STAGED_PLIST}")
done
(
  cd "${REPO_ROOT}"
  "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest aggregate \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
    "${AGGREGATE_ARGS[@]}"
)

STARTED_LABELS=()
normalize_control_identity() {
  sed -E '/^[[:space:]]*(state|pid|runs|last exit code|last terminating signal|successful exits|forks|execs|initialized|trampolined|started|proxy started) = /d' "$1"
}
rollback_activation() {
  local RETURN_CODE="$1"
  local ROLLBACK_FAILED=0
  trap - ERR
  set +e
  rm -f "${ACTIVATION_BARRIER}" || ROLLBACK_FAILED=1
  for LABEL in "${STARTED_LABELS[@]}"; do
    if ! launchctl bootout "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      ROLLBACK_FAILED=1
    fi
    if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      ROLLBACK_FAILED=1
    fi
  done
  for INDEX in 0 1 2 3 4 5 6; do
    LABEL="${LABELS[${INDEX}]}"
    TARGET="${TARGET_PLISTS[${INDEX}]}"
    if [[ -f "${STAGE_DIR}/backups/${LABEL}.plist" ]]; then
      install -m 600 "${STAGE_DIR}/backups/${LABEL}.plist" "${TARGET}" || ROLLBACK_FAILED=1
      cmp -s "${STAGE_DIR}/backups/${LABEL}.plist" "${TARGET}" || ROLLBACK_FAILED=1
    else
      rm -f "${TARGET}" || ROLLBACK_FAILED=1
      [[ ! -e "${TARGET}" ]] || ROLLBACK_FAILED=1
    fi
    if [[ "$(cat "${STAGE_DIR}/${LABEL}.previous_loaded")" == "1" \
      && -f "${TARGET}" ]]; then
      if ! launchctl bootstrap "gui/${USER_ID}" "${TARGET}" >/dev/null 2>&1 \
        || ! launchctl print "gui/${USER_ID}/${LABEL}" \
          > "${STAGE_DIR}/${LABEL}.actual_identity" 2>/dev/null; then
        ROLLBACK_FAILED=1
      else
        normalize_control_identity "${STAGE_DIR}/${LABEL}.actual_identity" \
          > "${STAGE_DIR}/${LABEL}.actual_identity.stable"
        cmp -s "${STAGE_DIR}/${LABEL}.previous_identity.stable" \
          "${STAGE_DIR}/${LABEL}.actual_identity.stable" || ROLLBACK_FAILED=1
      fi
    elif launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      ROLLBACK_FAILED=1
    fi
  done
  if [[ -f "${STAGE_DIR}/previous-barrier" ]]; then
    PREVIOUS_BARRIER_PATH="$(cat "${STAGE_DIR}/previous-barrier-path")"
    install -m 600 "${STAGE_DIR}/previous-barrier" "${PREVIOUS_BARRIER_PATH}" \
      || ROLLBACK_FAILED=1
    if ! (cd "${REPO_ROOT}" && "${PYTHON_PATH}" -m \
      scripts.pantheon_content_runtime_manifest barrier-validate \
      --barrier "${PREVIOUS_BARRIER_PATH}" \
      --manifest "${STAGE_DIR}/previous-runtime-manifest.json" \
      --expected-digest "$(cat "${STAGE_DIR}/previous-manifest-digest")") \
      >/dev/null; then
      ROLLBACK_FAILED=1
    fi
  elif grep -q '^1$' "${STAGE_DIR}"/*.previous_loaded; then
    ROLLBACK_FAILED=1
  fi
  if [[ "${ROLLBACK_FAILED}" == "1" ]]; then
    ROLLBACK_STATUS="ROLLBACK_FAILED"
  else
    ROLLBACK_STATUS="ROLLBACK_COMPLETE"
  fi
  printf '{"status":"%s","failed":true,"manifest_digest":"%s"}\n' \
    "${ROLLBACK_STATUS}" "${RUNTIME_MANIFEST_DIGEST}" > "${STAGE_DIR}/failure-receipt.json"
  exit "${RETURN_CODE}"
}

# aggregate activation 前才 snapshot live config/state；stage 不碰 live target 或 barrier。
rm -rf "${STAGE_DIR}/backups"
mkdir -p "${STAGE_DIR}/backups"
rm -f "${STAGE_DIR}/previous-barrier" "${STAGE_DIR}/previous-barrier-missing" \
  "${STAGE_DIR}/previous-runtime-manifest.json" "${STAGE_DIR}/previous-manifest-digest" \
  "${STAGE_DIR}/previous-barrier-path"
for INDEX in 0 1 2 3 4 5 6; do
  LABEL="${LABELS[${INDEX}]}"
  TARGET="${TARGET_PLISTS[${INDEX}]}"
  if [[ -f "${TARGET}" ]]; then
    cp "${TARGET}" "${STAGE_DIR}/backups/${LABEL}.plist"
  else
    : > "${STAGE_DIR}/backups/${LABEL}.missing"
  fi
  if launchctl print "gui/${USER_ID}/${LABEL}" > "${STAGE_DIR}/${LABEL}.previous_identity" 2>/dev/null; then
    printf '1\n' > "${STAGE_DIR}/${LABEL}.previous_loaded"
    normalize_control_identity "${STAGE_DIR}/${LABEL}.previous_identity" \
      > "${STAGE_DIR}/${LABEL}.previous_identity.stable"
  else
    printf '0\n' > "${STAGE_DIR}/${LABEL}.previous_loaded"
  fi
done
PREVIOUS_MANIFEST=""
PREVIOUS_MANIFEST_DIGEST=""
PREVIOUS_BARRIER_PATH=""
if [[ -f "${STAGE_DIR}/backups/com.pantheon.agy-gemini-coordinator.plist" ]]; then
  PREVIOUS_MANIFEST="$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST' \
    "${STAGE_DIR}/backups/com.pantheon.agy-gemini-coordinator.plist" 2>/dev/null || true)"
  PREVIOUS_MANIFEST_DIGEST="$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST_DIGEST' \
    "${STAGE_DIR}/backups/com.pantheon.agy-gemini-coordinator.plist" 2>/dev/null || true)"
  PREVIOUS_BARRIER_PATH="$(/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:5' \
    "${STAGE_DIR}/backups/com.pantheon.agy-gemini-coordinator.plist" 2>/dev/null || true)"
fi
if [[ "${PREVIOUS_BARRIER_PATH}" == /* && -f "${PREVIOUS_BARRIER_PATH}" \
  && -f "${PREVIOUS_MANIFEST}" \
  && "${PREVIOUS_MANIFEST_DIGEST}" =~ ^[0-9a-f]{64}$ ]] \
  && (cd "${REPO_ROOT}" && "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest \
    barrier-validate --barrier "${PREVIOUS_BARRIER_PATH}" \
    --manifest "${PREVIOUS_MANIFEST}" \
    --expected-digest "${PREVIOUS_MANIFEST_DIGEST}") >/dev/null; then
  cp "${PREVIOUS_BARRIER_PATH}" "${STAGE_DIR}/previous-barrier"
  cp "${PREVIOUS_MANIFEST}" "${STAGE_DIR}/previous-runtime-manifest.json"
  printf '%s\n' "${PREVIOUS_MANIFEST_DIGEST}" > "${STAGE_DIR}/previous-manifest-digest"
  printf '%s\n' "${PREVIOUS_BARRIER_PATH}" > "${STAGE_DIR}/previous-barrier-path"
else
  : > "${STAGE_DIR}/previous-barrier-missing"
fi

trap 'rollback_activation $?' ERR
rm -f "${ACTIVATION_BARRIER}"
rm -rf "${READY_ROOT}"
mkdir -p "${READY_ROOT}"
for INDEX in 0 1 2 3 4 5 6; do
  install -m 600 "${STAGED_PLISTS[${INDEX}]}" "${TARGET_PLISTS[${INDEX}]}"
done
for INDEX in 0 1 2 3 4 5 6; do
  LABEL="${LABELS[${INDEX}]}"
  TARGET="${TARGET_PLISTS[${INDEX}]}"
  if [[ "$(cat "${STAGE_DIR}/${LABEL}.previous_loaded")" == "1" ]]; then
    launchctl bootout "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1
    if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      false
    fi
  fi
done
for INDEX in 0 1 2 3 4 5 6; do
  LABEL="${LABELS[${INDEX}]}"
  TARGET="${TARGET_PLISTS[${INDEX}]}"
  STARTED_LABELS+=("${LABEL}")
  launchctl bootstrap "gui/${USER_ID}" "${TARGET}"
  launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null
done
LIVE_AGGREGATE_ARGS=()
for TARGET_PLIST_PATH in "${TARGET_PLISTS[@]}"; do
  LIVE_AGGREGATE_ARGS+=(--plist "${TARGET_PLIST_PATH}")
done
(
  cd "${REPO_ROOT}"
  "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest aggregate \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
    "${LIVE_AGGREGATE_ARGS[@]}"
) >/dev/null
(cd "${REPO_ROOT}" && "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest \
  barrier-activate \
  --manifest "${RUNTIME_MANIFEST_FILE}" \
  --expected-digest "${RUNTIME_MANIFEST_DIGEST}" \
  --ready-root "${READY_ROOT}" \
  --barrier "${ACTIVATION_BARRIER}" \
  --timeout 90) >/dev/null
trap - ERR
rm -rf "${STAGE_DIR}"

echo "Pantheon 七服務 aggregate activation 已完成。"
echo "Queue root：${QUEUE_ROOT}"
echo "狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-coordinator"
echo "停止：launchctl bootout gui/${USER_ID} ${TARGET_PLIST}"
echo "Lane 狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}"
echo "Lane plist：${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}.plist"
