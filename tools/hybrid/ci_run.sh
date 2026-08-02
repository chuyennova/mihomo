#!/usr/bin/env bash
set -uo pipefail
step="${1:?step name required}"
shift
mkdir -p .ci-status dist logs
start="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
{
  echo
  echo "===== STEP: ${step} ====="
  echo "start=${start}"
  printf 'command='; printf '%q ' "$@"; echo
} | tee -a full-build.log
set +e
"$@" 2>&1 | tee -a full-build.log
rc=${PIPESTATUS[0]}
set -e
end="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
{
  echo "end=${end}"
  echo "exit_code=${rc}"
  echo "===== END STEP: ${step} ====="
} | tee -a full-build.log
printf '%s\n' "$rc" > ".ci-status/${step}.exit"
exit "$rc"
