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
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.content-capacity-guard.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.content-capacity-guard.plist.example"
TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-content-capacity-guard.XXXXXX")"

cleanup() {
  local RETURN_CODE="$?"
  rm -f "${TEMP_PLIST}"
  return "${RETURN_CODE}"
}
trap cleanup EXIT

if [[ "${ACTION}" != "--install" && "${ACTION}" != "--preflight" ]]; then
  echo "用法：scripts/install_pantheon_content_capacity_guard_launchd.sh [--preflight|--install]" >&2
  exit 2
fi
if [[ ! -x "${PYTHON_PATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
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
PUBLISHER_ROOT="$(manifest_field publisher_state_root)"
LOG_ROOT="$(manifest_field log_root)"
RUNTIME_MANIFEST_DIGEST="$(manifest_field manifest_digest)"
RUNTIME_IDENTITY="$(manifest_field identity)"
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

if [[ "${ACTION}" == "--install" ]]; then
  mkdir -p "${QUEUE_ROOT}" "${PUBLISHER_ROOT}" "${LOG_ROOT}" "${LAUNCH_AGENTS_DIR}"
fi
(
  cd "${REPO_ROOT}"
  "${PYTHON_PATH}" -m scripts.pantheon_content_capacity_guard \
    --queue-root "${QUEUE_ROOT}" \
    --publisher-root "${PUBLISHER_ROOT}" \
    --log-root "${LOG_ROOT}" \
    --state-file "${STATE_FILE}" \
    preflight
)

cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:4 ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:6 ${PUBLISHER_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:8 ${LOG_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:10 ${STATE_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST_DIGEST ${RUNTIME_MANIFEST_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY ${RUNTIME_IDENTITY}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_ROOT}/pantheon-content-capacity-guard.stdout.log" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_ROOT}/pantheon-content-capacity-guard.stderr.log" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null

if [[ "${ACTION}" == "--preflight" ]]; then
  exit 0
fi

launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
install -m 600 "${TEMP_PLIST}" "${TARGET_PLIST}"
launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}"
echo "Pantheon content capacity watchdog 已啟用。"
