"""Start/reuse the local Cloudflare development tunnel; write ignored runtime config.

A Quick Tunnel has no stable hostname or uptime guarantee. If restarted, update
MAINTENANCE_BACKEND_ORIGIN in both Vercel projects and redeploy them.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
RUNTIME.mkdir(exist_ok=True)
pidfile = RUNTIME / 'cloudflared.pid'
logfile = RUNTIME / 'cloudflared.log'
active = False
if pidfile.exists():
    try:
        pid = int(pidfile.read_text().strip())
        # Verify this PID still belongs to cloudflared before treating it as ours.
        name = subprocess.check_output(['ps', '-p', str(pid), '-o', 'comm='], text=True).strip()
        active = Path(name).name == 'cloudflared'
    except (ValueError, ProcessLookupError, subprocess.CalledProcessError):
        pass
if not active:
    binary = shutil.which('cloudflared')
    if not binary:
        raise SystemExit('Install cloudflared first: brew install cloudflared')
    with logfile.open('wb') as log:
        process = subprocess.Popen([binary,'tunnel','--url','http://127.0.0.1:8000','--protocol','http2','--no-autoupdate'],
                                   stdout=log, stderr=log, start_new_session=True)
    pidfile.write_text(str(process.pid)+'\n')
for _ in range(45):
    matches = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com',logfile.read_text() if logfile.exists() else '')
    if matches:
        config = ROOT / '.env.vercel-local'
        config.write_text('MAINTENANCE_BACKEND_ORIGIN='+matches[-1]+'\n'
                          'ADDITIONAL_APP_ORIGINS=["https://maintenance-copilot-dun.vercel.app",'
                          '"https://nexaiimplimentation-pylrns-projects.vercel.app","https://nexaiimplimentation.vercel.app"]\n')
        config.chmod(0o600)
        print(matches[-1])
        print('Runtime configuration written to .env.vercel-local; do not commit it.')
        break
    time.sleep(1)
else:
    raise SystemExit('Tunnel did not publish a hostname; inspect .runtime/cloudflared.log')
