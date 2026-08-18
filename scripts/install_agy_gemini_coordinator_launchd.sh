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
REQUESTED_WRITER_MODEL="${AGY_WRITER_MODEL:-}"
REQUESTED_REVIEWER_MODEL="${AGY_REVIEWER_MODEL:-}"
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
MODEL_ROUTE_STORE_DIR="${LAUNCH_AGENTS_DIR}/.pantheon-model-routes"

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
  && "${ACTION}" != "--activate" && "${ACTION}" != "--activate-only" \
  && "${ACTION}" != "--activate-publisher-only" ]]; then
  echo "用法：scripts/install_agy_gemini_coordinator_launchd.sh [--preflight|--install|--activate|--activate-only|--activate-publisher-only]" >&2
  exit 2
fi
if [[ "${PYTHON_PATH}" != /* ]]; then
  echo "Pantheon Python 必須使用 absolute path：${PYTHON_PATH}" >&2
  exit 1
fi
PYTHON_REALPATH="$(/usr/bin/perl -MCwd=realpath -e 'print realpath($ARGV[0]) // ""' "${PYTHON_PATH}")"
if [[ -z "${PYTHON_REALPATH}" || ! -f "${PYTHON_REALPATH}" || ! -x "${PYTHON_REALPATH}" || -L "${PYTHON_REALPATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
  exit 1
fi
PYTHON_BIN="${PYTHON_REALPATH}"
if [[ ! -x "${AGY_CLI_PATH}" ]]; then
  echo "找不到 Gemini CLI：${AGY_CLI_PATH}" >&2
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
  "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest validate \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
    --expected-python-executable "${PYTHON_BIN}"
) >/dev/null
manifest_field() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest field \
      --manifest "${RUNTIME_MANIFEST_FILE}" \
      --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" --name "$1"
  )
}
optional_manifest_field() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest field \
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
RUNTIME_UV_EXECUTABLE="$(manifest_field uv_executable)"
MODEL_ROUTE_CONFIG_PATH="${REPO_ROOT}/config/agy_gemini_model_routes.v1.json"
route_identity() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -c 'import sys; from pathlib import Path; from scripts.agy_seo_copy_pipeline import load_model_route_config; route = load_model_route_config(Path(sys.argv[1])); print("\t".join((route.digest, route.routes["writer"][0], route.routes["reviewer"][0], str(route.path))))' "$1"
  )
}
if ! MODEL_ROUTE_IDENTITY="$(route_identity "${MODEL_ROUTE_CONFIG_PATH}" 2>/dev/null)"; then
  echo "model route source identity 無效。" >&2
  exit 1
fi
IFS=$'\t' read -r MODEL_ROUTE_CONFIG_DIGEST WRITER_MODEL REVIEWER_MODEL MODEL_ROUTE_CANONICAL_PATH <<< "${MODEL_ROUTE_IDENTITY}"
if [[ "${MODEL_ROUTE_CANONICAL_PATH}" != "${MODEL_ROUTE_CONFIG_PATH}" ]]; then
  echo "model route source identity 無效。" >&2
  exit 1
fi
STAGED_MODEL_ROUTE_CONFIG="${MODEL_ROUTE_STORE_DIR}/model-route-config-${MODEL_ROUTE_CONFIG_DIGEST}.json"
if [[ ( -n "${REQUESTED_WRITER_MODEL}" && "${REQUESTED_WRITER_MODEL}" != "${WRITER_MODEL}" ) \
  || ( -n "${REQUESTED_REVIEWER_MODEL}" && "${REQUESTED_REVIEWER_MODEL}" != "${REVIEWER_MODEL}" ) ]]; then
  echo "正式 Writer／Reviewer model route 不符合鎖定契約。" >&2
  exit 1
fi
add_hardened_runtime_identity() {
  local PLIST_PATH="$1"
  if [[ -n "${RUNTIME_ACTOR_HEAD}" ]]; then
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_ACTOR_HEAD string ${RUNTIME_ACTOR_HEAD}" "${PLIST_PATH}"
  fi
  if [[ -n "${RUNTIME_PYTHON_EXECUTABLE}" ]]; then
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_PYTHON_EXECUTABLE string ${RUNTIME_PYTHON_EXECUTABLE}" "${PLIST_PATH}"
  fi
  if [[ -n "${RUNTIME_UV_EXECUTABLE}" ]]; then
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_UV_EXECUTABLE string ${RUNTIME_UV_EXECUTABLE}" "${PLIST_PATH}"
  fi
}
ACTIVATION_BARRIER="${CONTENT_PUBLISHER_ROOT}/four-lane-activation-${RUNTIME_GENERATION}.barrier"
READY_ROOT="${STAGE_DIR}/readiness/${RUNTIME_GENERATION}"
PRODUCTION_STATE_FILE="${AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE:-${QUEUE_ROOT}/production-credential-pool-state.json}"
BARRIER_TIMEOUT_SECONDS="${PANTHEON_ACTIVATION_BARRIER_TIMEOUT_SECONDS:-90}"
if [[ "${ACTOR_ROOT}" != "${REPO_ROOT}" ]]; then
  echo "runtime manifest actor root 與 coordinator installer 不一致。" >&2
  exit 1
fi
if [[ ! "${BARRIER_TIMEOUT_SECONDS}" =~ ^[1-9][0-9]{0,2}$ ]] \
  || (( 10#${BARRIER_TIMEOUT_SECONDS} > 300 )); then
  echo "Pantheon activation barrier timeout 必須介於 1 與 300。" >&2
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
    "${PYTHON_BIN}" -m scripts.agy_gemini_runner \
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
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_BIN}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:5 ${ACTIVATION_BARRIER}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:7 ${RUNTIME_MANIFEST_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:9 ${RUNTIME_MANIFEST_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${READY_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:17 ${PYTHON_BIN}" "${TEMP_PLIST}"
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
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_WRITER_MODEL string ${WRITER_MODEL}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_REVIEWER_MODEL string ${REVIEWER_MODEL}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_MODEL_ROUTE_CONFIG string ${STAGED_MODEL_ROUTE_CONFIG}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST string ${MODEL_ROUTE_CONFIG_DIGEST}" "${TEMP_PLIST}"
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
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_BIN}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:5 ${ACTIVATION_BARRIER}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:7 ${RUNTIME_MANIFEST_DIGEST}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:9 ${RUNTIME_MANIFEST_FILE}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:11 ${LANE_LABEL}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${READY_ROOT}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:17 ${PYTHON_BIN}" "${LANE_TEMP_PLIST}"
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
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_WRITER_MODEL string ${WRITER_MODEL}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_REVIEWER_MODEL string ${REVIEWER_MODEL}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_MODEL_ROUTE_CONFIG string ${STAGED_MODEL_ROUTE_CONFIG}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST string ${MODEL_ROUTE_CONFIG_DIGEST}" "${LANE_TEMP_PLIST}"
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
  mkdir -p "${MODEL_ROUTE_STORE_DIR}"
  chmod 700 "${MODEL_ROUTE_STORE_DIR}"
  rm -f "${STAGE_DIR}/failure-receipt.json"
  install -m 600 "${MODEL_ROUTE_CONFIG_PATH}" "${STAGED_MODEL_ROUTE_CONFIG}"
  for INDEX in 0 1 2 3 4; do
    install -m 600 "${TEMP_PLISTS[${INDEX}]}" "${STAGED_PLISTS[${INDEX}]}"
  done
  printf '%s\n' "${RUNTIME_MANIFEST_DIGEST}" > "${STAGE_DIR}/manifest-digest"
  printf '%s\n' "${RUNTIME_GENERATION}" > "${STAGE_DIR}/generation"
  printf '%s\n' "${MODEL_ROUTE_CONFIG_DIGEST}" > "${STAGE_DIR}/model-route-digest"
  printf '%s\n' "${STAGED_MODEL_ROUTE_CONFIG}" > "${STAGE_DIR}/model-route-path"
  echo "Pantheon Gemini coordinator 與四條 lane plist 已寫入 private stage；尚未 activation。"
  exit 0
fi

ACTIVATION_ONLY=0
if [[ "${ACTION}" == "--activate-only" ]]; then
  ACTIVATION_ONLY=1
fi
PUBLISHER_ONLY_ACTIVATION=0
if [[ "${ACTION}" == "--activate-publisher-only" ]]; then
  PUBLISHER_ONLY_ACTIVATION=1
fi
ACTIVATION_CORRELATION_ID="activation-${RUNTIME_GENERATION}-$$"
ACTIVATION_PHASE="correlation_validation"
write_failure_receipt() {
  local STATUS="$1"
  local RETURN_CODE="$2"
  local EXIT_PHASE="$3"
  local ROLLBACK_CHECK_IDS_JSON="${4:-[]}"
  local RECEIPT_TEMP="${STAGE_DIR}/failure-receipt.json.tmp.$$"
  printf '{"schema_version":1,"status":"%s","failed":true,"correlation_id":"%s","stage_identity":{"manifest_digest":"%s","generation":"%s"},"exit_reason":{"phase":"%s","exit_code":%d},"rollback_check_ids":%s}\n' \
    "${STATUS}" "${ACTIVATION_CORRELATION_ID}" "${RUNTIME_MANIFEST_DIGEST}" \
    "${RUNTIME_GENERATION}" "${EXIT_PHASE}" "${RETURN_CODE}" \
    "${ROLLBACK_CHECK_IDS_JSON}" > "${RECEIPT_TEMP}"
  chmod 600 "${RECEIPT_TEMP}"
  mv "${RECEIPT_TEMP}" "${STAGE_DIR}/failure-receipt.json"
}
reject_activation() {
  local RETURN_CODE="$1"
  local EXIT_PHASE="$2"
  trap - ERR
  set +e
  write_failure_receipt "ACTIVATION_REJECTED" "${RETURN_CODE}" "${EXIT_PHASE}"
  exit "${RETURN_CODE}"
}
trap 'reject_activation $? "${ACTIVATION_PHASE}"' ERR
if [[ -n "${PANTHEON_ACTIVATION_CORRELATION_ID:-}" ]]; then
  if [[ ! "${PANTHEON_ACTIVATION_CORRELATION_ID}" =~ ^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$ ]]; then
    echo "activation correlation id 格式無效。" >&2
    false
  fi
  ACTIVATION_CORRELATION_ID="${PANTHEON_ACTIVATION_CORRELATION_ID}"
fi
if [[ "${PUBLISHER_ONLY_ACTIVATION}" == "1" ]]; then
  PUBLISHER_LABEL="com.pantheon.agy-content-publisher"
  PUBLISHER_STAGE_PLIST="${STAGE_DIR}/${PUBLISHER_LABEL}.plist"
  PUBLISHER_TARGET_PLIST="${LAUNCH_AGENTS_DIR}/${PUBLISHER_LABEL}.plist"
  OTHER_LIVE_PLISTS=(
    "${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-coordinator.plist"
    "${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-new.plist"
    "${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-rewrite.plist"
    "${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-i18n-new.plist"
    "${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-i18n-rewrite.plist"
    "${LAUNCH_AGENTS_DIR}/com.pantheon.content-capacity-guard.plist"
  )
  ACTIVATION_PHASE="publisher_only_stage_validation"
  if [[ ! -d "${STAGE_DIR}" \
    || "$(cat "${STAGE_DIR}/manifest-digest" 2>/dev/null || true)" != "${RUNTIME_MANIFEST_DIGEST}" \
    || "$(cat "${STAGE_DIR}/generation" 2>/dev/null || true)" != "${RUNTIME_GENERATION}" \
    || "$(cat "${STAGE_DIR}/publisher-max-runs" 2>/dev/null || true)" != "1" \
    || ! -f "${PUBLISHER_STAGE_PLIST}" ]]; then
    echo "Publisher-only activation requires matching stage receipt with max-runs=1." >&2
    false
  fi
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest publisher-plist \
      --manifest "${RUNTIME_MANIFEST_FILE}" \
      --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
      --plist "${PUBLISHER_STAGE_PLIST}"
  )
  ACTIVATION_PHASE="publisher_only_live_activation_only_validation"
  LIVE_ACTIVATION_ONLY_ARGS=()
  for TARGET_PLIST_PATH in "${TARGET_PLISTS[@]}"; do
    LIVE_ACTIVATION_ONLY_ARGS+=(--plist "${TARGET_PLIST_PATH}")
  done
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest aggregate \
      --manifest "${RUNTIME_MANIFEST_FILE}" \
      --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
      --activation-mode activation-only \
      "${LIVE_ACTIVATION_ONLY_ARGS[@]}"
  ) >/dev/null
  ACTIVATION_PHASE="publisher_only_barrier_validation"
  if ! (cd "${REPO_ROOT}" && "${PYTHON_BIN}" -m \
    scripts.pantheon_content_runtime_manifest barrier-validate \
    --barrier "${ACTIVATION_BARRIER}" \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${RUNTIME_MANIFEST_DIGEST}") >/dev/null; then
    echo "Publisher-only normal activation 缺少 matching activation barrier，拒絕 activation。" >&2
    false
  fi
  ACTIVATION_PHASE="publisher_only_snapshot_previous_state"
  rm -rf "${STAGE_DIR}/publisher-only-backups"
  mkdir -p "${STAGE_DIR}/publisher-only-backups"
  cp "${PUBLISHER_TARGET_PLIST}" "${STAGE_DIR}/publisher-only-backups/${PUBLISHER_LABEL}.plist"
  for OTHER_PLIST in "${OTHER_LIVE_PLISTS[@]}"; do
    cp "${OTHER_PLIST}" "${STAGE_DIR}/publisher-only-backups/$(basename "${OTHER_PLIST}")"
  done
  if launchctl print "gui/${USER_ID}/${PUBLISHER_LABEL}" \
    > "${STAGE_DIR}/publisher-only-backups/${PUBLISHER_LABEL}.previous_identity" 2>/dev/null; then
    printf '1\n' > "${STAGE_DIR}/publisher-only-backups/${PUBLISHER_LABEL}.previous_loaded"
  else
    printf '0\n' > "${STAGE_DIR}/publisher-only-backups/${PUBLISHER_LABEL}.previous_loaded"
  fi
  rollback_publisher_only_activation() {
    local RETURN_CODE="$1"
    local EXIT_PHASE="$2"
    local ROLLBACK_STATUS="ROLLBACK_COMPLETE"
    trap - ERR
    set +e
    install -m 600 "${STAGE_DIR}/publisher-only-backups/${PUBLISHER_LABEL}.plist" \
      "${PUBLISHER_TARGET_PLIST}" || ROLLBACK_STATUS="ROLLBACK_FAILED"
    launchctl bootout "gui/${USER_ID}/${PUBLISHER_LABEL}" >/dev/null 2>&1 || true
    if [[ "$(cat "${STAGE_DIR}/publisher-only-backups/${PUBLISHER_LABEL}.previous_loaded" 2>/dev/null || true)" == "1" ]]; then
      launchctl bootstrap "gui/${USER_ID}" "${PUBLISHER_TARGET_PLIST}" >/dev/null 2>&1 \
        || ROLLBACK_STATUS="ROLLBACK_FAILED"
    fi
    for OTHER_PLIST in "${OTHER_LIVE_PLISTS[@]}"; do
      cmp -s "${STAGE_DIR}/publisher-only-backups/$(basename "${OTHER_PLIST}")" \
        "${OTHER_PLIST}" || ROLLBACK_STATUS="ROLLBACK_FAILED"
    done
    write_failure_receipt "${ROLLBACK_STATUS}" "${RETURN_CODE}" "${EXIT_PHASE}"
    exit "${RETURN_CODE}"
  }
  ACTIVATION_PHASE="publisher_only_pre_replace_drift_check"
  for OTHER_PLIST in "${OTHER_LIVE_PLISTS[@]}"; do
    cmp -s "${STAGE_DIR}/publisher-only-backups/$(basename "${OTHER_PLIST}")" \
      "${OTHER_PLIST}"
  done
  ACTIVATION_PHASE="publisher_only_replace_live_plist"
  trap 'rollback_publisher_only_activation $? "${ACTIVATION_PHASE}"' ERR
  install -m 600 "${PUBLISHER_STAGE_PLIST}" "${PUBLISHER_TARGET_PLIST}"
  ACTIVATION_PHASE="publisher_only_restart_publisher"
  launchctl bootout "gui/${USER_ID}/${PUBLISHER_LABEL}" >/dev/null 2>&1 || true
  if launchctl print "gui/${USER_ID}/${PUBLISHER_LABEL}" >/dev/null 2>&1; then
    false
  fi
  launchctl bootstrap "gui/${USER_ID}" "${PUBLISHER_TARGET_PLIST}"
  launchctl print "gui/${USER_ID}/${PUBLISHER_LABEL}" >/dev/null
  ACTIVATION_PHASE="publisher_only_postcheck"
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest publisher-plist \
      --manifest "${RUNTIME_MANIFEST_FILE}" \
      --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
      --plist "${PUBLISHER_TARGET_PLIST}"
  ) >/dev/null
  for OTHER_PLIST in "${OTHER_LIVE_PLISTS[@]}"; do
    cmp -s "${STAGE_DIR}/publisher-only-backups/$(basename "${OTHER_PLIST}")" \
      "${OTHER_PLIST}"
  done
  trap - ERR
  rm -rf "${STAGE_DIR}"
  echo "Pantheon Publisher-only bounded activation 已完成。"
  echo "Queue root：${QUEUE_ROOT}"
  echo "狀態：launchctl print gui/${USER_ID}/${PUBLISHER_LABEL}"
  exit 0
fi
if ! STAGED_MODEL_ROUTE_IDENTITY="$(route_identity "${STAGED_MODEL_ROUTE_CONFIG}" 2>/dev/null)"; then
  echo "model route stage identity 無效，拒絕 activation。" >&2
  false
fi
IFS=$'\t' read -r STAGED_MODEL_ROUTE_DIGEST _STAGED_WRITER_MODEL _STAGED_REVIEWER_MODEL STAGED_MODEL_ROUTE_CANONICAL_PATH <<< "${STAGED_MODEL_ROUTE_IDENTITY}"
if [[ "$(cat "${STAGE_DIR}/model-route-digest" 2>/dev/null || true)" != "${MODEL_ROUTE_CONFIG_DIGEST}" \
  || "$(cat "${STAGE_DIR}/model-route-path" 2>/dev/null || true)" != "${STAGED_MODEL_ROUTE_CONFIG}" \
  || "${STAGED_MODEL_ROUTE_DIGEST}" != "${MODEL_ROUTE_CONFIG_DIGEST}" \
  || "${STAGED_MODEL_ROUTE_CANONICAL_PATH}" != "${STAGED_MODEL_ROUTE_CONFIG}" ]]; then
  echo "model route stage identity 無效，拒絕 activation。" >&2
  false
fi
if [[ ! -d "${STAGE_DIR}" \
  || "$(cat "${STAGE_DIR}/manifest-digest" 2>/dev/null || true)" != "${RUNTIME_MANIFEST_DIGEST}" \
  || "$(cat "${STAGE_DIR}/generation" 2>/dev/null || true)" != "${RUNTIME_GENERATION}" ]]; then
  echo "找不到 matching aggregate stage receipt，拒絕 activation。" >&2
  false
fi
for STAGED_GEMINI_PLIST in "${STAGED_PLISTS[@]:0:5}"; do
  if [[ "$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:AGY_GEMINI_MODEL_ROUTE_CONFIG' "${STAGED_GEMINI_PLIST}" 2>/dev/null || true)" != "${STAGED_MODEL_ROUTE_CONFIG}" \
    || "$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST' "${STAGED_GEMINI_PLIST}" 2>/dev/null || true)" != "${MODEL_ROUTE_CONFIG_DIGEST}" ]]; then
    echo "model route stage identity 無效，拒絕 activation。" >&2
    false
  fi
done
ACTIVATION_PHASE="aggregate_preflight"
AGGREGATE_ARGS=()
for STAGED_PLIST in "${STAGED_PLISTS[@]}"; do
  AGGREGATE_ARGS+=(--plist "${STAGED_PLIST}")
done
(
  cd "${REPO_ROOT}"
  "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest aggregate \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
    --activation-mode normal \
    "${AGGREGATE_ARGS[@]}"
)

STARTED_LABELS=()
normalize_control_identity() {
  sed -E '/^[[:space:]]*(state|pid|runs|last exit code|last terminating signal|successful exits|forks|execs|initialized|trampolined|started|proxy started) = /d' "$1"
}
rollback_activation() {
  local RETURN_CODE="$1"
  local EXIT_PHASE="$2"
  local ROLLBACK_FAILED=0
  local ROLLBACK_CHECK_IDS=()
  record_rollback_failure() {
    ROLLBACK_FAILED=1
    ROLLBACK_CHECK_IDS+=("$1")
  }
  rollback_check_ids_json() {
    local ID
    local SEPARATOR=""
    if [[ "${#ROLLBACK_CHECK_IDS[@]}" == "0" ]]; then
      printf '%s' '[]'
      return 0
    fi
    printf '['
    for ID in "${ROLLBACK_CHECK_IDS[@]}"; do
      printf '%s"%s"' "${SEPARATOR}" "${ID}"
      SEPARATOR=","
    done
    printf ']'
  }
  trap - ERR
  set +e
  rm -f "${ACTIVATION_BARRIER}" || record_rollback_failure "rollback.barrier.remove"
  for LABEL in "${STARTED_LABELS[@]}"; do
    if ! launchctl bootout "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      record_rollback_failure "rollback.bootout"
    fi
    if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      record_rollback_failure "rollback.bootout.loaded"
    fi
  done
  for INDEX in 0 1 2 3 4 5 6; do
    LABEL="${LABELS[${INDEX}]}"
    TARGET="${TARGET_PLISTS[${INDEX}]}"
    if [[ -f "${STAGE_DIR}/backups/${LABEL}.plist" ]]; then
      install -m 600 "${STAGE_DIR}/backups/${LABEL}.plist" "${TARGET}" \
        || record_rollback_failure "rollback.restore"
      cmp -s "${STAGE_DIR}/backups/${LABEL}.plist" "${TARGET}" \
        || record_rollback_failure "rollback.restore.hash"
    else
      rm -f "${TARGET}" || record_rollback_failure "rollback.restore.remove"
      [[ ! -e "${TARGET}" ]] || record_rollback_failure "rollback.restore.remove"
    fi
    if [[ "$(cat "${STAGE_DIR}/${LABEL}.previous_loaded")" == "1" \
      && -f "${TARGET}" ]]; then
      if ! launchctl bootstrap "gui/${USER_ID}" "${TARGET}" >/dev/null 2>&1 \
        || ! launchctl print "gui/${USER_ID}/${LABEL}" \
          > "${STAGE_DIR}/${LABEL}.actual_identity" 2>/dev/null; then
        record_rollback_failure "rollback.bootstrap"
      else
        normalize_control_identity "${STAGE_DIR}/${LABEL}.actual_identity" \
          > "${STAGE_DIR}/${LABEL}.actual_identity.stable"
        cmp -s "${STAGE_DIR}/${LABEL}.previous_identity.stable" \
          "${STAGE_DIR}/${LABEL}.actual_identity.stable" \
          || record_rollback_failure "rollback.identity"
      fi
    elif launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      record_rollback_failure "rollback.identity.unloaded"
    fi
  done
  if [[ -f "${STAGE_DIR}/previous-barrier" ]]; then
    PREVIOUS_BARRIER_PATH="$(cat "${STAGE_DIR}/previous-barrier-path")"
    install -m 600 "${STAGE_DIR}/previous-barrier" "${PREVIOUS_BARRIER_PATH}" \
      || record_rollback_failure "rollback.barrier.restore"
    if ! (cd "${REPO_ROOT}" && "${PYTHON_BIN}" -m \
      scripts.pantheon_content_runtime_manifest barrier-validate \
      --barrier "${PREVIOUS_BARRIER_PATH}" \
      --manifest "${STAGE_DIR}/previous-runtime-manifest.json" \
      --expected-digest "$(cat "${STAGE_DIR}/previous-manifest-digest")") \
      >/dev/null; then
      record_rollback_failure "rollback.barrier.validate"
    fi
  elif grep -q '^1$' "${STAGE_DIR}"/*.previous_loaded \
    && [[ ! -f "${STAGE_DIR}/legacy-capacity-adoption" ]]; then
    record_rollback_failure "rollback.barrier.missing"
  fi
  if [[ "${ROLLBACK_FAILED}" == "1" ]]; then
    ROLLBACK_STATUS="ROLLBACK_FAILED"
  else
    ROLLBACK_STATUS="ROLLBACK_COMPLETE"
  fi
  write_failure_receipt "${ROLLBACK_STATUS}" "${RETURN_CODE}" "${EXIT_PHASE}" \
    "$(rollback_check_ids_json)"
  exit "${RETURN_CODE}"
}
canonical_existing_path() {
  local INPUT_PATH="$1"
  local INPUT_DIR
  local INPUT_BASE
  local PHYSICAL_DIR
  INPUT_DIR="$(dirname "${INPUT_PATH}")"
  INPUT_BASE="$(basename "${INPUT_PATH}")"
  PHYSICAL_DIR="$(cd "${INPUT_DIR}" 2>/dev/null && pwd -P)" || return 1
  printf '%s/%s\n' "${PHYSICAL_DIR}" "${INPUT_BASE}"
}
prepare_legacy_capacity_adoption() {
  local CAPACITY_LABEL="com.pantheon.content-capacity-guard"
  local CAPACITY_INDEX=6
  local CAPACITY_TARGET="${TARGET_PLISTS[${CAPACITY_INDEX}]}"
  local CAPACITY_BACKUP="${STAGE_DIR}/backups/${CAPACITY_LABEL}.plist"
  local CAPACITY_IDENTITY="${STAGE_DIR}/${CAPACITY_LABEL}.previous_identity"
  local ADOPTION_MODE="capacity-only"
  local BUSINESS_BACKUP_COUNT=0
  local CANONICAL_LOADED_PATH
  local CANONICAL_TARGET_PATH
  local INDEX
  local LABEL
  local LOADED_PATH
  local PATH_FIELD_COUNT
  local STRICT_PATH_FIELD_COUNT
  local TARGET
  local TARGET_CANONICAL

  [[ "${ACTIVATION_ONLY}" == "1" ]] || return 1
  [[ -f "${STAGE_DIR}/previous-barrier-missing" ]] || return 1
  [[ "$(cat "${STAGE_DIR}/${CAPACITY_LABEL}.previous_loaded")" == "1" ]] \
    || return 1
  for INDEX in 0 1 2 3 4 5; do
    LABEL="${LABELS[${INDEX}]}"
    [[ "$(cat "${STAGE_DIR}/${LABEL}.previous_loaded")" == "0" ]] || return 1
    if [[ -f "${STAGE_DIR}/backups/${LABEL}.plist" ]]; then
      BUSINESS_BACKUP_COUNT=$((BUSINESS_BACKUP_COUNT + 1))
    fi
  done
  if [[ "${BUSINESS_BACKUP_COUNT}" == "0" ]]; then
    ADOPTION_MODE="capacity-only"
  elif [[ "${BUSINESS_BACKUP_COUNT}" == "6" ]]; then
    ADOPTION_MODE="inert-six"
  else
    return 1
  fi
  if [[ "${ADOPTION_MODE}" == "inert-six" ]]; then
    for INDEX in 0 1 2 3 4 5; do
      LABEL="${LABELS[${INDEX}]}"
      TARGET="${TARGET_PLISTS[${INDEX}]}"
      [[ -f "${STAGE_DIR}/backups/${LABEL}.plist" && -f "${TARGET}" ]] \
        || return 1
      [[ ! -L "${STAGE_DIR}/backups/${LABEL}.plist" && ! -L "${TARGET}" ]] \
        || return 1
      [[ "$(stat -f '%u' "${TARGET}")" == "${USER_ID}" ]] || return 1
      [[ "$(stat -f '%Lp' "${TARGET}")" == "600" ]] || return 1
      TARGET_CANONICAL="$(canonical_existing_path "${TARGET}")" || return 1
      [[ "${TARGET}" == "${TARGET_CANONICAL}" ]] || return 1
      cmp -s "${STAGE_DIR}/backups/${LABEL}.plist" "${TARGET}" || return 1
      shasum -a 256 "${TARGET}" \
        > "${STAGE_DIR}/${LABEL}.inert-plist.sha256" || return 1
    done
  fi
  [[ -f "${CAPACITY_BACKUP}" && -f "${CAPACITY_TARGET}" ]] || return 1
  [[ ! -L "${CAPACITY_TARGET}" && ! -L "${CAPACITY_BACKUP}" ]] || return 1
  [[ "$(stat -f '%u' "${CAPACITY_TARGET}")" == "${USER_ID}" ]] || return 1
  [[ "$(stat -f '%u' "${CAPACITY_BACKUP}")" == "${USER_ID}" ]] || return 1
  [[ "$(stat -f '%Lp' "${CAPACITY_TARGET}")" == "600" ]] || return 1
  cmp -s "${CAPACITY_BACKUP}" "${CAPACITY_TARGET}" || return 1
  PATH_FIELD_COUNT="$(grep -Ec '^[[:space:]]*path[[:space:]]*=' \
    "${CAPACITY_IDENTITY}" || true)"
  [[ "${PATH_FIELD_COUNT}" == "1" ]] || return 1
  STRICT_PATH_FIELD_COUNT="$(grep -Ec '^[[:space:]]*path = /[^[:space:]]+$' \
    "${CAPACITY_IDENTITY}" || true)"
  [[ "${STRICT_PATH_FIELD_COUNT}" == "1" ]] || return 1
  LOADED_PATH="$(sed -n 's/^[[:space:]]*path = \(\/[^[:space:]]*\)$/\1/p' \
    "${CAPACITY_IDENTITY}")"
  [[ "${LOADED_PATH}" == /* && -e "${LOADED_PATH}" && ! -L "${LOADED_PATH}" ]] \
    || return 1
  CANONICAL_LOADED_PATH="$(canonical_existing_path "${LOADED_PATH}")" || return 1
  CANONICAL_TARGET_PATH="$(canonical_existing_path "${CAPACITY_TARGET}")" || return 1
  [[ "${LOADED_PATH}" == "${CANONICAL_LOADED_PATH}" ]] || return 1
  [[ "${CAPACITY_TARGET}" == "${CANONICAL_TARGET_PATH}" ]] || return 1
  [[ "${CANONICAL_LOADED_PATH}" == "${CANONICAL_TARGET_PATH}" ]] || return 1
  [[ "${LOADED_PATH}" == "${CAPACITY_TARGET}" ]] || return 1
  if grep -Eq '^[[:space:]]*state = running$' \
    "${CAPACITY_IDENTITY}"; then
    return 1
  fi
  shasum -a 256 "${CAPACITY_TARGET}" \
    > "${STAGE_DIR}/legacy-capacity-plist.sha256" || return 1
  cp "${CAPACITY_IDENTITY}" "${STAGE_DIR}/legacy-capacity-loaded-identity"
  printf '%s\n' "${CAPACITY_TARGET}" > "${STAGE_DIR}/legacy-capacity-target-path"
  printf '%s\n' "${ADOPTION_MODE}" > "${STAGE_DIR}/legacy-capacity-adoption-mode"
  if [[ "${ADOPTION_MODE}" == "inert-six" ]]; then
    : > "${STAGE_DIR}/legacy-capacity-inert-six-adoption"
  fi
  : > "${STAGE_DIR}/legacy-capacity-adoption"
  return 0
}
verify_legacy_capacity_adoption_pre_replace() {
  local INDEX
  local LABEL
  local TARGET
  [[ -f "${STAGE_DIR}/legacy-capacity-inert-six-adoption" ]] || return 0
  for INDEX in 0 1 2 3 4 5; do
    LABEL="${LABELS[${INDEX}]}"
    TARGET="${TARGET_PLISTS[${INDEX}]}"
    if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      return 1
    fi
    [[ -f "${TARGET}" && ! -L "${TARGET}" ]] || return 1
    cmp -s "${STAGE_DIR}/backups/${LABEL}.plist" "${TARGET}" || return 1
    shasum -a 256 "${TARGET}" \
      | cmp -s "${STAGE_DIR}/${LABEL}.inert-plist.sha256" - || return 1
  done
  return 0
}

# aggregate activation 前才 snapshot live config/state；stage 不碰 live target 或 barrier。
ACTIVATION_PHASE="snapshot_previous_state"
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
  && (cd "${REPO_ROOT}" && "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest \
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
ACTIVATION_PHASE="previous_barrier_validation"
if [[ -f "${STAGE_DIR}/previous-barrier-missing" ]] \
  && grep -q '^1$' "${STAGE_DIR}"/*.previous_loaded; then
  if ! prepare_legacy_capacity_adoption; then
    echo "legacy prior-loaded service 缺少 valid activation barrier，拒絕 activation。" >&2
    false
  fi
fi
ACTIVATION_PHASE="normal_transition_barrier_validation"
if [[ "${ACTIVATION_ONLY}" != "1" ]]; then
  if ! (cd "${REPO_ROOT}" && "${PYTHON_BIN}" -m \
    scripts.pantheon_content_runtime_manifest barrier-validate \
    --barrier "${ACTIVATION_BARRIER}" \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${RUNTIME_MANIFEST_DIGEST}") >/dev/null; then
    echo "normal activation 缺少 matching activation barrier，拒絕 activation。" >&2
    false
  fi
fi
ACTIVATION_PHASE="legacy_capacity_adoption_pre_replace"
if ! verify_legacy_capacity_adoption_pre_replace; then
  echo "legacy inert plist set 在 replace 前 drift，拒絕 activation。" >&2
  false
fi

ACTIVATION_PHASE="replace_live_plists"
trap 'rollback_activation $? "${ACTIVATION_PHASE}"' ERR
if [[ "${ACTIVATION_ONLY}" == "1" ]]; then
  rm -f "${ACTIVATION_BARRIER}"
fi
rm -rf "${READY_ROOT}"
mkdir -p "${READY_ROOT}"
for INDEX in 0 1 2 3 4 5 6; do
  install -m 600 "${STAGED_PLISTS[${INDEX}]}" "${TARGET_PLISTS[${INDEX}]}"
  if [[ "${ACTIVATION_ONLY}" == "1" ]]; then
    /usr/libexec/PlistBuddy -c "Add :ProgramArguments:16 string --activation-only" \
      "${TARGET_PLISTS[${INDEX}]}"
  fi
done
ACTIVATION_PHASE="bootout_previous_services"
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
ACTIVATION_PHASE="bootstrap_staged_services"
for INDEX in 0 1 2 3 4 5 6; do
  LABEL="${LABELS[${INDEX}]}"
  TARGET="${TARGET_PLISTS[${INDEX}]}"
  STARTED_LABELS+=("${LABEL}")
  launchctl bootstrap "gui/${USER_ID}" "${TARGET}"
  launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null
done
ACTIVATION_PHASE="live_aggregate_validation"
LIVE_AGGREGATE_ARGS=()
for TARGET_PLIST_PATH in "${TARGET_PLISTS[@]}"; do
  LIVE_AGGREGATE_ARGS+=(--plist "${TARGET_PLIST_PATH}")
done
LIVE_ACTIVATION_MODE="normal"
if [[ "${ACTIVATION_ONLY}" == "1" ]]; then
  LIVE_ACTIVATION_MODE="activation-only"
fi
(
  cd "${REPO_ROOT}"
  "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest aggregate \
    --manifest "${RUNTIME_MANIFEST_FILE}" \
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" \
    --activation-mode "${LIVE_ACTIVATION_MODE}" \
    "${LIVE_AGGREGATE_ARGS[@]}"
) >/dev/null
ACTIVATION_PHASE="barrier_activation"
(cd "${REPO_ROOT}" && "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest \
  barrier-activate \
  --manifest "${RUNTIME_MANIFEST_FILE}" \
  --expected-digest "${RUNTIME_MANIFEST_DIGEST}" \
  --ready-root "${READY_ROOT}" \
  --barrier "${ACTIVATION_BARRIER}" \
  --timeout "${BARRIER_TIMEOUT_SECONDS}") >/dev/null
if [[ "${ACTIVATION_ONLY}" == "1" ]]; then
  ACTIVATION_PHASE="activation_only_postcheck"
  for LABEL in "${LABELS[@]}"; do
    launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null
  done
fi
trap - ERR
rm -rf "${STAGE_DIR}"

if [[ "${ACTIVATION_ONLY}" == "1" ]]; then
  echo "Pantheon 七服務 activation-only 已完成。"
else
  echo "Pantheon 七服務 aggregate activation 已完成。"
fi
echo "Queue root：${QUEUE_ROOT}"
echo "狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-coordinator"
echo "停止：launchctl bootout gui/${USER_ID} ${TARGET_PLIST}"
echo "Lane 狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}"
echo "Lane plist：${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}.plist"
