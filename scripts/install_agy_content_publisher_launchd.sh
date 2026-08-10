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
MAX_RUNS="${PANTHEON_PUBLISH_MAX_RUNS:-3}"
NEW_ONLY="${PANTHEON_PUBLISH_NEW_ONLY:-0}"
LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin}"
LAUNCH_AGENTS_DIR="${USER_HOME_DIR}/Library/LaunchAgents"
TARGET_PLIST="${LAUNCH_AGENTS_DIR}/com.pantheon.agy-content-publisher.plist"
TEMPLATE_PLIST="${REPO_ROOT}/ops/launchd/com.pantheon.agy-content-publisher.plist.example"
RUNTIME_MANIFEST_FILE="${PANTHEON_RUNTIME_MANIFEST_FILE:-${REPO_ROOT}/.work/pantheon-content-runtime-manifest.json}"
TEMP_PLIST=""

cleanup() {
  local RETURN_CODE="$?"
  if [[ -n "${TEMP_PLIST}" ]]; then
    rm -f "${TEMP_PLIST}"
  fi
  return "${RETURN_CODE}"
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
if ! [[ "${MAX_RUNS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "PANTHEON_PUBLISH_MAX_RUNS 必須是正整數" >&2
  exit 1
fi
if [[ "${NEW_ONLY}" != "0" && "${NEW_ONLY}" != "1" ]]; then
  echo "PANTHEON_PUBLISH_NEW_ONLY 只能是 0 或 1" >&2
  exit 1
fi
if [[ "${NEW_ONLY}" == "1" ]]; then
  echo "四軌 recovery 禁止 new-only；請改用獨立 maintenance 入口。" >&2
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
STATE_ROOT="$(manifest_field publisher_state_root)"
LOG_DIR="$(manifest_field log_root)"
RUNTIME_MANIFEST_DIGEST="$(manifest_field manifest_digest)"
RUNTIME_IDENTITY="$(manifest_field identity)"
if [[ ! -d "${QUEUE_ROOT}/runs" ]]; then
  echo "找不到 Gemini queue runs：${QUEUE_ROOT}/runs" >&2
  exit 1
fi
if [[ "${ACTOR_ROOT}" != "${REPO_ROOT}" ]]; then
  echo "runtime manifest actor root 與 installer actor 不一致。" >&2
  exit 1
fi
for LEGACY_QUEUE_ROOT in "${PANTHEON_GEMINI_QUEUE_ROOT:-}" "${AGY_GEMINI_QUEUE_ROOT:-}"; do
  if [[ -n "${LEGACY_QUEUE_ROOT}" && "${LEGACY_QUEUE_ROOT}" != "${QUEUE_ROOT}" ]]; then
    echo "runtime manifest queue root 與 legacy override 不一致。" >&2
    exit 1
  fi
done
if [[ -n "${PANTHEON_CONTENT_PUBLISHER_ROOT:-}" \
  && "${PANTHEON_CONTENT_PUBLISHER_ROOT}" != "${STATE_ROOT}" ]]; then
  echo "runtime manifest publisher state root 與 legacy override 不一致。" >&2
  exit 1
fi
STDOUT_LOG="${LOG_DIR}/agy-content-publisher.stdout.log"
STDERR_LOG="${LOG_DIR}/agy-content-publisher.stderr.log"
PUBLISH_MODE="--include-rewrites"
TEMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-content-publisher.XXXXXX")"
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
RUNTIME_DIGEST="$(
  cd "${REPO_ROOT}"
  "${PYTHON_PATH}" -c \
    'from pathlib import Path; from scripts.agy_content_publisher import runtime_manifest_digest; print(runtime_manifest_digest(Path.cwd()))'
)"

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
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:22 ${RUNTIME_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory ${REPO_ROOT}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_PUBLISHER_STDOUT_LOG ${STDOUT_LOG}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_PUBLISHER_STDERR_LOG ${STDERR_LOG}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_MANIFEST_DIGEST ${RUNTIME_MANIFEST_DIGEST}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PANTHEON_RUNTIME_IDENTITY ${RUNTIME_IDENTITY}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardOutPath ${STDOUT_LOG}" "${TEMP_PLIST}"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath ${STDERR_LOG}" "${TEMP_PLIST}"
plutil -lint "${TEMP_PLIST}" >/dev/null

run_preflight() {
  (
    cd "${REPO_ROOT}"
    "${PYTHON_PATH}" -m scripts.agy_content_publisher \
      --repo-root "${REPO_ROOT}" \
      --queue-root "${QUEUE_ROOT}" \
      --state-root "${STATE_ROOT}" \
      --max-runs "${MAX_RUNS}" \
      "${PUBLISH_MODE}" \
      --push \
      --deployment-preflight \
      --expected-repo-root "${REPO_ROOT}" \
      --expected-queue-root "${QUEUE_ROOT}" \
      --expected-state-root "${STATE_ROOT}" \
      --expected-runtime-sha "${RUNTIME_SHA}" \
      --expected-runtime-digest "${RUNTIME_DIGEST}" \
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
