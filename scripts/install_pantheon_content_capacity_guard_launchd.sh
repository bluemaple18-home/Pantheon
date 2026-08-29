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
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.content-capacity-guard.plist"
STAGE_DIR="${LAUNCH_AGENTS_DIR}/.pantheon-four-lane-stage"
PUBLISHER_RESET_RECEIPT="${STAGE_DIR}/publisher-reset-receipt.json"
EXPECTED_RESET_CORRELATION_ID="${PANTHEON_ACTIVATION_CORRELATION_ID:-}"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.content-capacity-guard.plist.example"
TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-content-capacity-guard.XXXXXX")"
PREFLIGHT_RECEIPT="$(mktemp "${TMPDIR:-/tmp}/pantheon-content-capacity-guard-preflight.XXXXXX")"

cleanup() {
  local RETURN_CODE="$?"
  rm -f "${TEMP_PLIST}" "${PREFLIGHT_RECEIPT}"
  return "${RETURN_CODE}"
}
trap cleanup EXIT

TEMP_PLIST_REALPATH="$(/usr/bin/perl -MCwd=realpath -e 'print realpath($ARGV[0]) // ""' "${TEMP_PLIST}")"
if [[ -z "${TEMP_PLIST_REALPATH}" || ! -f "${TEMP_PLIST_REALPATH}" || -L "${TEMP_PLIST_REALPATH}" ]]; then
  echo "無法取得 capacity temporary plist 的 canonical path。" >&2
  exit 1
fi
TEMP_PLIST="${TEMP_PLIST_REALPATH}"

