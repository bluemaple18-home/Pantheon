#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "用法：$0 <reviewer-model>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REVIEWER_MODEL="$1"
USER_NAME="$(id -un)"
USER_ID="$(id -u)"
USER_HOME_DIR="$(dscl . -read "/Users/${USER_NAME}" NFSHomeDirectory | awk '{print $2}')"
PYTHON_PATH="${PANTHEON_PYTHON_PATH:-${REPO_ROOT}/.venv/bin/python}"
LABEL="com.pantheon.agy-gemini-coordinator"
TARGET_PLIST="${USER_HOME_DIR}/Library/LaunchAgents/${LABEL}.plist"
STAGED_PLIST=""
ORIGINAL_PLIST=""

cleanup() {
  if [[ -n "${STAGED_PLIST}" ]]; then
    rm -f "${STAGED_PLIST}"
  fi
  if [[ -n "${ORIGINAL_PLIST}" ]]; then
    rm -f "${ORIGINAL_PLIST}"
  fi
}
trap cleanup EXIT

if [[ ! -x "${PYTHON_PATH}" ]]; then
  echo "找不到 Pantheon Python：${PYTHON_PATH}" >&2
  exit 1
fi
if [[ ! "${REVIEWER_MODEL}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "reviewer model 只能使用 model identifier 安全字元。" >&2
  exit 1
fi
if [[ ! -f "${TARGET_PLIST}" || -L "${TARGET_PLIST}" ]]; then
  echo "找不到可信任的 coordinator plist：${TARGET_PLIST}" >&2
  exit 1
fi

STAGED_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-reviewer-cutover.XXXXXX")"
ORIGINAL_PLIST="$(mktemp "${TMPDIR:-/tmp}/pantheon-reviewer-original.XXXXXX")"
cp "${TARGET_PLIST}" "${ORIGINAL_PLIST}"
ORIGINAL_SHA256="$(shasum -a 256 "${ORIGINAL_PLIST}" | awk '{print $1}')"

SUMMARY="$(
  cd "${REPO_ROOT}"
  "${PYTHON_PATH}" -m scripts.agy_gemini_reviewer_cutover \
    --source "${ORIGINAL_PLIST}" \
    --output "${STAGED_PLIST}" \
    --reviewer-model "${REVIEWER_MODEL}"
)"
plutil -lint "${STAGED_PLIST}" >/dev/null

CURRENT_SHA256="$(shasum -a 256 "${TARGET_PLIST}" | awk '{print $1}')"
if [[ "${CURRENT_SHA256}" != "${ORIGINAL_SHA256}" ]]; then
  echo "coordinator plist 在 cutover preflight 期間已改變；未執行切換。" >&2
  exit 1
fi

WAS_LOADED=0
if launchctl print "gui/${USER_ID}/${LABEL}" >/dev/null 2>&1; then
  WAS_LOADED=1
fi

restore_original() {
  if [[ "${WAS_LOADED}" -eq 1 ]]; then
    launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
  fi
  /usr/bin/install -m 600 "${ORIGINAL_PLIST}" "${TARGET_PLIST}" || return 1
  if [[ "${WAS_LOADED}" -eq 1 ]]; then
    launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}" || return 1
  fi
}

if [[ "${WAS_LOADED}" -eq 1 ]]; then
  if ! launchctl bootout "gui/${USER_ID}" "${TARGET_PLIST}"; then
    echo "無法停止 coordinator；未修改 plist。" >&2
    exit 1
  fi
fi

CURRENT_SHA256="$(shasum -a 256 "${TARGET_PLIST}" | awk '{print $1}')"
if [[ "${CURRENT_SHA256}" != "${ORIGINAL_SHA256}" ]]; then
  if [[ "${WAS_LOADED}" -eq 1 ]]; then
    launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
  fi
  echo "coordinator plist 在控制切換期間已改變；未覆寫檔案。" >&2
  exit 1
fi

if ! /usr/bin/install -m 600 "${STAGED_PLIST}" "${TARGET_PLIST}"; then
  restore_original >/dev/null 2>&1 || true
  echo "無法安裝 reviewer cutover plist；已嘗試還原。" >&2
  exit 1
fi

if [[ "${WAS_LOADED}" -eq 1 ]] && ! launchctl bootstrap "gui/${USER_ID}" "${TARGET_PLIST}"; then
  if ! restore_original; then
    echo "reviewer cutover 啟動失敗，且自動還原未完整成功。" >&2
    exit 1
  fi
  echo "reviewer cutover 啟動失敗；已還原原 coordinator plist。" >&2
  exit 1
fi

printf '%s\n' "${SUMMARY}"
if [[ "${WAS_LOADED}" -eq 1 ]]; then
  echo "coordinator 已以新 reviewer model 重新載入；四條 lane 未變更。"
else
  echo "coordinator plist 已更新但維持未載入；四條 lane 未變更。"
fi
