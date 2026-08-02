#!/usr/bin/env bash
# Fail the job only after tests, compile, packaging and complete log upload have
# all had a chance to run. ci_run.sh records the original exit code per step.
set -uo pipefail

required=(prepare source-tree go-environment install-tools source-verify vendor apply-patch gofmt verify tests compile wintun package)
failed=0
for step in "${required[@]}"; do
  file=".ci-status/${step}.exit"
  if [[ ! -f "$file" ]]; then
    echo "FINAL GATE: ${step}=MISSING"
    failed=1
    continue
  fi
  rc="$(cat "$file" 2>/dev/null || echo unknown)"
  if [[ "$rc" != "0" ]]; then
    echo "FINAL GATE: ${step}=FAILED(${rc})"
    failed=1
  else
    echo "FINAL GATE: ${step}=OK"
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "FINAL GATE: build is not releasable; inspect uploaded diagnostics."
  exit 1
fi

echo "FINAL GATE: all mandatory steps passed."
exit 0
