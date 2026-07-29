#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ACTION="${1:---install}"
USER_NAME="$(id -un)"
USER_ID="$(id -u)"
USER_HOME_DIR="$(dscl . -read "/Users/${USER_NAME}" NFSHomeDirectory | awk '{print $2}')"
PYTHON_PATH="${PANTHEON_PYTHON_PATH:-${REPO_ROOT}/.venv/bin/python}"
QUEUE_ROOT="${PANTHEON_GEMINI_QUEUE_ROOT:-${REPO_ROOT}/.work/gemini-runner}"
STATE_ROOT="${REPO_ROOT}/.work/content-publisher"
MAX_RUNS="${PANTHEON_PUBLISH_MAX_RUNS:-3}"
LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin}"
LOG_DIR="${USER_HOME_DIR}/Library/Logs/Pantheon"
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.agy-content-publisher.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-content-publisher.plist.example"
TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-content-publisher.XXXXXX")"

cleanup() {
  rm -f "${TEMP_PLIST}"
}
trap cleanup EXIT

if [[ "${ACTION}" != "--install" && "${ACTION}" != "--preflight" ]]; then
  echo "用法：scripts/install_agy_content_publisher_launchd.sh [--preflight|--install]" >&2
  exit 2
fi
if [[ ! -x "${PYTHON_PATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
  exit 1
fi
if [[ ! -d "${QUEUE_ROOT}/runs" ]]; then
  echo "找不到 Gemini queue runs：${QUEUE_ROOT}/runs" >&2
  exit 1
fi
if ! [[ "${MAX_RUNS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "PANTHEON_PUBLISH_MAX_RUNS 必須是正整數" >&2
  exit 1
fi
if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]]; then
  echo "publisher actor worktree 不乾淨，拒絕部署" >&2
  exit 1
fi
RUNTIME_SHA="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
ORIGIN_MAIN_SHA="$(git -C "${REPO_ROOT}" rev-parse origin/main)"
if [[ "${RUNTIME_SHA}" != "${ORIGIN_MAIN_SHA}" ]]; then
  echo "publisher actor HEAD 與 origin/main 不一致，拒絕部署" >&2
  exit 1
fi

cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 ${PYTHON_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:4 ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:6 ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:8 ${STATE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:10 ${MAX_RUNS}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:14 ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:16 ${QUEUE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:18 ${STATE_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:20 ${RUNTIME_SHA}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${LOG_DIR}/agy-content-publisher.stdout.log" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${LOG_DIR}/agy-content-publisher.stderr.log" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null

run_preflight() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_PATH}" -m scripts.agy_content_publisher \
      --repo-root "${REPO_ROOT}" \
      --queue-root "${QUEUE_ROOT}" \
      --state-root "${STATE_ROOT}" \
      --max-runs "${MAX_RUNS}" \
      --include-rewrites \
      --push \
      --deployment-preflight \
      --expected-repo-root "${REPO_ROOT}" \
      --expected-queue-root "${QUEUE_ROOT}" \
      --expected-state-root "${STATE_ROOT}" \
      --expected-runtime-sha "${RUNTIME_SHA}" \
      --expected-push-mode push
  )
}

if [[ "${ACTION}" == "--preflight" ]]; then
  run_preflight
  exit 0
fi

run_preflight >/dev/null
mkdir -p "${LOG_DIR}" "${LAUNCH_AGENTS_DIR}" "${STATE_ROOT}"
launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
install -m 600 "${TEMP_PLIST}" "${TARGET_PLIST}"
launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}"

echo "Pantheon content publisher 已啟用。"
echo "狀態：launchctl print gui/${USER_ID}/com.pantheon.agy-content-publisher"
echo "停止：launchctl bootout gui/${USER_ID} ${TARGET_PLIST}"
