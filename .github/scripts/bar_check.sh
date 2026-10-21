#!/usr/bin/env bash
# Lists the lines in a diff that lower a bar: a skip or xfail added, an assert
# or a test removed, a suppression comment added, a numeric constant in src/
# changed, a line removed from a guard list. A hit is not a violation -- a
# removal can be right -- it is a line the PR description should explain.
# Prints Markdown and always exits 0.
set -u
range="${1:?usage: bar_check.sh <base>...<head>}"

check() {
  local label="$1" pattern="$2"; shift 2
  local hits
  hits=$(git diff -U0 "$range" -- "$@" | grep -E "$pattern" | grep -vE '^(\+\+\+|---) ')
  if [ -n "$hits" ]; then
    echo "### $label ($(printf '%s\n' "$hits" | wc -l | tr -d ' '))"
    echo '```diff'
    printf '%s\n' "$hits"
    echo '```'
    found=1
  fi
}

found=0
echo "## Bar-lowering check"
check "skip / xfail added" '^\+.*(pytest\.skip|pytest\.mark\.skip|xfail|importorskip)' '*.py'
check "assert removed" '^-\s+assert ' '*.py'
check "test function removed" '^-\s*(async )?def test_' '*.py'
check "suppression comment added" '^\+.*# *(noqa|type: *ignore)' '*.py'
check "numeric constant changed (src/)" '^[-+]\s*[A-Z][A-Z0-9_]{2,}\s*(:\s*\w+\s*)?=\s*[0-9.]+' 'src/'
check "guard list line removed" '^-' tests/test_dod.py tests/test_no_label_leakage.py
if [ "$found" = 0 ]; then
  echo "No hits."
else
  echo
  echo "Each hit needs a reason in the PR description. This check does not fail the build."
fi
exit 0
