#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
sub="$root/external/pddl-to-htn"
patch="$root/external/patches/pddl-to-htn.patch"

if git -C "$sub" apply --check "$patch" 2>/dev/null; then
    git -C "$sub" apply "$patch"
fi

cp -rn "$root/external/patches/pddl-to-htn-fullhabitat" "$sub/htn/domains/fullhabitat"

g++ -O2 -o "$sub/htn/bin/create_htn" "$sub/htn/bin/create_htn.cpp"
