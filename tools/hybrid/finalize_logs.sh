#!/usr/bin/env bash
set -uo pipefail
mkdir -p logs dist .ci-status
status_of() {
  local f=".ci-status/$1.exit"
  if [[ -f "$f" ]]; then
    local rc; rc="$(cat "$f")"
    [[ "$rc" == "0" ]] && echo OK || echo "FAILED(${rc})"
  else
    echo SKIPPED
  fi
}
{
  echo "Mihomo hybrid build summary"
  echo "upstream_tag=${UPSTREAM_TAG:-v1.19.29}"
  echo "patch_revision=${PATCH_REVISION:-hybrid-4profiles-v1}"
  echo "commit_sha=${GITHUB_SHA:-unknown}"
  echo "build_date_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "workflow_run_id=${GITHUB_RUN_ID:-unknown}"
  echo "workflow_run_url=${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-unknown}/actions/runs/${GITHUB_RUN_ID:-unknown}"
  echo "runner_os=${RUNNER_OS:-unknown}"
  echo "go_version=$(go version 2>/dev/null || echo unavailable)"
  echo "GOOS=windows"
  echo "GOARCH=amd64"
  echo "GOAMD64=v2"
  [[ -f go.mod ]] && echo "go_mod_sha256=$(sha256sum go.mod | awk '{print $1}')"
  [[ -f go.sum ]] && echo "go_sum_sha256=$(sha256sum go.sum | awk '{print $1}')"
  grep -E 'github.com/metacubex/(sing-wireguard|gvisor|wireguard-go)' go.mod 2>/dev/null || true
  echo
  for step in source-verify vendor apply-patch gofmt verify tests compile wintun package; do
    echo "${step}=$(status_of "$step")"
  done
  echo
  if [[ -f dist/verge-mihomo.exe ]]; then
    echo "binary_sha256=$(sha256sum dist/verge-mihomo.exe | awk '{print $1}')"
  fi
  if [[ -f dist/wintun.dll ]]; then
    echo "wintun_sha256=$(sha256sum dist/wintun.dll | awk '{print $1}')"
  fi
} > summary.txt
cp -f summary.txt logs/summary.txt
[[ -f full-build.log ]] && cp -f full-build.log logs/full-build.log || : > logs/full-build.log
cp -f tools/hybrid/SOURCE_LOCKS.md logs/SOURCE_LOCKS.md 2>/dev/null || true
cp -f tools/hybrid/MANIFEST-SHA256.txt logs/MANIFEST-SHA256.txt 2>/dev/null || true
(cd logs && zip -9 -r ../dist/hybrid-build-logs.zip . >/dev/null)
