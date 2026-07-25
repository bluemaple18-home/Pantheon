#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ACTION="${1:-install}"
USER_ID="$(id -u)"
USER_HOME_DIR="$(cd && pwd)"
LABEL="com.pantheon.agy-gemini-v4-shadow"
PYTHON_PATH="${PANTHEON_PYTHON_PATH:-${REPO_ROOT}/.venv/bin/python}"
CREDENTIAL_POOL_FILE="${PANTHEON_GEMINI_V4_CREDENTIAL_POOL_FILE:-${USER_HOME_DIR}/.config/pantheon/gemini-api-pool.json}"
STRUCTURED_TARGET="${REPO_ROOT}/scripts/agy_gemini_v4_structured_target.py"
STATE_ROOT="${PANTHEON_GEMINI_V4_SHADOW_STATE_ROOT:-${USER_HOME_DIR}/Library/Application Support/Pantheon/gemini-v4-shadow}"
LOG_DIR="${USER_HOME_DIR}/Library/Logs/Pantheon"
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/${LABEL}.plist.example"

case "${ACTION}" in
  status)
    launchctl print "gui/${USER_ID}/${LABEL}"
    exit 0
    ;;
  stop)
    launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}"
    echo "Pantheon Gemini V4 shadow 已停止；plist與state保留。"
    exit 0
    ;;
  uninstall)
    launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
    rm -f "${TARGET_PLIST}"
    echo "Pantheon Gemini V4 shadow 已移除；state與log保留。"
    exit 0
    ;;
  install|check)
    ;;
  *)
    echo "用法：$0 [check|install|status|stop|uninstall]" >&2
    exit 2
    ;;
esac

if [[ ! -x "${PYTHON_PATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
  exit 1
fi
if [[ ! -x "${STRUCTURED_TARGET}" ]]; then
  echo "找不到 Gemini V4 structured target：${STRUCTURED_TARGET}" >&2
  exit 1
fi
if [[ -L "${CREDENTIAL_POOL_FILE}" || ! -f "${CREDENTIAL_POOL_FILE}" ]]; then
  echo "credential pool必須是regular non-symlink file。" >&2
  exit 1
fi
if [[ "$(stat -f '%Lp' "${CREDENTIAL_POOL_FILE}")" != "600" ]]; then
  echo "credential pool權限必須是0600。" >&2
  exit 1
fi

TARGET_SHA256="$(shasum -a 256 "${STRUCTURED_TARGET}" | awk '{print $1}')"
TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-gemini-v4-shadow.XXXXXX")"
cleanup() {
  rm -f "${TEMP_PLIST}"
}
trap cleanup EXIT

cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:4 ${STATE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_V4_CREDENTIAL_POOL_FILE ${CREDENTIAL_POOL_FILE}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_V4_EXECUTABLE ${STRUCTURED_TARGET}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_V4_EXECUTABLE_SHA256 ${TARGET_SHA256}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/agy-gemini-v4-shadow.stdout.log" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/agy-gemini-v4-shadow.stderr.log" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null

if [[ "${ACTION}" == "check" ]]; then
  echo "Pantheon Gemini V4 shadow install check：PASS"
  echo "cadence=21600 state_root=${STATE_ROOT}"
  exit 0
fi

mkdir -p "${STATE_ROOT}" "${LOG_DIR}" "${LAUNCH_AGENTS_DIR}"
chmod 700 "${STATE_ROOT}"
launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
install -m 600 "${TEMP_PLIST}" "${TARGET_PLIST}"
launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}"

echo "Pantheon Gemini V4 shadow 已啟用：每6小時最多一筆、每日最多4筆。"
echo "狀態：bash ${REPO_ROOT}/scripts/install_agy_gemini_v4_shadow_launchd.sh status"
echo "停止：bash ${REPO_ROOT}/scripts/install_agy_gemini_v4_shadow_launchd.sh stop"
