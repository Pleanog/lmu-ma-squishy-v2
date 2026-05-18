on windows:
.\.venv\Scripts\Activate.ps1

on pie:
source venv/bin/activate


there is a deploy file that i need to finish!
i did everything incl. setp 3 but not more:

🧱 Goal architecture

You will have:

a GitHub repo (your code)
a systemd service running your app
a deploy script that:
pulls latest code
optionally installs deps
restarts service
1. Create a systemd service

On your Pi:

sudo nano /etc/systemd/system/lmu-app.service

Example (adjust paths!):

[Unit]
Description=LMU App Service
After=network.target

[Service]
Type=simple
User=lang
WorkingDirectory=/home/lang/lmu-ma-squishy-v2
ExecStart=/home/lang/lmu-ma-squishy-v2/.venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
Enable it:
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable lmu-app
sudo systemctl start lmu-app
Check logs:
journalctl -u lmu-app -f
2. Create a deploy script

Inside your repo:

nano deploy.sh

Paste:

#!/bin/bash

set -e

echo "🚀 Pulling latest code..."
git pull origin main

echo "📦 Activating venv..."
source .venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🔄 Restarting service..."
sudo systemctl restart lmu-app

echo "✅ Deploy complete"

Make it executable:

chmod +x deploy.sh
3. Allow sudo restart WITHOUT password (important)

Otherwise your script will stop.

sudo visudo

Add at bottom:

lang ALL=NOPASSWD: /bin/systemctl restart lmu-app
4. Run deploy manually

Now test:

./deploy.sh

If everything works → you are done.

5. (Optional but VERY nice) Git hook auto-deploy

Instead of manually running script:

On Pi:
cd ~/lmu-ma-squishy-v2/.git/hooks
nano post-receive

BUT better approach (simpler & safer):

👉 we use “pull + restart manually OR via alias”

6. Best practical version (what I recommend)

Instead of full automation, use:

git pull && ./deploy.sh

or alias:

alias deploy="git pull && ./deploy.sh"
7. Even better (clean dev workflow)

You’ll end up with:

On laptop:
git push
On Pi:
ssh lang@pi
deploy

That’s it.

8. Common improvement (important for your Gemini/WebSocket app)

If your app uses live connections:

In systemd:

Restart=always
RestartSec=2

This ensures:

WebSocket crashes → auto recover
API hiccups → restart cleanly
9. Optional upgrade: zero-downtime deploy (later)

When you scale:

use git fetch + reset
or Docker
or pm2-like manager

But NOT needed now.

🔥 Recommended final setup (simple + solid)

You will have:

systemd service (always running)
git repo
venv
deploy.sh
one command deploy