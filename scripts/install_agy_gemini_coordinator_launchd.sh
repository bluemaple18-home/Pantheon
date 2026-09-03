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
REQUESTED_GSC_COPY_ROOT="${PANTHEON_GSC_COPY_ROOT:-}"
LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin}"
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-coordinator.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example"
LANE_TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-gemini-lane.plist.example"
TEMP_PLIST=""
PUBLISHER_RESET_TEMP=""
RECOVERY_ADMISSION_TMP="" RECOVERY_CAPACITY_SNAPSHOT_HOME=""
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
  if [[ -n "${PUBLISHER_RESET_TEMP}" ]]; then
    rm -f "${PUBLISHER_RESET_TEMP}"
  fi
  if [[ -n "${RECOVERY_ADMISSION_TMP}" ]]; then
    rm -rf "${RECOVERY_ADMISSION_TMP}"
  fi
  [[ -z "${RECOVERY_CAPACITY_SNAPSHOT_HOME}" ]] || rm -rf "${RECOVERY_CAPACITY_SNAPSHOT_HOME}"
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
  && "${ACTION}" != "--activate-publisher-only" \
  && "${ACTION}" != "--reset-publisher-activation-only" \
  && "${ACTION}" != "--recover-malformed-activation-only-cohort" ]]; then
  echo "用法：scripts/install_agy_gemini_coordinator_launchd.sh [--preflight|--install|--activate|--activate-only|--activate-publisher-only|--reset-publisher-activation-only|--recover-malformed-activation-only-cohort]" >&2
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
if [[ -n "${PANTHEON_RELEASE_NEXT_EDGE:-}" ]]; then
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_g8_production_preactivation \
      --validate-effector-edge \
      --edge-id "${PANTHEON_RELEASE_NEXT_EDGE}" \
      --action="${ACTION}"
  ) || exit 1
