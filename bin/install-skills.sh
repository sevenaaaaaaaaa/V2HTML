#!/usr/bin/env bash
# 把 skills/ 同步安装到 ~/.agents/skills/（ZCode 用户技能目录），之后 /v2html /v2video 全局可用
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)/skills"
DST="$HOME/.agents/skills"
mkdir -p "$DST"
for d in "$SRC"/*/; do
  name="$(basename "$d")"
  rm -rf "$DST/$name"
  cp -R "$d" "$DST/$name"
  echo "installed: ~/.agents/skills/$name"
done
echo "done. 重启 ZCode 会话后 /v2html /v2video 生效。"
