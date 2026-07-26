#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
USER_NAME="$(id -un)"
USER_ID="$(id -u)"
USER_HOME_DIR="$(dscl . -read "/Users/${USER_NAME}" NFSHomeDirectory | awk '{print $2}')"
PYTHON_PATH="${PANTHEON_PYTHON_PATH:-${REPO_ROOT}/.venv/bin/python}"
AGY_CLI_PATH="${AGY_GEMINI_CLI_PATH:-${USER_HOME_DIR}/.antigravity/bin/agy-1.1.3}"
PRODUCTION_POOL_FILE="${AGY_GEMINI_CREDENTIAL_POOL_FILE:-}"
QUEUE_ROOT="${AGY_GEMINI_QUEUE_ROOT:-${REPO_ROOT}/.work/gemini-runner}"
LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin}"
LOG_DIR="${USER_HOME_DIR}/Library/Logs/Pantheon"
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-coordinator.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example"
LANE_TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-gemini-lane.plist.example"
TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-gemini-coordinator.XXXXXX")"

cleanup() {
  rm -f "${TEMP_PLIST}"
}
trap cleanup EXIT

if [[ ! -x "${PYTHON_PATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
  exit 1
fi
if [[ ! -x "${AGY_CLI_PATH}" ]]; then
  echo "找不到 Gemini CLI：${AGY_CLI_PATH}" >&2
  exit 1
fi
if [[ -n "${PRODUCTION_POOL_FILE}" ]]; then
  if [[ ! -f "${PRODUCTION_POOL_FILE}" || -L "${PRODUCTION_POOL_FILE}" ]]; then
    echo "Production Gemini credential pool 必須是 regular non-symlink file。" >&2
    exit 1
  fi
  POOL_OWNER="$(stat -f '%u' "${PRODUCTION_POOL_FILE}")"
  POOL_MODE="$(stat -f '%Lp' "${PRODUCTION_POOL_FILE}")"
  if [[ "${POOL_OWNER}" != "${USER_ID}" || $((8#${POOL_MODE} & 8#077)) -ne 0 ]]; then
    echo "Production Gemini credential pool 必須由目前使用者擁有且不得開放 group/other 權限。" >&2
    exit 1
  fi
fi
if launchctl print "gui/${USER_ID}/com.pantheon.agy-gemini-runner" >/dev/null 2>&1; then
  echo "偵測到舊版 standalone runner；請先停止 com.pantheon.agy-gemini-runner，避免兩個服務競爭 queue。" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}" "${LAUNCH_AGENTS_DIR}"
cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:4 ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:6 ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:8 ${REPO_ROOT}/.work/gsc-copy" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:11 ${REPO_ROOT}/.work/content-publisher" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:13 ${REPO_ROOT}/.work/gsc-copy" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_CLI ${AGY_CLI_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/agy-gemini-coordinator.stdout.log" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/agy-gemini-coordinator.stderr.log" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null

launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
install -m 600 "${TEMP_PLIST}" "${TARGET_PLIST}"
launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}"

for LANE in new rewrite i18n-new i18n-rewrite; do
  LANE_LABEL="com.pantheon.agy-gemini-${LANE}"
  LANE_TARGET_PLIST="${LAUNCH_AGENTS_DIR}/${LANE_LABEL}.plist"
  LANE_TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-gemini-${LANE}.XXXXXX")"
  cp "${LANE_TEMPLATE_PLIST}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :Label ${LANE_LABEL}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :ProgramArguments:4 ${QUEUE_ROOT}/lanes/${LANE}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:AGY_GEMINI_CLI ${AGY_CLI_PATH}" "${LANE_TEMP_PLIST}"
  if [[ -n "${PRODUCTION_POOL_FILE}" ]]; then
    /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_FILE string ${PRODUCTION_POOL_FILE}" "${LANE_TEMP_PLIST}"
  fi
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/agy-gemini-${LANE}.stdout.log" "${LANE_TEMP_PLIST}"
  /usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/agy-gemini-${LANE}.stderr.log" "${LANE_TEMP_PLIST}"
  plutil -lint "${LANE_TEMP_PLIST}" >/dev/null
  launchctl bootout "gui/${USER_ID}" "${LANE_TARGET_PLIST}" >/dev/null 2>&1 || true
  install -m 600 "${LANE_TEMP_PLIST}" "${LANE_TARGET_PLIST}"
  rm -f "${LANE_TEMP_PLIST}"
  launchctl bootstrap "gui/${USER_ID}" "${LANE_TARGET_PLIST}"
done

echo "Pantheon Gemini coordinator 已啟用。"
echo "四條 lane runner 已啟用：new、rewrite、i18n-new、i18n-rewrite。"
echo "Queue root：${QUEUE_ROOT}"
echo "狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-coordinator"
echo "停止：launchctl bootout gui/${USER_ID} ${TARGET_PLIST}"
echo "Lane 狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}"
echo "Lane plist：${LAUNCH_AGENTS_DIR}/com.pantheon.agy-gemini-{new,rewrite,i18n-new,i18n-rewrite}.plist"
