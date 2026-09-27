#!/bin/bash
# ConFlow 服务器端部署脚本（在服务器上执行，通过 GitHub Actions 或 SSH 调用）
# 步骤：拉取 main → 重启 v2html → 本地配置署名同步为 ConFlow 引擎
set -e
cd /www/wwwroot/V2HTML
# 服务器 git 较老（1.8），拉取需 .gitssh.sh 包装 deploy key
[ -f .gitssh.sh ] && export GIT_SSH=/www/wwwroot/V2HTML/.gitssh.sh
git fetch origin main
git reset --hard FETCH_HEAD
# 改名 ConFlow：output/ 不走 git，就地同步旧产物里的品牌残留（生成物，整词替换安全）
sed -i 's/V2HTML/ConFlow/g' output/*/slides.html 2>/dev/null || true
systemctl restart v2html
sleep 2
systemctl is-active v2html
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('/www/wwwroot/V2HTML/server-data/config.json')
# 服务器系统 Python 3.6：读写显式 utf-8，stdout 仅 ascii
c = json.loads(p.read_text(encoding='utf-8'))
a = c.get('push', {}).get('author')
if a == 'V2HTML 引擎':
    c['push']['author'] = 'ConFlow 引擎'
    p.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding='utf-8')
    print('config author updated')
else:
    print('config author:', a.encode('unicode_escape').decode())
PY
git log --oneline -1
echo REMOTE-DEPLOY-DONE
