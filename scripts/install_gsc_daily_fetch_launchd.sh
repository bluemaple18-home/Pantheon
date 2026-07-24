#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
USER_NAME="$(id -un)"
USER_ID="$(id -u)"
USER_HOME_DIR="$(dscl . -read "/Users/${USER_NAME}" NFSHomeDirectory | awk '{print $2}')"
PYTHON_PATH="${REPO_ROOT}/.venv/bin/python"
CONFIG_DIR="${USER_HOME_DIR}/.config/pantheon-gsc"
LOG_DIR="${USER_HOME_DIR}/Library/Logs/Pantheon"
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.gsc-daily-fetch.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.gsc-daily-fetch.plist.example"
TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-gsc-daily-fetch.XXXXXX")"

cleanup() {
  rm -f "${TEMP_PLIST}"
}
trap cleanup EXIT

if [[ ! -x "${PYTHON_PATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
  exit 1
fi
if [[ ! -r "${CONFIG_DIR}/client.json" || ! -r "${CONFIG_DIR}/token.json" ]]; then
  echo "找不到 GSC credential：${CONFIG_DIR}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}" "${LAUNCH_AGENTS_DIR}"
cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/gsc-daily-fetch.stdout.log" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/gsc-daily-fetch.stderr.log" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null

launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
install -m 600 "${TEMP_PLIST}" "${TARGET_PLIST}"
launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}"

echo "Pantheon GSC 每日抓取已啟用。"
echo "狀態：launchctl print gui/${USER_ID}/com.pantheon.gsc-daily-fetch"
echo "停止：launchctl bootout gui/${USER_ID} ${TARGET_PLIST}"