if [[ "${ACTION}" != "--install" && "${ACTION}" != "--preflight" \
  && "${ACTION}" != "--install-recovery-stage" ]]; then
  echo "用法：scripts/install_pantheon_content_capacity_guard_launchd.sh [--preflight|--install|--install-recovery-stage]" >&2
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
PUBLISHER_ROOT="$(manifest_field publisher_state_root)"
LOG_ROOT="$(manifest_field log_root)"
RUNTIME_MANIFEST_DIGEST="$(manifest_field manifest_digest)"
RUNTIME_IDENTITY="$(manifest_field identity)"
RUNTIME_IDENTITY_DIGEST="$(manifest_field runtime_identity_digest)"
RUNTIME_CODE_DIGEST="$(manifest_field runtime_digest)"
RUNTIME_CONFIG_VERSION="$(manifest_field config_version)"
RUNTIME_GENERATION="$(manifest_field generation)"
RUNTIME_ACTOR_HEAD="$(optional_manifest_field actor_head)"
RUNTIME_PYTHON_EXECUTABLE="$(optional_manifest_field python_executable)"
RUNTIME_UV_EXECUTABLE="$(manifest_field uv_executable)"
ACTIVATION_BARRIER="${PUBLISHER_ROOT}/four-lane-activation-${RUNTIME_GENERATION}.barrier"
READY_ROOT="${STAGE_DIR}/readiness/${RUNTIME_GENERATION}"
STATE_FILE="${PANTHEON_CAPACITY_GUARD_STATE_FILE:-${QUEUE_ROOT}/capacity-guard-state.json}"
for PATH_VALUE in "${QUEUE_ROOT}" "${PUBLISHER_ROOT}" "${LOG_ROOT}" "${STATE_FILE}"; do
  if [[ "${PATH_VALUE}" != /* ]]; then
    echo "容量 watchdog 路徑必須是 absolute path。" >&2
    exit 1
  fi
done
if [[ "${ACTOR_ROOT}" != "${REPO_ROOT}" ]]; then
  echo "runtime manifest actor root 與 capacity installer 不一致。" >&2
  exit 1
fi
for LEGACY_QUEUE_ROOT in "${AGY_GEMINI_QUEUE_ROOT:-}" "${PANTHEON_GEMINI_QUEUE_ROOT:-}"; do
  if [[ -n "${LEGACY_QUEUE_ROOT}" && "${LEGACY_QUEUE_ROOT}" != "${QUEUE_ROOT}" ]]; then
    echo "runtime manifest queue root 與 legacy override 不一致。" >&2
    exit 1
  fi
done
if [[ -n "${PANTHEON_CONTENT_PUBLISHER_ROOT:-}" \
  && "${PANTHEON_CONTENT_PUBLISHER_ROOT}" != "${PUBLISHER_ROOT}" ]]; then
  echo "runtime manifest publisher state root 與 legacy override 不一致。" >&2
  exit 1
fi
HARDENED_RUNTIME_ENV=(PANTHEON_RUNTIME_UV_EXECUTABLE="${RUNTIME_UV_EXECUTABLE}")
if [[ -n "${RUNTIME_ACTOR_HEAD}" ]]; then
  HARDENED_RUNTIME_ENV+=("PANTHEON_RUNTIME_ACTOR_HEAD=${RUNTIME_ACTOR_HEAD}")
fi
if [[ -n "${RUNTIME_PYTHON_EXECUTABLE}" ]]; then
  HARDENED_RUNTIME_ENV+=("PANTHEON_RUNTIME_PYTHON_EXECUTABLE=${RUNTIME_PYTHON_EXECUTABLE}")
fi

run_capacity_preflight() {
  local PREFLIGHT_OUTPUT
  local PREFLIGHT_STATUS
  set +e
  PREFLIGHT_OUTPUT="$(
    cd "${REPO_ROOT}"
    env \
      PANTHEON_FORMAL_RUNTIME=1 \
      PANTHEON_RUNTIME_MANIFEST="${RUNTIME_MANIFEST_FILE}" \
      PANTHEON_RUNTIME_MANIFEST_DIGEST="${RUNTIME_MANIFEST_DIGEST}" \
      PANTHEON_RUNTIME_IDENTITY="${RUNTIME_IDENTITY}" \
      PANTHEON_RUNTIME_IDENTITY_DIGEST="${RUNTIME_IDENTITY_DIGEST}" \
      PANTHEON_RUNTIME_CODE_DIGEST="${RUNTIME_CODE_DIGEST}" \
      PANTHEON_RUNTIME_CONFIG_VERSION="${RUNTIME_CONFIG_VERSION}" \
      PANTHEON_RUNTIME_GENERATION="${RUNTIME_GENERATION}" \
      PANTHEON_RUNTIME_ACTOR_ROOT="${ACTOR_ROOT}" \
      PANTHEON_RUNTIME_QUEUE_ROOT="${QUEUE_ROOT}" \
      PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT="${PUBLISHER_ROOT}" \
      PANTHEON_RUNTIME_LOG_ROOT="${LOG_ROOT}" \
      PANTHEON_RUNTIME_SERVICE_LABEL="com.pantheon.content-capacity-guard" \
      "${HARDENED_RUNTIME_ENV[@]}" \
      "${PYTHON_BIN}" -m scripts.pantheon_content_capacity_guard \
      --queue-root "${QUEUE_ROOT}" \
      --publisher-root "${PUBLISHER_ROOT}" \
      --log-root "${LOG_ROOT}" \
      --state-file "${STATE_FILE}" \
      preflight
  )"
  PREFLIGHT_STATUS="$?"
  set -e
  printf '%s\n' "${PREFLIGHT_OUTPUT}" > "${PREFLIGHT_RECEIPT}"
  if [[ "${PREFLIGHT_STATUS}" == "0" \
    && ! -f "${STAGE_DIR}/manifest-digest" \
    && ! -f "${STAGE_DIR}/generation" \
    && ! -f "${STAGE_DIR}/publisher-max-runs" ]]; then
    printf '%s\n' "${PREFLIGHT_OUTPUT}"
    return 0
  fi
  TRANSITION_ARGS=(
    -m scripts.pantheon_content_capacity_guard
    --preflight-receipt "${PREFLIGHT_RECEIPT}"
    --manifest "${RUNTIME_MANIFEST_FILE}"
    --expected-digest "${RUNTIME_MANIFEST_DIGEST}"
    --barrier "${ACTIVATION_BARRIER}"
    --launch-agents-dir "${LAUNCH_AGENTS_DIR}"
    --capacity-plist "${TEMP_PLIST}"
    --publisher-reset-receipt "${PUBLISHER_RESET_RECEIPT}"
    --expected-reset-correlation-id "${EXPECTED_RESET_CORRELATION_ID}"
  )
  if [[ "${ACTION}" == "--install-recovery-stage" ]]; then
    TRANSITION_ARGS+=(--recovery-from-normal-stopped)
  fi
  if (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" "${TRANSITION_ARGS[@]}" preactivation-transition
  ); then
    return 0
  fi
  printf '%s\n' "${PREFLIGHT_OUTPUT}"
  if [[ "${PREFLIGHT_STATUS}" == "0" ]]; then
    return 1
  fi
  return "${PREFLIGHT_STATUS}"
}

cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_BIN}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:5 ${ACTIVATION_BARRIER}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:7 ${RUNTIME_MANIFEST_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:9 ${RUNTIME_MANIFEST_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${READY_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:17 ${PYTHON_BIN}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:21 ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:23 ${PUBLISHER_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:25 ${LOG_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:27 ${STATE_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST_DIGEST ${RUNTIME_MANIFEST_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST ${RUNTIME_MANIFEST_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY_DIGEST ${RUNTIME_IDENTITY_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_CODE_DIGEST ${RUNTIME_CODE_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_CONFIG_VERSION ${RUNTIME_CONFIG_VERSION}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_GENERATION ${RUNTIME_GENERATION}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY ${RUNTIME_IDENTITY}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_ACTOR_ROOT ${ACTOR_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_QUEUE_ROOT ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT ${PUBLISHER_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_LOG_ROOT ${LOG_ROOT}" "${TEMP_PLIST}"
if [[ -n "${RUNTIME_ACTOR_HEAD}" ]]; then
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_ACTOR_HEAD string ${RUNTIME_ACTOR_HEAD}" "${TEMP_PLIST}"
fi
if [[ -n "${RUNTIME_PYTHON_EXECUTABLE}" ]]; then
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_PYTHON_EXECUTABLE string ${RUNTIME_PYTHON_EXECUTABLE}" "${TEMP_PLIST}"
fi
if [[ -n "${RUNTIME_UV_EXECUTABLE}" ]]; then
  /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PANTHEON_RUNTIME_UV_EXECUTABLE string ${RUNTIME_UV_EXECUTABLE}" "${TEMP_PLIST}"
fi
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_ROOT}/pantheon-content-capacity-guard.stdout.log" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_ROOT}/pantheon-content-capacity-guard.stderr.log" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null
run_capacity_preflight

if [[ "${ACTION}" == "--preflight" ]]; then
  exit 0
fi

mkdir -p "${STAGE_DIR}"
install -m 600 "${TEMP_PLIST}" "${STAGE_DIR}/com.pantheon.content-capacity-guard.plist"
echo "Pantheon content capacity watchdog plist 已寫入 private aggregate stage；尚未 activation。"
