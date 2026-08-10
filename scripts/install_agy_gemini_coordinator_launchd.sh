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
(
  cd "${REPO_ROOT}"
  "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest validate \
    --manifest "${RUNTIME_MANIFEST_FILE}"
) >/dev/null
manifest_field() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_PATH}" -m scripts.pantheon_content_runtime_manifest field \
      --manifest "${RUNTIME_MANIFEST_FILE}" --name "$1"
  )
}
ACTOR_ROOT="$(manifest_field actor_root)"
QUEUE_ROOT="$(manifest_field queue_root)"
CONTENT_PUBLISHER_ROOT="$(manifest_field publisher_state_root)"
LOG_DIR="$(manifest_field log_root)"
RUNTIME_MANIFEST_DIGEST="$(manifest_field manifest_digest)"
RUNTIME_IDENTITY="$(manifest_field identity)"
ACTIVATION_BARRIER="${CONTENT_PUBLISHER_ROOT}/four-lane-activation.barrier"
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
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:9 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:15 ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:17 ${GSC_COPY_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:20 ${CONTENT_PUBLISHER_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:22 ${GSC_COPY_ROOT}" "${TEMP_PLIST}"
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
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY ${RUNTIME_IDENTITY}" "${TEMP_PLIST}"
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
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:9 ${PYTHON_PATH}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${QUEUE_ROOT}/lanes/${LANE}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:15 ${LANE}" "${LANE_TEMP_PLIST}"
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
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY ${RUNTIME_IDENTITY}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/agy-gemini-${LANE}.stdout.log" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/agy-gemini-${LANE}.stderr.log" "${LANE_TEMP_PLIST}"
  plutil -lint "${LANE_TEMP_PLIST}" >/dev/null
done

if [[ "${ACTION}" == "--preflight" ]]; then
  echo "Pantheon Gemini coordinator 與四條 lane runner preflight 通過。"
  exit 0
fi

LABELS=(
  "com.pantheon.agy-gemini-coordinator"
  "com.pantheon.agy-gemini-new"
  "com.pantheon.agy-gemini-rewrite"
  "com.pantheon.agy-gemini-i18n-new"
  "com.pantheon.agy-gemini-i18n-rewrite"
)
TEMP_PLISTS=("${TEMP_PLIST}" "${LANE_TEMP_PLISTS[@]}")
TARGET_PLISTS=("${TARGET_PLIST}" "${LANE_TARGET_PLISTS[@]}")

if [[ "${ACTION}" == "--install" ]]; then
  mkdir -p "${LOG_DIR}" "${LAUNCH_AGENTS_DIR}"
  rm -rf "${STAGE_DIR}"
  mkdir -p "${STAGE_DIR}/backups"
  if [[ -f "${ACTIVATION_BARRIER}" ]]; then
    cp "${ACTIVATION_BARRIER}" "${STAGE_DIR}/previous-barrier"
  else
    : > "${STAGE_DIR}/previous-barrier-missing"
  fi
  for INDEX in 0 1 2 3 4; do
    LABEL="${LABELS[${INDEX}]}"
    TARGET="${TARGET_PLISTS[${INDEX}]}"
    if [[ -f "${TARGET}" ]]; then
      cp "${TARGET}" "${STAGE_DIR}/backups/${LABEL}.plist"
    else
      : > "${STAGE_DIR}/backups/${LABEL}.missing"
    fi
    previous_loaded=0
    if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      previous_loaded=1
    fi
    printf '%s\n' "${previous_loaded}" > "${STAGE_DIR}/${LABEL}.previous_loaded"
    install -m 600 "${TEMP_PLISTS[${INDEX}]}" "${TARGET}"
  done
  printf '%s\n' "${RUNTIME_MANIFEST_DIGEST}" > "${STAGE_DIR}/manifest-digest"
  echo "Pantheon Gemini coordinator 與四條 lane plist 已 stage；尚未 activation。"
  exit 0
fi

if [[ ! -d "${STAGE_DIR}" \
  || "$(cat "${STAGE_DIR}/manifest-digest" 2>/dev/null || true)" != "${RUNTIME_MANIFEST_DIGEST}" ]]; then
  echo "找不到 matching four-lane stage receipt，拒絕 activation。" >&2
  exit 1
fi
for INDEX in 0 1 2 3 4; do
  if ! cmp -s "${TEMP_PLISTS[${INDEX}]}" "${TARGET_PLISTS[${INDEX}]}"; then
    echo "staged plist 與 activation input 不一致。" >&2
    exit 1
  fi
done

STARTED_LABELS=()
rollback_activation() {
  local RETURN_CODE="$1"
  trap - ERR
  set +e
  rm -f "${ACTIVATION_BARRIER}"
  for LABEL in "${STARTED_LABELS[@]}"; do
    launchctl bootout "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1
  done
  for INDEX in 0 1 2 3 4; do
    LABEL="${LABELS[${INDEX}]}"
    TARGET="${TARGET_PLISTS[${INDEX}]}"
    if [[ -f "${STAGE_DIR}/backups/${LABEL}.plist" ]]; then
      install -m 600 "${STAGE_DIR}/backups/${LABEL}.plist" "${TARGET}"
    else
      rm -f "${TARGET}"
    fi
    if [[ "$(cat "${STAGE_DIR}/${LABEL}.previous_loaded")" == "1" \
      && -f "${TARGET}" ]]; then
      launchctl bootstrap "gui/${USER_ID}" "${TARGET}" >/dev/null 2>&1
    fi
  done
  if [[ -f "${STAGE_DIR}/previous-barrier" ]]; then
    install -m 600 "${STAGE_DIR}/previous-barrier" "${ACTIVATION_BARRIER}"
  fi
  printf '{"status":"ROLLBACK_COMPLETE","failed":true,"manifest_digest":"%s"}\n' \
    "${RUNTIME_MANIFEST_DIGEST}" > "${STAGE_DIR}/failure-receipt.json"
  exit "${RETURN_CODE}"
}

# activation barrier：五個 identity 全部 loaded 前，wrapper 不會進入 queue command。
trap 'rollback_activation $?' ERR
rm -f "${ACTIVATION_BARRIER}"
for INDEX in 0 1 2 3 4; do
  LABEL="${LABELS[${INDEX}]}"
  TARGET="${TARGET_PLISTS[${INDEX}]}"
  launchctl bootout "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/${USER_ID}" "${TARGET}"
  STARTED_LABELS+=("${LABEL}")
  launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null
done
BARRIER_TEMP="${ACTIVATION_BARRIER}.tmp.$$"
printf '%s\n' "${RUNTIME_MANIFEST_DIGEST}" > "${BARRIER_TEMP}"
chmod 600 "${BARRIER_TEMP}"
mv "${BARRIER_TEMP}" "${ACTIVATION_BARRIER}"
trap - ERR
rm -rf "${STAGE_DIR}"

echo "Pantheon Gemini coordinator 已啟用。"
echo "四條 lane runner 已啟用：new、rewrite、i18n-new、i18n-rewrite。"
echo "Queue root：${QUEUE_ROOT}"
echo "狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-coordinator"
echo "停止：launchctl bootout gui/${USER_ID} ${TARGET_PLIST}"
echo "Lane 狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}"
echo "Lane plist：${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}.plist"
