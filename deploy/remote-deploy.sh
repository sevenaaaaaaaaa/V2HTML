#!/bin/bash
# ConFlow 服务器端部署脚本（在服务器上执行，通过 GitHub Actions 或 SSH 调用）
# 步骤：拉取 main → 重启 v2html → 本地配置署名同步为 ConFlow 引擎
set -e
cd /www/wwwroot/V2HTML
# 服务器 git 较老（1.8），拉取需 .gitssh.sh 包装 deploy key
[ -f .gitssh.sh ] && export GIT_SSH=/www/wwwroot/V2HTML/.gitssh.sh
git fetch origin main
git reset --hard FETCH_HEAD
systemctl restart v2html
sleep 2
systemctl is-active v2html
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('/www/wwwroot/V2HTML/server-data/config.json')
c = json.loads(p.read_text())
if c.get('push', {}).get('author') == 'V2HTML 引擎':
    c['push']['author'] = 'ConFlow 引擎'
    p.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    print('config author -> ConFlow 引擎')
else:
    print('config author:', c.get('push', {}).get('author'))
PY
git log --oneline -1
echo REMOTE-DEPLOY-DONE