fi
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
GSC_COPY_ROOT="${QUEUE_ROOT}/gsc-copy"
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
make_publisher_only_one_shot_plist() {
  local PLIST_PATH="$1"
  /usr/libexec/PlistBuddy -c "Delete :StartInterval" "${PLIST_PATH}" >/dev/null 2>&1 || true
  /usr/libexec/PlistBuddy -c "Delete :KeepAlive" "${PLIST_PATH}" >/dev/null 2>&1 || true
  if ! /usr/libexec/PlistBuddy -c "Set :RunAtLoad true" "${PLIST_PATH}" >/dev/null 2>&1; then
    /usr/libexec/PlistBuddy -c "Add :RunAtLoad bool true" "${PLIST_PATH}" >/dev/null
  fi
  plutil -lint "${PLIST_PATH}" >/dev/null
}
make_publisher_activation_only_plist() {
  local PLIST_PATH="$1"
  make_publisher_only_one_shot_plist "${PLIST_PATH}"
  /usr/libexec/PlistBuddy -c "Add :ProgramArguments:16 string --activation-only" \
    "${PLIST_PATH}" >/dev/null
  /usr/libexec/PlistBuddy -c "Delete :StandardInPath" "${PLIST_PATH}" >/dev/null 2>&1 || true
  /usr/libexec/PlistBuddy -c "Delete :StandardOutPath" "${PLIST_PATH}" >/dev/null 2>&1 || true
  /usr/libexec/PlistBuddy -c "Delete :StandardErrorPath" "${PLIST_PATH}" >/dev/null 2>&1 || true
  plutil -lint "${PLIST_PATH}" >/dev/null
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
if [[ -n "${REQUESTED_GSC_COPY_ROOT}" && "${REQUESTED_GSC_COPY_ROOT}" != "${GSC_COPY_ROOT}" ]]; then
  echo "GSC copy run root 必須由 runtime queue 擁有。" >&2
  exit 1
fi
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
if [[ "${ACTION}" == "--activate" || "${ACTION}" == "--activate-only" ]]; then
  if ! (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -c 'import json; from scripts.agy_seo_copy_pipeline import model_route_config_from_environment, validate_gemini_api_model_capabilities; print(json.dumps(validate_gemini_api_model_capabilities(model_route_config_from_environment()), sort_keys=True))'
  ); then
    echo "正式 Writer／Reviewer Gemini API route capability 驗證失敗；尚未 activation。" >&2
    exit 1
  fi
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
if [[ "${ACTION}" == "--activate-only" \
  || "${ACTION}" == "--recover-malformed-activation-only-cohort" ]]; then
  ACTIVATION_ONLY=1
fi
MALFORMED_COHORT_RECOVERY=0
if [[ "${ACTION}" == "--recover-malformed-activation-only-cohort" ]]; then
  MALFORMED_COHORT_RECOVERY=1
fi
PUBLISHER_ONLY_ACTIVATION=0
if [[ "${ACTION}" == "--activate-publisher-only" ]]; then
  PUBLISHER_ONLY_ACTIVATION=1
fi
PUBLISHER_ACTIVATION_ONLY_RESET=0
if [[ "${ACTION}" == "--reset-publisher-activation-only" ]]; then
  PUBLISHER_ACTIVATION_ONLY_RESET=1
fi
PUBLISHER_RESET_SUCCESS_RECEIPT="${STAGE_DIR}/publisher-reset-receipt.json"
if [[ "${PUBLISHER_ACTIVATION_ONLY_RESET}" == "1" ]]; then
  rm -f "${PUBLISHER_RESET_SUCCESS_RECEIPT}"
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
RECOVERY_TRANSACTION_ROOT="${STAGE_DIR}/malformed-cohort-transaction" RECOVERY_SUCCESS_RECEIPT="${LAUNCH_AGENTS_DIR}/.pantheon-malformed-cohort-recovery-receipt.json" RECOVERY_SUCCESS_CANDIDATE="${STAGE_DIR}/malformed-cohort-transaction/committed-receipt.json" RECOVERY_ROLLBACK_RECEIPT="${STAGE_DIR}/malformed-cohort-rollback-receipt.json"
RECOVERY_AUTHORITATIVE_LABELS=(
  "com.pantheon.agy-content-publisher" "com.pantheon.agy-gemini-coordinator" "com.pantheon.agy-gemini-new" "com.pantheon.agy-gemini-rewrite"
  "com.pantheon.agy-gemini-i18n-new" "com.pantheon.agy-gemini-i18n-rewrite" "com.pantheon.content-capacity-guard"
)
RECOVERY_EXPECTED_HASH_BINDINGS=(
  "com.pantheon.agy-content-publisher=4acf50b23652565d3f4aebd18c393e40e371436eb1a898e1833687c70733fefd" "com.pantheon.agy-gemini-coordinator=5b5d4ac37991a98ef8da8430e06e96037f1627e693347f7c3f1d39241298876c"
  "com.pantheon.agy-gemini-new=90aba48482a30ac2d53c5d4018e166f7c3e5bebe89a33b15007de9f76b1e3712" "com.pantheon.agy-gemini-rewrite=373b8162c967e4bd368a5971ea238ab850b0b7b02b5b2ff79c5098041bafe530"
  "com.pantheon.agy-gemini-i18n-new=80614f9e1d356a2b29f4ae26a7822141e49802586e7809b3f3926874d1d844dc" "com.pantheon.agy-gemini-i18n-rewrite=5aa0ebeb148bbe792f79b951bb5358893ffc9c6879d33433b0479a296c12a88b"
  "com.pantheon.content-capacity-guard=e0ba76e9df2124cb0d93d5ccd01ab5b460f20ef3810d2abf412f8e9d70df3c49"
)
RECOVERY_PLIST_REPLACE_COUNT=0 RECOVERY_BOOTOUT_COUNT=0 RECOVERY_BOOTSTRAP_COUNT=0 RECOVERY_BARRIER_TRANSITION_COUNT=0 RECOVERY_CAPACITY_PREFLIGHT_COUNT=0
recovery_probe() {
  local MODE="$1" REASON="${2:-}" INDEX LABEL STATUS
  RECOVERY_ADMISSION_TMP="$(mktemp -d "${TMPDIR:-/tmp}/pantheon-malformed-cohort.XXXXXX")"
  for INDEX in 0 1 2 3 4 5 6; do
    LABEL="${LABELS[${INDEX}]}"
    if ! launchctl print "gui/${USER_ID}/${LABEL}" \
      > "${RECOVERY_ADMISSION_TMP}/${LABEL}.identity" 2>/dev/null; then
      : > "${RECOVERY_ADMISSION_TMP}/${LABEL}.not-loaded"
    fi
  done
  if RECOVERY_PROBE_OUTPUT="$(
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" - "${MODE}" "${REASON}" "${RUNTIME_MANIFEST_FILE}" \
      "${EXPECTED_RUNTIME_MANIFEST_DIGEST}" "${ACTIVATION_BARRIER}" \
      "${RECOVERY_TRANSACTION_ROOT}" "${RECOVERY_ADMISSION_TMP}" \
      "${RECOVERY_SUCCESS_CANDIDATE}" "${ACTIVATION_CORRELATION_ID}" \
      "${RECOVERY_PLIST_REPLACE_COUNT}" "${RECOVERY_BOOTOUT_COUNT}" \
      "${RECOVERY_BOOTSTRAP_COUNT}" "${RECOVERY_BARRIER_TRANSITION_COUNT}" \
      "${RECOVERY_CAPACITY_PREFLIGHT_COUNT}" \
      --authoritative-labels "${RECOVERY_AUTHORITATIVE_LABELS[@]}" \
      --transaction-labels "${LABELS[@]}" --targets "${TARGET_PLISTS[@]}" \
      --hash-bindings "${RECOVERY_EXPECTED_HASH_BINDINGS[@]}" <<'PY'
import hashlib, json, os, plistlib, re, stat, sys
from pathlib import Path

from scripts import pantheon_content_capacity_guard as capacity_guard, pantheon_content_runtime_manifest as runtime_manifest

mode, reason, manifest_path, expected_digest = *sys.argv[1:3], Path(sys.argv[3]), sys.argv[4]; barrier_path, transaction_root, identity_dir = map(Path, sys.argv[5:8])
receipt_path, correlation_id = Path(sys.argv[8]), sys.argv[9]; counts = list(map(int, sys.argv[10:15]))
am, lm = sys.argv.index("--authoritative-labels"), sys.argv.index("--transaction-labels")
tm, hm = sys.argv.index("--targets"), sys.argv.index("--hash-bindings")
authoritative, labels = sys.argv[am + 1 : lm], sys.argv[lm + 1 : tm]
targets = [Path(value) for value in sys.argv[tm + 1 : hm]]


def bindings(values: list[str], code: str) -> dict[str, str]:
    try:
        result = dict(value.split("=", 1) for value in values)
    except ValueError:
        reject(code)
    if len(result) != len(values): reject(code)
    return result


def seal(payload: dict) -> None:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")); payload["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest(); output = json.dumps(payload, sort_keys=True)
    if mode == "success":
        temporary = receipt_path.with_name(receipt_path.name + f".tmp.{os.getpid()}")
        temporary.write_text(output + "\n", encoding="utf-8"); temporary.chmod(0o600); temporary.replace(receipt_path)
    print(output)


def emit(status: str, details: dict, mismatch: str | None = None) -> None:
    payload = {"schema_version": 1,
        "status": status,
        "correlation_id": correlation_id,
        "mutation_count": sum(counts[:4]),
        "operation_counts": dict(zip(("live_plist_replacements", "launchctl_bootout", "launchctl_bootstrap", "barrier_transition", "capacity_preflight_invocations"), counts)),
        "transaction_root_created": transaction_root.exists(),
        "details": details,
    }
    if mismatch: payload["first_mismatch"] = mismatch
    seal(payload)


def reject(code: str, details: object = None) -> None:
    emit("NO-GO", {"mismatch_details": details}, code); raise SystemExit(1)


if mode in {"reject", "capacity-fail"}:
    source = transaction_root / "admission-receipt.json"
    try:
        details = json.loads(source.read_text())["details"]
    except (OSError, ValueError, KeyError):
        details = {}
    emit("NO-GO", details, reason or "formal_capacity_preflight")
    raise SystemExit(1)

formal_labels = [*capacity_guard.SERVICE_LABELS, capacity_guard.CAPACITY_GUARD_LABEL]
expected_order = [
    "com.pantheon.agy-gemini-coordinator", "com.pantheon.agy-gemini-new", "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new", "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.agy-content-publisher", "com.pantheon.content-capacity-guard",
]
expected_hashes = bindings(sys.argv[hm + 1 :], "hash_binding_format")
if list(runtime_manifest.SERVICE_LABELS) != formal_labels: reject("runtime_manifest_service_order")
if authoritative != formal_labels: reject("authoritative_service_order", [formal_labels, authoritative])
if labels != expected_order or len(targets) != 7: reject("transaction_service_order", [expected_order, labels])
if set(expected_hashes) != set(formal_labels): reject("hash_binding_labels")
target_map = {label: target for label, target in zip(labels, targets)}
if len(target_map) != 7: reject("target_binding_labels")
if mode == "admission" and transaction_root.exists(): reject("transaction_root_exists")
if mode in {"revalidate", "success", "rollback"} and not (transaction_root / "admission-receipt.json").is_file(): reject("transaction_root_identity")
try:
    manifest = runtime_manifest.load_manifest(manifest_path, expected_digest)
except Exception as error:
    reject("manifest_invalid", type(error).__name__)

fingerprints, topology, services, outer_counts = {}, [], [], {}
for label in formal_labels:
    target = target_map[label]
    try:
        metadata = target.lstat()
        canonical = target.resolve(strict=True)
    except OSError:
        reject("target_missing", label)
    if (not stat.S_ISREG(metadata.st_mode) or target.is_symlink()
            or canonical != target or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600):
        reject("target_file_identity", label)
    data = target.read_bytes()
    fingerprints[label] = hashlib.sha256(data).hexdigest()
    try:
        payload = plistlib.loads(data)
    except plistlib.InvalidFileException:
        reject("plist_invalid", label)
    if payload.get("Label") != label:
        reject("plist_label_mismatch", label)
    arguments = payload.get("ProgramArguments")
    if not isinstance(arguments, list) or any(type(value) is not str for value in arguments):
        reject("program_arguments_invalid", label)
    if arguments.count("--") != 1:
        reject("outer_separator_count", label)
    separator = arguments.index("--")
    outer, child = arguments[:separator], arguments[separator + 1 :]
    count = outer.count("--activation-only")
    outer_counts[label] = count
    controls = {
        "--barrier": str(barrier_path), "--expected-digest": expected_digest,
        "--manifest": str(manifest_path), "--service-label": label,
    }
    if any(value in {*controls, "--activation-only"} for value in child):
        reject("child_authority_control", label)
    for control, expected in controls.items():
        positions = [index for index, value in enumerate(outer) if value == control]
        if len(positions) != 1 or positions[0] + 1 >= len(outer):
            reject("outer_control_count", [label, control])
        if outer[positions[0] + 1] != expected:
            reject("outer_control_value", [label, control])
    identity_path = identity_dir / f"{label}.identity"
    if (identity_dir / f"{label}.not-loaded").exists() or not identity_path.is_file():
        reject("topology_not_loaded", label)
    identity = identity_path.read_text(encoding="utf-8")
    paths = re.findall(r"^\s*path = (/\S+)\s*$", identity, re.M)
    states = re.findall(r"^\s*state = (.+?)\s*$", identity, re.M)
    pids = re.findall(r"^\s*pid = ([0-9]+)\s*$", identity, re.M)
    exits = re.findall(r"^\s*last exit code = (-?[0-9]+)\s*$", identity, re.M)
    if paths != [str(target)]:
        reject("topology_loaded_path", [label, paths])
    if pids:
        reject("topology_pid_present", label)
    if states != ["not running"]:
        reject("topology_state", [label, states])
    if exits != ["78"]:
        reject("topology_last_exit", [label, exits])
    stable = "\n".join(line for line in identity.splitlines() if not re.match(
        r"^\s*(runs|successful exits|forks|execs|initialized|trampolined|started|proxy started) = ", line
    ))
    item = {"label": label, "loaded_path": paths[0], "state": states[0],
            "pid": None, "last_exit": 78,
            "stable_identity_sha256": hashlib.sha256(stable.encode()).hexdigest()}
    topology.append(item)
    safe_arguments, redact = [], False
    for argument in arguments:
        sensitive = bool(re.search(r"(credential|secret|token|api[-_]?key)", argument, re.I))
        safe_arguments.append("<redacted>" if redact or (sensitive and (not argument.startswith("--") or "=" in argument)) else argument)
        redact = sensitive and argument.startswith("--") and "=" not in argument
    services.append({**item, "fingerprint": fingerprints[label],
                     "outer_activation_only_count": count,
                     "outer_separator_index": separator,
                     "safe_program_arguments": safe_arguments})

try:
    barrier_stat = barrier_path.lstat()
except OSError:
    reject("barrier_missing")
if (not stat.S_ISREG(barrier_stat.st_mode) or barrier_path.is_symlink()
        or barrier_path.resolve(strict=True) != barrier_path
        or barrier_stat.st_uid != os.getuid()
        or stat.S_IMODE(barrier_stat.st_mode) != 0o600):
    reject("barrier_file_identity")
try:
    runtime_manifest.validate_barrier(barrier_path, manifest)
except Exception as error:
    reject("barrier_identity", str(error))
details = {
    "fingerprints": fingerprints, "topology": topology, "services": services,
    "barrier_path": str(barrier_path),
    "barrier_sha256": hashlib.sha256(barrier_path.read_bytes()).hexdigest(),
    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
}
def rollback_evidence(restored: dict) -> dict:
    return {"before_fingerprints": before["fingerprints"], "restored_fingerprints": restored["fingerprints"],
            "before_topology": before["topology"], "restored_topology": restored["topology"],
            "before_barrier_sha256": before["barrier_sha256"], "restored_barrier_sha256": restored["barrier_sha256"],
            "before_manifest_sha256": before["manifest_sha256"], "restored_manifest_sha256": restored["manifest_sha256"]}

if mode in {"admission", "revalidate", "rollback"}:
    if any(count != 0 for count in outer_counts.values()):
        if mode == "admission" and all(count == 1 for count in outer_counts.values()):
            runtime_manifest.aggregate_plist_preflight(
                manifest, [target_map[label] for label in formal_labels],
                expected_activation_mode="activation-only",
            )
            emit("ALREADY_RECOVERED", details)
            raise SystemExit(10)
        reject("activation_mode_count", outer_counts)
    before = json.loads((transaction_root / "admission-receipt.json").read_text())["details"] if mode != "admission" else {}
    for label in formal_labels:
        if fingerprints[label] != expected_hashes[label]:
            if mode == "rollback": emit("ROLLBACK_FAILED", rollback_evidence(details), "rollback_restore_mismatch"); raise SystemExit(1)
            reject("before_sha256", [label, expected_hashes[label], fingerprints[label]])
    try:
        runtime_manifest.aggregate_plist_preflight(
            manifest, [target_map[label] for label in formal_labels]
        )
    except Exception as error:
        reject("before_state_aggregate", str(error))
    if mode == "admission":
        emit("MALFORMED_COHORT_ADMITTED", details)
    else:
        keys = ("fingerprints", "topology", "barrier_path", "barrier_sha256", "manifest_sha256")
        mismatches = [key for key in keys if details[key] != before.get(key)]
        rollback_checks = json.loads(reason) if mode == "rollback" else []
        if mismatches or rollback_checks:
            if mode != "rollback":
                reject("revalidation_" + mismatches[0])
            evidence = rollback_evidence(details); evidence["rollback_check_ids"] = rollback_checks
            emit("ROLLBACK_FAILED", evidence, "rollback_restore_mismatch")
            raise SystemExit(1)
        emit("ROLLBACK_COMPLETE", rollback_evidence(details)) if mode == "rollback" else emit("MALFORMED_COHORT_REVALIDATED", details)
    raise SystemExit(0)

if any(count != 1 for count in outer_counts.values()):
    reject("after_activation_mode_count", outer_counts)
try:
    runtime_manifest.aggregate_plist_preflight(
        manifest, [target_map[label] for label in formal_labels],
        expected_activation_mode="activation-only",
    )
except Exception as error:
    reject("after_state_aggregate", str(error))
before = {}
if (transaction_root / "admission-receipt.json").is_file():
    before = json.loads((transaction_root / "admission-receipt.json").read_text())["details"]
operation_counts = dict(zip(("live_plist_replacements", "launchctl_bootout", "launchctl_bootstrap", "barrier_transition", "capacity_preflight_invocations"), counts))
before_services = {item["label"]: item for item in before.get("services", [])}
services = [{**before_services.get(item["label"], {}), "before_fingerprint": before.get("fingerprints", fingerprints).get(item["label"]),
             "after_fingerprint": item["fingerprint"], "before_outer_activation_only_count": before_services.get(item["label"], {}).get("outer_activation_only_count"),
             "after_outer_activation_only_count": item["outer_activation_only_count"]} for item in details["services"]]
payload = {
    "schema_version": 1,
    "status": "RECOVERY_COMMITTED" if mode == "success" else "ALREADY_RECOVERED",
    "correlation_id": correlation_id,
    "mutation_count": sum(counts[:4]),
    "transaction_root_created": transaction_root.exists(),
    "operation_counts": operation_counts,
    "capacity_preflight": "PASS",
    "capacity_binding": {"before": "CLASSIFIER_EMPTY_SET_PID_REQUIRED", "after": "PASS"},
    "authoritative_service_order": authoritative,
    "transaction_service_order": labels,
    "before_fingerprints": before.get("fingerprints", fingerprints),
    "after_fingerprints": fingerprints,
    "loaded_state_transition": {label: {"before": "loaded:not-running:last-exit-78", "after": "loaded:not-running:last-exit-78"} for label in formal_labels},
    "barrier_fingerprints": {"before": before.get("barrier_sha256"), "after": details["barrier_sha256"]},
    "services": services,
    "details": details,
}
seal(payload)
PY
  )"; then
    STATUS=0
  else
    STATUS="$?"
  fi
  rm -rf "${RECOVERY_ADMISSION_TMP}"
  RECOVERY_ADMISSION_TMP=""
  printf '%s\n' "${RECOVERY_PROBE_OUTPUT}"
  return "${STATUS}"
}
run_recovery_capacity_preflight() {
  local PREFLIGHT_STATUS INDEX LABEL SNAPSHOT_LA SNAPSHOT_VALID=1
  RECOVERY_CAPACITY_PREFLIGHT_OUTPUT=""
  RECOVERY_CAPACITY_SNAPSHOT_HOME="$(mktemp -d "${TMPDIR:-/tmp}/pantheon-capacity-home.XXXXXX")" || return 1
  SNAPSHOT_LA="${RECOVERY_CAPACITY_SNAPSHOT_HOME}/Library/LaunchAgents"
  if ! chmod 700 "${RECOVERY_CAPACITY_SNAPSHOT_HOME}" || ! mkdir -p "${SNAPSHOT_LA}" || ! chmod 700 "${RECOVERY_CAPACITY_SNAPSHOT_HOME}/Library" "${SNAPSHOT_LA}"; then
    rm -rf "${RECOVERY_CAPACITY_SNAPSHOT_HOME}"; RECOVERY_CAPACITY_SNAPSHOT_HOME=""; return 1
  fi
  for INDEX in 0 1 2 3 4 5 6; do
    LABEL="${LABELS[${INDEX}]}"
    if ! install -m 600 "${TARGET_PLISTS[${INDEX}]}" "${SNAPSHOT_LA}/${LABEL}.plist" || ! cmp -s "${TARGET_PLISTS[${INDEX}]}" "${SNAPSHOT_LA}/${LABEL}.plist"; then
      rm -rf "${RECOVERY_CAPACITY_SNAPSHOT_HOME}"; RECOVERY_CAPACITY_SNAPSHOT_HOME=""; return 1
    fi
  done
  RECOVERY_CAPACITY_PREFLIGHT_COUNT=$((RECOVERY_CAPACITY_PREFLIGHT_COUNT + 1))
  if RECOVERY_CAPACITY_PREFLIGHT_OUTPUT="$(
    cd "${REPO_ROOT}"
    PANTHEON_USER_HOME_DIR="${RECOVERY_CAPACITY_SNAPSHOT_HOME}" /bin/bash scripts/install_pantheon_content_capacity_guard_launchd.sh --preflight
  )"; then PREFLIGHT_STATUS=0; else PREFLIGHT_STATUS="$?"; fi
  for INDEX in 0 1 2 3 4 5 6; do cmp -s "${TARGET_PLISTS[${INDEX}]}" "${SNAPSHOT_LA}/${LABELS[${INDEX}]}.plist" || SNAPSHOT_VALID=0; done
  rm -rf "${RECOVERY_CAPACITY_SNAPSHOT_HOME}"; RECOVERY_CAPACITY_SNAPSHOT_HOME=""
  [[ "${PREFLIGHT_STATUS}" == "0" && "${SNAPSHOT_VALID}" == "1" ]] || return 1
  printf '%s\n' "${RECOVERY_CAPACITY_PREFLIGHT_OUTPUT}" \
    | "${PYTHON_BIN}" -c 'import json,sys; p=json.load(sys.stdin); raise SystemExit(0 if isinstance(p,dict) and p.get("status")=="PASS" else 1)'
}
if [[ "${PUBLISHER_ACTIVATION_ONLY_RESET}" == "1" ]]; then
  PUBLISHER_LABEL="com.pantheon.agy-content-publisher"
  PUBLISHER_STAGE_PLIST="${STAGE_DIR}/${PUBLISHER_LABEL}.plist"
  PUBLISHER_TARGET_PLIST="${LAUNCH_AGENTS_DIR}/${PUBLISHER_LABEL}.plist"
  RESET_BACKUP_ROOT="${STAGE_DIR}/publisher-reset-backups"
  OTHER_LABELS=(
    "com.pantheon.agy-gemini-coordinator"
    "com.pantheon.agy-gemini-new"
    "com.pantheon.agy-gemini-rewrite"
    "com.pantheon.agy-gemini-i18n-new"
    "com.pantheon.agy-gemini-i18n-rewrite"
    "com.pantheon.content-capacity-guard"
  )
  ACTIVATION_PHASE="publisher_reset_stage_validation"
  if [[ ! -d "${STAGE_DIR}" \
    || "$(cat "${STAGE_DIR}/manifest-digest" 2>/dev/null || true)" != "${RUNTIME_MANIFEST_DIGEST}" \
    || "$(cat "${STAGE_DIR}/generation" 2>/dev/null || true)" != "${RUNTIME_GENERATION}" \
    || "$(cat "${STAGE_DIR}/publisher-max-runs" 2>/dev/null || true)" != "1" \
    || ! -f "${PUBLISHER_STAGE_PLIST}" \
    || ! -f "${PUBLISHER_TARGET_PLIST}" ]]; then
    echo "Publisher activation-only reset requires matching one-shot stage and live plist." >&2
    false
  fi
  RESET_PUBLISHER_PREFLIGHT_ARGS=(
    publisher-plist
    --manifest "${RUNTIME_MANIFEST_FILE}"
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}"
    --plist "${PUBLISHER_STAGE_PLIST}"
  )
  if [[ -f "${STAGE_DIR}/publisher-exact-run-id" ]]; then
    RESET_EXACT_RUN_ID="$(cat "${STAGE_DIR}/publisher-exact-run-id")"
    if [[ -z "${RESET_EXACT_RUN_ID}" ]]; then
      echo "Publisher activation-only reset exact-run receipt is empty." >&2
      false
    fi
    RESET_PUBLISHER_PREFLIGHT_ARGS+=(--expected-exact-run-id "${RESET_EXACT_RUN_ID}")
  else
    RESET_PUBLISHER_PREFLIGHT_ARGS+=(--require-no-exact-run-id)
  fi
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest \
      "${RESET_PUBLISHER_PREFLIGHT_ARGS[@]}"
  ) >/dev/null
  PUBLISHER_RESET_TEMP_DIR="$(/usr/bin/perl -MCwd=realpath -e \
    'print realpath($ARGV[0]) // ""' "${TMPDIR:-/tmp}")"
  if [[ -z "${PUBLISHER_RESET_TEMP_DIR}" || ! -d "${PUBLISHER_RESET_TEMP_DIR}" ]]; then
    echo "Publisher activation-only reset temp directory is not canonical." >&2
    false
  fi
  PUBLISHER_RESET_TEMP="$(mktemp "${PUBLISHER_RESET_TEMP_DIR}/pantheon-publisher-reset.XXXXXX")"
  cp "${PUBLISHER_TARGET_PLIST}" "${PUBLISHER_RESET_TEMP}"
  chmod 600 "${PUBLISHER_RESET_TEMP}"
  if /usr/libexec/PlistBuddy -c "Print :ProgramArguments" \
    "${PUBLISHER_TARGET_PLIST}" | grep -q -- '--activation-only'; then
    echo "Publisher activation-only reset requires a normal terminal Publisher plist." >&2
    false
  fi
  PUBLISHER_RUN_AT_LOAD="$(/usr/libexec/PlistBuddy -c 'Print :RunAtLoad' "${PUBLISHER_TARGET_PLIST}" 2>/dev/null || true)"
  PUBLISHER_START_INTERVAL="$(/usr/libexec/PlistBuddy -c 'Print :StartInterval' "${PUBLISHER_TARGET_PLIST}" 2>/dev/null || true)"
  PUBLISHER_KEEP_ALIVE="$(/usr/libexec/PlistBuddy -c 'Print :KeepAlive' "${PUBLISHER_TARGET_PLIST}" 2>/dev/null || true)"
  if [[ "${PUBLISHER_RUN_AT_LOAD}" != "true" || -n "${PUBLISHER_KEEP_ALIVE}" ]]; then
    echo "Publisher activation-only reset requires a normal one-shot or scheduled Publisher plist." >&2
    false
  fi
  if [[ -n "${PUBLISHER_START_INTERVAL}" && "${PUBLISHER_START_INTERVAL}" != "60" ]]; then
    echo "Publisher activation-only reset rejects unexpected Publisher StartInterval." >&2
    false
  fi
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest \
      publisher-plist-receipt \
      --plist "${PUBLISHER_TARGET_PLIST}" \
      --activation-mode normal
  ) >/dev/null
  LIVE_REFERENCE_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-coordinator.plist"
  LIVE_IDENTITY_FIELDS=(
    PANTHEON_RUNTIME_IDENTITY
    PANTHEON_RUNTIME_MANIFEST_DIGEST
    PANTHEON_RUNTIME_IDENTITY_DIGEST
    PANTHEON_RUNTIME_CODE_DIGEST
    PANTHEON_RUNTIME_CONFIG_VERSION
    PANTHEON_RUNTIME_GENERATION
    PANTHEON_RUNTIME_ACTOR_ROOT
    PANTHEON_RUNTIME_QUEUE_ROOT
    PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT
    PANTHEON_RUNTIME_LOG_ROOT
    PANTHEON_RUNTIME_ACTOR_HEAD
    PANTHEON_RUNTIME_PYTHON_EXECUTABLE
    PANTHEON_RUNTIME_UV_EXECUTABLE
  )
  for FIELD in "${LIVE_IDENTITY_FIELDS[@]}"; do
    REFERENCE_VALUE="$(/usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:${FIELD}" "${LIVE_REFERENCE_PLIST}" 2>/dev/null || true)"
    PUBLISHER_VALUE="$(/usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:${FIELD}" "${PUBLISHER_TARGET_PLIST}" 2>/dev/null || true)"
    if [[ "${PUBLISHER_VALUE}" != "${REFERENCE_VALUE}" ]]; then
      echo "Publisher activation-only reset live identity drift." >&2
      false
    fi
  done
  if [[ "$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:PANTHEON_RUNTIME_SERVICE_LABEL' "${PUBLISHER_TARGET_PLIST}" 2>/dev/null || true)" != "${PUBLISHER_LABEL}" ]]; then
    echo "Publisher activation-only reset live service-label drift." >&2
    false
  fi
  make_publisher_activation_only_plist "${PUBLISHER_RESET_TEMP}"
  if ! PUBLISHER_RESET_RECEIPT="$(
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest \
      publisher-plist-receipt \
      --plist "${PUBLISHER_RESET_TEMP}" \
      --activation-mode activation-only
  )"; then
    echo "Publisher activation-only reset temp receipt failed: ${PUBLISHER_RESET_RECEIPT:-no receipt output}" >&2
    false
  fi
  ACTIVATION_PHASE="publisher_reset_other_services_validation"
  rm -rf "${RESET_BACKUP_ROOT}"
  mkdir -p "${RESET_BACKUP_ROOT}"
  for LABEL in "${OTHER_LABELS[@]}"; do
    OTHER_LIVE_PLIST="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
    if ! /usr/libexec/PlistBuddy -c "Print :ProgramArguments" \
      "${OTHER_LIVE_PLIST}" | grep -q -- '--activation-only'; then
      echo "Publisher activation-only reset requires other services activation-only." >&2
      false
    fi
    for FIELD in "${LIVE_IDENTITY_FIELDS[@]}"; do
      REFERENCE_VALUE="$(/usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:${FIELD}" "${LIVE_REFERENCE_PLIST}" 2>/dev/null || true)"
      OTHER_VALUE="$(/usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:${FIELD}" "${OTHER_LIVE_PLIST}" 2>/dev/null || true)"
      if [[ "${OTHER_VALUE}" != "${REFERENCE_VALUE}" ]]; then
        echo "Publisher activation-only reset other-service identity drift." >&2
        false
      fi
    done
    if [[ "$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:PANTHEON_RUNTIME_SERVICE_LABEL' "${OTHER_LIVE_PLIST}" 2>/dev/null || true)" != "${LABEL}" ]]; then
      echo "Publisher activation-only reset other-service service-label drift." >&2
      false
    fi
    cp "${OTHER_LIVE_PLIST}" "${RESET_BACKUP_ROOT}/${LABEL}.plist"
    launchctl print "gui/${USER_ID}/${LABEL}" \
      > "${RESET_BACKUP_ROOT}/${LABEL}.identity"
    if grep -Eq '^[[:space:]]*pid = [1-9][0-9]*[[:space:]]*$' \
      "${RESET_BACKUP_ROOT}/${LABEL}.identity"; then
      echo "Publisher activation-only reset requires other services loaded without PID." >&2
      false
    fi
    LOADED_PATH_COUNT="$(sed -nE 's/^[[:space:]]*path = (\/[^[:space:]]+)[[:space:]]*$/\1/p' \
      "${RESET_BACKUP_ROOT}/${LABEL}.identity" | wc -l | tr -d '[:space:]')"
    LOADED_PATH="$(sed -nE 's/^[[:space:]]*path = (\/[^[:space:]]+)[[:space:]]*$/\1/p' \
      "${RESET_BACKUP_ROOT}/${LABEL}.identity")"
    if [[ "${LOADED_PATH_COUNT}" != "1" || "${LOADED_PATH}" != "${OTHER_LIVE_PLIST}" ]]; then
      echo "Publisher activation-only reset other-service launchctl path drift." >&2
      false
    fi
  done
  cp "${PUBLISHER_TARGET_PLIST}" "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.plist"
  RESET_PUBLISHER_PREVIOUS_LOADED=0
  if launchctl print "gui/${USER_ID}/${PUBLISHER_LABEL}" \
    > "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.identity" 2>/dev/null; then
    RESET_PUBLISHER_PREVIOUS_LOADED=1
    if grep -Eq '^[[:space:]]*pid = [1-9][0-9]*[[:space:]]*$' \
      "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.identity"; then
      echo "Publisher activation-only reset refuses a running Publisher." >&2
      false
    fi
    PUBLISHER_LOADED_PATH="$(sed -nE 's/^[[:space:]]*path = (\/[^[:space:]]+)[[:space:]]*$/\1/p' \
      "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.identity")"
    if [[ "${PUBLISHER_LOADED_PATH}" != "${PUBLISHER_TARGET_PLIST}" ]]; then
      echo "Publisher activation-only reset Publisher launchctl path drift." >&2
      false
    fi
  fi
  printf '%s\n' "${RESET_PUBLISHER_PREVIOUS_LOADED}" \
    > "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.previous_loaded"
  rollback_publisher_activation_only_reset() {
    local RETURN_CODE="$1"
    local EXIT_PHASE="$2"
    local ROLLBACK_STATUS="ROLLBACK_COMPLETE"
    trap - ERR
    set +e
    install -m 600 "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.plist" \
      "${PUBLISHER_TARGET_PLIST}" || ROLLBACK_STATUS="ROLLBACK_FAILED"
    launchctl bootout "gui/${USER_ID}/${PUBLISHER_LABEL}" >/dev/null 2>&1 || true
    if [[ "${RESET_PUBLISHER_PREVIOUS_LOADED}" == "1" ]]; then
      launchctl bootstrap "gui/${USER_ID}" "${PUBLISHER_TARGET_PLIST}" >/dev/null 2>&1 \
        || ROLLBACK_STATUS="ROLLBACK_FAILED"
    fi
    for LABEL in "${OTHER_LABELS[@]}"; do
      cmp -s "${RESET_BACKUP_ROOT}/${LABEL}.plist" \
        "${LAUNCH_AGENTS_DIR}/${LABEL}.plist" || ROLLBACK_STATUS="ROLLBACK_FAILED"
    done
    write_failure_receipt "${ROLLBACK_STATUS}" "${RETURN_CODE}" "${EXIT_PHASE}"
    exit "${RETURN_CODE}"
  }
  ACTIVATION_PHASE="publisher_reset_replace_live_plist"
  trap 'rollback_publisher_activation_only_reset $? "${ACTIVATION_PHASE}"' ERR
  install -m 600 "${PUBLISHER_RESET_TEMP}" "${PUBLISHER_TARGET_PLIST}"
  if [[ "${RESET_PUBLISHER_PREVIOUS_LOADED}" == "1" ]]; then
    launchctl bootout "gui/${USER_ID}/${PUBLISHER_LABEL}" >/dev/null
  fi
  if launchctl print "gui/${USER_ID}/${PUBLISHER_LABEL}" >/dev/null 2>&1; then
    false
  fi
  ACTIVATION_PHASE="publisher_reset_bootstrap"
  launchctl bootstrap "gui/${USER_ID}" "${PUBLISHER_TARGET_PLIST}"
  ACTIVATION_PHASE="publisher_reset_settle"
  RESET_PUBLISHER_SETTLED=0
  for ((RESET_SETTLE_ATTEMPT=1; RESET_SETTLE_ATTEMPT<=20; RESET_SETTLE_ATTEMPT++)); do
    if launchctl print "gui/${USER_ID}/${PUBLISHER_LABEL}" \
      > "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.post_identity" 2>/dev/null; then
      PUBLISHER_POST_PATH_COUNT="$(sed -nE 's/^[[:space:]]*path = (\/[^[:space:]]+)[[:space:]]*$/\1/p' \
        "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.post_identity" | wc -l | tr -d '[:space:]')"
      PUBLISHER_POST_PATH="$(sed -nE 's/^[[:space:]]*path = (\/[^[:space:]]+)[[:space:]]*$/\1/p' \
        "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.post_identity")"
      if [[ "${PUBLISHER_POST_PATH_COUNT}" != "1" \
        || "${PUBLISHER_POST_PATH}" != "${PUBLISHER_TARGET_PLIST}" ]]; then
        echo "Publisher activation-only reset settled with launchctl path drift." >&2
        false
      fi
      if grep -Eq '^[[:space:]]*pid = [1-9][0-9]*[[:space:]]*$' \
        "${RESET_BACKUP_ROOT}/${PUBLISHER_LABEL}.post_identity"; then
        if (( RESET_SETTLE_ATTEMPT >= 20 )); then
          echo "Publisher activation-only reset settled with a running Publisher." >&2
          false
        fi
      else
        RESET_PUBLISHER_SETTLED=1
        break
      fi
    fi
    if (( RESET_SETTLE_ATTEMPT < 20 )); then
      /bin/sleep 0.05
    fi
  done
  if [[ "${RESET_PUBLISHER_SETTLED}" != "1" ]]; then
    echo "Publisher activation-only reset did not settle as loaded without PID." >&2
    false
  fi
  ACTIVATION_PHASE="publisher_reset_postcheck"
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest \
      publisher-plist-receipt \
      --plist "${PUBLISHER_TARGET_PLIST}" \
      --activation-mode activation-only
  ) >/dev/null
  for LABEL in "${OTHER_LABELS[@]}"; do
    cmp -s "${RESET_BACKUP_ROOT}/${LABEL}.plist" \
      "${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
    launchctl print "gui/${USER_ID}/${LABEL}" \
      > "${RESET_BACKUP_ROOT}/${LABEL}.post_identity"
  done
  ACTIVATION_PHASE="publisher_reset_success_receipt"
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_capacity_guard \
      --publisher-reset-receipt "${PUBLISHER_RESET_SUCCESS_RECEIPT}" \
      --expected-reset-correlation-id "${ACTIVATION_CORRELATION_ID}" \
      --manifest "${RUNTIME_MANIFEST_FILE}" \
      --expected-digest "${RUNTIME_MANIFEST_DIGEST}" \
      --launch-agents-dir "${LAUNCH_AGENTS_DIR}" \
      --reset-proof-dir "${RESET_BACKUP_ROOT}" \
      publisher-reset-receipt
  ) >/dev/null
  trap - ERR
  rm -rf "${RESET_BACKUP_ROOT}"
  echo "Pantheon Publisher activation-only reset 已完成。"
  echo "狀態：launchctl print gui/${USER_ID}/${PUBLISHER_LABEL}"
  exit 0
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
  PUBLISHER_PLIST_PREFLIGHT_ARGS=(
    publisher-plist
    --manifest "${RUNTIME_MANIFEST_FILE}"
    --expected-digest "${EXPECTED_RUNTIME_MANIFEST_DIGEST}"
    --plist "${PUBLISHER_STAGE_PLIST}"
  )
  if [[ -f "${STAGE_DIR}/publisher-exact-run-id" ]]; then
    PUBLISHER_EXACT_RUN_ID="$(cat "${STAGE_DIR}/publisher-exact-run-id")"
    if [[ -z "${PUBLISHER_EXACT_RUN_ID}" ]]; then
      echo "Publisher-only activation exact-run-id receipt is empty." >&2
      false
    fi
    PUBLISHER_PLIST_PREFLIGHT_ARGS+=(
      --expected-exact-run-id "${PUBLISHER_EXACT_RUN_ID}"
    )
  else
    PUBLISHER_PLIST_PREFLIGHT_ARGS+=(--require-no-exact-run-id)
  fi
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" -m scripts.pantheon_content_runtime_manifest \
      "${PUBLISHER_PLIST_PREFLIGHT_ARGS[@]}"
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
  ACTIVATION_PHASE="publisher_only_one_shot_plist"
  make_publisher_only_one_shot_plist "${PUBLISHER_STAGE_PLIST}"
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
BOOTED_OUT_LABELS=()
record_confirmed_bootout() {
  local LABEL="$1" MARKER_TMP STATUS
  BOOTED_OUT_LABELS+=("${LABEL}")
  if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
    RECOVERY_BOOTOUT_COUNT=$((RECOVERY_BOOTOUT_COUNT + 1))
    MARKER_TMP="${RECOVERY_TRANSACTION_ROOT}/booted-out/${LABEL}.tmp.$$"
    if printf '%s\n' "${LABEL}" > "${MARKER_TMP}"; then
      :
    else
      STATUS="$?"
      return "${STATUS}"
    fi
    if chmod 600 "${MARKER_TMP}"; then
      :
    else
      STATUS="$?"
      return "${STATUS}"
    fi
    if mv "${MARKER_TMP}" "${RECOVERY_TRANSACTION_ROOT}/booted-out/${LABEL}"; then
      :
    else
      STATUS="$?"
      return "${STATUS}"
    fi
  fi
}
propagate_failure_status() {
  return "$1"
}
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
  was_booted_out_by_transaction() {
    local CANDIDATE
    if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" \
      && -f "${RECOVERY_TRANSACTION_ROOT}/booted-out/$1" ]]; then
      return 0
    fi
    if (( ${#BOOTED_OUT_LABELS[@]} > 0 )); then
      for CANDIDATE in "${BOOTED_OUT_LABELS[@]}"; do
        [[ "${CANDIDATE}" == "$1" ]] && return 0
      done
    fi
    return 1
  }
  trap - ERR
  set +e
  rm -f "${ACTIVATION_BARRIER}" || record_rollback_failure "rollback.barrier.remove"
  if (( ${#STARTED_LABELS[@]} > 0 )); then
    for LABEL in "${STARTED_LABELS[@]}"; do
      if ! launchctl bootout "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
        record_rollback_failure "rollback.bootout"
      fi
      if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
        record_rollback_failure "rollback.bootout.loaded"
      fi
    done
  fi
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
      if was_booted_out_by_transaction "${LABEL}"; then
        if ! launchctl bootstrap "gui/${USER_ID}" "${TARGET}" >/dev/null 2>&1 \
          || ! launchctl print "gui/${USER_ID}/${LABEL}" \
            > "${STAGE_DIR}/${LABEL}.actual_identity" 2>/dev/null; then
          record_rollback_failure "rollback.bootstrap"
          continue
        fi
      elif ! launchctl print "gui/${USER_ID}/${LABEL}" \
        > "${STAGE_DIR}/${LABEL}.actual_identity" 2>/dev/null; then
        record_rollback_failure "rollback.identity.loaded_missing"
        continue
      fi
      normalize_control_identity "${STAGE_DIR}/${LABEL}.actual_identity" \
        > "${STAGE_DIR}/${LABEL}.actual_identity.stable"
      cmp -s "${STAGE_DIR}/${LABEL}.previous_identity.stable" \
        "${STAGE_DIR}/${LABEL}.actual_identity.stable" \
        || record_rollback_failure "rollback.identity"
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
  if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
    RECOVERY_ROLLBACK_OK=1
    recovery_probe rollback "$(rollback_check_ids_json)" \
      > "${RECOVERY_ROLLBACK_RECEIPT}.tmp.$$" || RECOVERY_ROLLBACK_OK=0
    if ! chmod 600 "${RECOVERY_ROLLBACK_RECEIPT}.tmp.$$" \
      || ! mv "${RECOVERY_ROLLBACK_RECEIPT}.tmp.$$" "${RECOVERY_ROLLBACK_RECEIPT}"; then
      RECOVERY_ROLLBACK_OK=0
    fi
    [[ "${RECOVERY_ROLLBACK_OK}" == "1" ]] || record_rollback_failure "rollback.recovery.verification"
    if [[ -f "${RECOVERY_SUCCESS_RECEIPT}" ]] && (cd "${REPO_ROOT}" && "${PYTHON_BIN}" -c \
      'import json,sys; raise SystemExit(json.load(open(sys.argv[1])).get("correlation_id") != sys.argv[2])' \
      "${RECOVERY_SUCCESS_RECEIPT}" "${ACTIVATION_CORRELATION_ID}"); then
      rm -f "${RECOVERY_SUCCESS_RECEIPT}" || record_rollback_failure "rollback.committed_receipt.remove"
    fi
    if [[ "${RECOVERY_ROLLBACK_OK}" == "1" && "${ROLLBACK_FAILED}" == "0" ]]; then
      rm -rf "${RECOVERY_TRANSACTION_ROOT}" || record_rollback_failure "rollback.transaction.cleanup"
    fi
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
capture_legacy_transition_previous_barrier() {
  local OUTPUT_MANIFEST="${STAGE_DIR}/previous-runtime-manifest.json"
  [[ "${ACTIVATION_ONLY}" == "1" ]] || return 1
  [[ "${PREVIOUS_BARRIER_PATH}" == /* && -f "${PREVIOUS_BARRIER_PATH}" ]] \
    || return 1
  [[ "${PREVIOUS_MANIFEST_DIGEST}" =~ ^[0-9a-f]{64}$ ]] || return 1
  if ! (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" - "${STAGE_DIR}" "${PREVIOUS_BARRIER_PATH}" \
      "${PREVIOUS_MANIFEST_DIGEST}" "${OUTPUT_MANIFEST}" \
      "${TARGET_PLISTS[@]}" <<'PY'
import json
import os
import plistlib
import re
import sys
from pathlib import Path

from scripts import pantheon_content_runtime_manifest as runtime_manifest

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STAGE_DIR = Path(sys.argv[1])
BARRIER_PATH = Path(sys.argv[2])
EXPECTED_DIGEST = sys.argv[3]
OUTPUT_MANIFEST = Path(sys.argv[4])
TARGETS = [Path(value) for value in sys.argv[5:]]


def reject() -> None:
    raise SystemExit(1)


def canonical_existing(path: Path) -> str:
    try:
        return str(path.parent.resolve(strict=True) / path.name)
    except OSError:
        reject()


def read_plist(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            payload = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException):
        reject()
    if not isinstance(payload, dict):
        reject()
    return payload


def parse_outer_arguments(arguments: list[object]) -> dict[str, str]:
    value_controls = {
        "--barrier",
        "--expected-digest",
        "--manifest",
        "--service-label",
    }
    authority_controls = value_controls | {"--activation-only"}
    if any(not isinstance(value, str) for value in arguments):
        reject()
    string_arguments = [str(value) for value in arguments]
    if string_arguments.count("--") != 1:
        reject()
    separator = string_arguments.index("--")
    outer = string_arguments[:separator]
    child = string_arguments[separator + 1 :]
    if (
        len(outer) < 4
        or outer[1:4]
        != ["-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec"]
        or any(value in authority_controls for value in child)
    ):
        reject()

    counts = {name: 0 for name in authority_controls}
    values: dict[str, str] = {}
    index = 4
    while index < len(outer):
        name = outer[index]
        if name == "--activation-only":
            counts[name] += 1
            index += 1
            continue
        if not name.startswith("--") or index + 1 >= len(outer):
            reject()
        value = outer[index + 1]
        if value.startswith("--"):
            reject()
        if name in value_controls:
            counts[name] += 1
            values[name] = value
        index += 2
    if any(counts[name] != 1 for name in authority_controls):
        reject()
    return values


def read_identity_path(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        reject()
    matches = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("pid =") and stripped != "pid = 0":
            reject()
        if stripped == "state = running":
            reject()
        match = re.fullmatch(r"\s*path = (/[^\s]+)", line)
        if match:
            matches.append(match.group(1))
    if len(matches) != 1:
        reject()
    return matches[0]


def require_env(environment: dict[str, object], key: str) -> str:
    value = environment.get(key)
    if not isinstance(value, str) or not value:
        reject()
    return value


runtime_labels = list(runtime_manifest.SERVICE_LABELS)
labels = [target.name.removesuffix(".plist") for target in TARGETS]
if (
    len(TARGETS) != len(runtime_labels)
    or any(not target.name.endswith(".plist") for target in TARGETS)
    or set(labels) != set(runtime_labels)
):
    reject()
common: dict[str, str] | None = None
expected_barrier = str(BARRIER_PATH)

if BARRIER_PATH.is_symlink():
    reject()
try:
    barrier_payload = json.loads(BARRIER_PATH.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    reject()

for label, target in zip(labels, TARGETS):
    backup = STAGE_DIR / "backups" / f"{label}.plist"
    loaded_marker = STAGE_DIR / f"{label}.previous_loaded"
    identity_path = STAGE_DIR / f"{label}.previous_identity"
    if loaded_marker.read_text(encoding="utf-8").strip() != "1":
        reject()
    if backup.is_symlink() or target.is_symlink():
        reject()
    if not backup.is_file() or not target.is_file():
        reject()
    try:
        if backup.read_bytes() != target.read_bytes():
            reject()
    except OSError:
        reject()
    loaded_path = read_identity_path(identity_path)
    if loaded_path != str(target):
        reject()
    if canonical_existing(Path(loaded_path)) != canonical_existing(target):
        reject()

    payload = read_plist(backup)
    if payload.get("Label") != label:
        reject()
    arguments = payload.get("ProgramArguments")
    environment = payload.get("EnvironmentVariables")
    if not isinstance(arguments, list) or not isinstance(environment, dict):
        reject()
    outer_arguments = parse_outer_arguments(arguments)
    if outer_arguments["--barrier"] != expected_barrier:
        reject()
    if outer_arguments["--expected-digest"] != EXPECTED_DIGEST:
        reject()
    if outer_arguments["--service-label"] != label:
        reject()
    manifest_path = outer_arguments["--manifest"]
    if environment.get("PANTHEON_RUNTIME_MANIFEST") not in (None, manifest_path):
        reject()
    tuple_fields = {
        "identity": require_env(environment, "PANTHEON_RUNTIME_IDENTITY"),
        "runtime_identity_digest": require_env(
            environment, "PANTHEON_RUNTIME_IDENTITY_DIGEST"
        ),
        "runtime_digest": require_env(environment, "PANTHEON_RUNTIME_CODE_DIGEST"),
        "config_version": require_env(
            environment, "PANTHEON_RUNTIME_CONFIG_VERSION"
        ),
        "generation": require_env(environment, "PANTHEON_RUNTIME_GENERATION"),
        "actor_root": require_env(environment, "PANTHEON_RUNTIME_ACTOR_ROOT"),
        "queue_root": require_env(environment, "PANTHEON_RUNTIME_QUEUE_ROOT"),
        "publisher_state_root": require_env(
            environment, "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT"
        ),
        "log_root": require_env(environment, "PANTHEON_RUNTIME_LOG_ROOT"),
        "manifest_path": manifest_path,
    }
    if require_env(environment, "PANTHEON_RUNTIME_MANIFEST_DIGEST") != EXPECTED_DIGEST:
        reject()
    if require_env(environment, "PANTHEON_RUNTIME_SERVICE_LABEL") != label:
        reject()
    for source, target_key in (
        ("PANTHEON_RUNTIME_ACTOR_HEAD", "actor_head"),
        ("PANTHEON_RUNTIME_PYTHON_EXECUTABLE", "python_executable"),
        ("PANTHEON_RUNTIME_UV_EXECUTABLE", "uv_executable"),
    ):
        value = environment.get(source)
        if isinstance(value, str) and value:
            tuple_fields[target_key] = value
    if common is None:
        common = tuple_fields
    elif common != tuple_fields:
        reject()

if common is None:
    reject()
manifest = runtime_manifest.build_manifest(
    actor_root=Path(common["actor_root"]),
    queue_root=Path(common["queue_root"]),
    publisher_state_root=Path(common["publisher_state_root"]),
    log_root=Path(common["log_root"]),
    identity=common["identity"],
    runtime_digest=common["runtime_digest"],
    config_version=common["config_version"],
    generation=common["generation"],
    actor_head=common.get("actor_head"),
    python_executable=Path(common["python_executable"])
    if "python_executable" in common
    else None,
    uv_executable=Path(common["uv_executable"])
    if "uv_executable" in common
    else None,
)
if manifest["manifest_digest"] != EXPECTED_DIGEST:
    reject()
if manifest["runtime_identity_digest"] != common["runtime_identity_digest"]:
    reject()
expected_payload = {
    "schema_version": runtime_manifest.SCHEMA_VERSION,
    "manifest_digest": EXPECTED_DIGEST,
    "runtime_identity_digest": manifest["runtime_identity_digest"],
    "generation": manifest["generation"],
    "owner_uid": os.getuid(),
    "service_labels": runtime_labels,
}
if any(barrier_payload.get(key) != value for key, value in expected_payload.items()):
    reject()
ack_digests = barrier_payload.get("ack_digests")
if (
    not isinstance(ack_digests, list)
    or len(ack_digests) != len(runtime_labels)
    or any(not isinstance(value, str) or SHA256_RE.fullmatch(value) is None for value in ack_digests)
):
    reject()
runtime_manifest.write_manifest(OUTPUT_MANIFEST, manifest)
PY
  ) >/dev/null; then
    return 1
  fi
  cp "${PREVIOUS_BARRIER_PATH}" "${STAGE_DIR}/previous-barrier" || return 1
  printf '%s\n' "${PREVIOUS_MANIFEST_DIGEST}" > "${STAGE_DIR}/previous-manifest-digest"
  printf '%s\n' "${PREVIOUS_BARRIER_PATH}" > "${STAGE_DIR}/previous-barrier-path"
  return 0
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

reject_recovery_before_live_mutation() {
  local RETURN_CODE="$1"
  local EXIT_PHASE="$2"
  trap - ERR
  set +e
  recovery_probe reject "${EXIT_PHASE}" >/dev/null
  write_failure_receipt "ACTIVATION_REJECTED" "${RETURN_CODE}" "${EXIT_PHASE}"
  rm -rf "${RECOVERY_TRANSACTION_ROOT}"
  exit "${RETURN_CODE}"
}

if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
  ACTIVATION_PHASE="malformed_cohort_admission"
  if recovery_probe admission; then
    RECOVERY_ADMISSION_STATUS=0
  else
    RECOVERY_ADMISSION_STATUS="$?"
  fi
  if [[ "${RECOVERY_ADMISSION_STATUS}" == "10" ]]; then
    if run_recovery_capacity_preflight; then
      recovery_probe already >/dev/null
      printf '%s\n' "${RECOVERY_PROBE_OUTPUT}"
      trap - ERR
      exit 0
    fi
    recovery_probe capacity-fail formal_capacity_preflight >/dev/null || true
    printf '%s\n' "${RECOVERY_PROBE_OUTPUT}"
    trap - ERR
    exit 1
  elif [[ "${RECOVERY_ADMISSION_STATUS}" != "0" ]]; then
    trap - ERR
    exit 1
  fi
  RECOVERY_FIRST_ADMISSION_OUTPUT="${RECOVERY_PROBE_OUTPUT}"
  ACTIVATION_PHASE="malformed_cohort_admission_revalidation"
  if ! recovery_probe admission >/dev/null \
    || [[ "${RECOVERY_PROBE_OUTPUT}" != "${RECOVERY_FIRST_ADMISSION_OUTPUT}" ]]; then
    recovery_probe reject admission_revalidation_drift >/dev/null || true
    printf '%s\n' "${RECOVERY_PROBE_OUTPUT}"
    trap - ERR
    exit 1
  fi
  RECOVERY_PROBE_OUTPUT="${RECOVERY_FIRST_ADMISSION_OUTPUT}"
  ACTIVATION_PHASE="malformed_cohort_transaction_initialization"
  mkdir "${RECOVERY_TRANSACTION_ROOT}"
  trap 'reject_recovery_before_live_mutation $? "${ACTIVATION_PHASE}"' ERR
  mkdir "${RECOVERY_TRANSACTION_ROOT}/booted-out"
  chmod 700 "${RECOVERY_TRANSACTION_ROOT}/booted-out"
  printf '%s\n' "${RECOVERY_PROBE_OUTPUT}" \
    > "${RECOVERY_TRANSACTION_ROOT}/admission-receipt.json"
  chmod 600 "${RECOVERY_TRANSACTION_ROOT}/admission-receipt.json"
fi

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
elif capture_legacy_transition_previous_barrier; then
  :
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
if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
  ACTIVATION_PHASE="malformed_cohort_previous_barrier_snapshot_validation"
  if [[ ! -f "${STAGE_DIR}/previous-barrier" \
    || ! -f "${STAGE_DIR}/previous-runtime-manifest.json" \
    || ! -f "${STAGE_DIR}/previous-manifest-digest" \
    || ! -f "${STAGE_DIR}/previous-barrier-path" ]]; then
    echo "malformed cohort previous barrier snapshot 不完整。" >&2
    false
  fi
  if ! cmp -s "${STAGE_DIR}/previous-barrier" "${ACTIVATION_BARRIER}" \
    || ! cmp -s "${STAGE_DIR}/previous-runtime-manifest.json" \
      "${RUNTIME_MANIFEST_FILE}"; then
    echo "malformed cohort previous barrier snapshot fingerprint 不一致。" >&2
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
if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
  ACTIVATION_PHASE="malformed_cohort_toctou_validation"
  if ! recovery_probe revalidate >/dev/null; then
    write_failure_receipt "ACTIVATION_REJECTED" 1 "${ACTIVATION_PHASE}"
    rm -rf "${RECOVERY_TRANSACTION_ROOT}"
    echo "malformed cohort 在 replace 前 drift，拒絕 recovery。" >&2
    trap - ERR
    exit 1
  fi
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
  if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
    RECOVERY_PLIST_REPLACE_COUNT=$((RECOVERY_PLIST_REPLACE_COUNT + 1))
  fi
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
    BOOTOUT_RETURN_CODE=0
    if launchctl bootout "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      :
    else
      BOOTOUT_RETURN_CODE="$?"
    fi
    if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
      BOOTOUT_CONFIRMED=0
    else
      BOOTOUT_CONFIRMED=1
      record_confirmed_bootout "${LABEL}"
    fi
    if [[ "${BOOTOUT_RETURN_CODE}" != "0" ]]; then
      propagate_failure_status "${BOOTOUT_RETURN_CODE}"
    elif [[ "${BOOTOUT_CONFIRMED}" != "1" ]]; then
      false
    fi
  fi
done
ACTIVATION_PHASE="bootstrap_staged_services"
for INDEX in 0 1 2 3 4 5 6; do
  LABEL="${LABELS[${INDEX}]}"
  TARGET="${TARGET_PLISTS[${INDEX}]}"
  BOOTSTRAP_RETURN_CODE=0
  if launchctl bootstrap "gui/${USER_ID}" "${TARGET}"; then
    :
  else
    BOOTSTRAP_RETURN_CODE="$?"
  fi
  if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null; then
    BOOTSTRAP_CONFIRMED=1
    STARTED_LABELS+=("${LABEL}")
    if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
      RECOVERY_BOOTSTRAP_COUNT=$((RECOVERY_BOOTSTRAP_COUNT + 1))
    fi
  else
    BOOTSTRAP_CONFIRMED=0
  fi
  if [[ "${BOOTSTRAP_RETURN_CODE}" != "0" ]]; then
    propagate_failure_status "${BOOTSTRAP_RETURN_CODE}"
  elif [[ "${BOOTSTRAP_CONFIRMED}" != "1" ]]; then
    false
  fi
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
if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
  RECOVERY_BARRIER_TRANSITION_COUNT=$((RECOVERY_BARRIER_TRANSITION_COUNT + 1))
fi
if [[ "${ACTIVATION_ONLY}" == "1" ]]; then
  ACTIVATION_PHASE="activation_only_postcheck"
  for LABEL in "${LABELS[@]}"; do
    launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null
  done
fi
if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
  ACTIVATION_PHASE="malformed_cohort_formal_capacity_preflight"
  if ! run_recovery_capacity_preflight; then
    printf '%s\n' "${RECOVERY_CAPACITY_PREFLIGHT_OUTPUT}" >&2
    echo "formal Capacity preflight 未通過，觸發 recovery rollback。" >&2
    false
  fi
  ACTIVATION_PHASE="malformed_cohort_success_receipt"
  recovery_probe success
  [[ -f "${RECOVERY_SUCCESS_CANDIDATE}" && ! -L "${RECOVERY_SUCCESS_CANDIDATE}" ]] \
    && chmod 600 "${RECOVERY_SUCCESS_CANDIDATE}"
  ACTIVATION_PHASE="malformed_cohort_success_publish"
  mv "${RECOVERY_SUCCESS_CANDIDATE}" "${RECOVERY_SUCCESS_RECEIPT}"
fi
trap - ERR
rm -rf "${STAGE_DIR}"

if [[ "${MALFORMED_COHORT_RECOVERY}" == "1" ]]; then
  echo "Pantheon malformed activation-only cohort recovery 已完成。"
elif [[ "${ACTIVATION_ONLY}" == "1" ]]; then
  echo "Pantheon 七服務 activation-only 已完成。"
else
  echo "Pantheon 七服務 aggregate activation 已完成。"
fi
echo "Queue root：${QUEUE_ROOT}"
echo "狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-coordinator"
echo "停止：launchctl bootout gui/${USER_ID} ${TARGET_PLIST}"
echo "Lane 狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}"
echo "Lane plist：${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}.plist"
