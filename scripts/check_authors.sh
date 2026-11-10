#!/bin/sh
# Only Ashish Kharche may author or commit here.
# Usage: check_authors.sh [rev-range]   (default: all history)
# With --me, checks the identity git will use for the next commit.
allowed="thekharche@gmail.com ashishkharche@users.noreply.github.com"
ok() { for a in $allowed; do [ "$1" = "$a" ] && return 0; done; return 1; }

if [ "$1" = "--me" ]; then
  email=$(git config user.email)
  ok "$email" && exit 0
  echo "Blocked: commits here must be by Ashish Kharche, not $email." >&2
  echo "Run: git config user.email thekharche@gmail.com" >&2
  exit 1
fi

range=${1:-HEAD}
bad=$(git log --format='%h %ae %ce' "$range" | while read -r h a c; do
  ok "$a" || { echo "$h author $a"; continue; }
  # GitHub's web merges are committed by noreply@github.com.
  [ "$c" = "noreply@github.com" ] || ok "$c" || echo "$h committer $c"
done)
[ -z "$bad" ] && exit 0
echo "Blocked: these commits are not by Ashish Kharche:" >&2
echo "$bad" >&2
exit 1
