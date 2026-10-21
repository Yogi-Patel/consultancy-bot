# 📘 Consultation Bot Setup (VM)

## 🧠 Overview

This VM runs a Python Playwright bot that:

* Logs into the consultation portal
* Continuously scans for available slots
* Books based on priority and constraints
* Runs automatically on boot
* Restarts automatically if it crashes

---

# ⚙️ Project Structure (IMPORTANT)

All files are in `/root`:

```
/root/
│
├── Final_bot.py        # Main bot script
├── run_bot.sh          # Runner script (auto-restart loop)
├── botenv/             # Python virtual environment
└── bot.service         # systemd service (in /etc/systemd/system/)
```

---

# 🧪 Environment Setup (Already Done)

## 1. Python + venv

* Python 3 installed
* Virtual environment created:

```
python3 -m venv botenv
```

---

## 2. Playwright

Installed inside venv:

```
pip install playwright
python -m playwright install chromium
```

---

## 3. Linux Dependencies (IMPORTANT)

Installed to support Chromium:

```
apt install -y \
libatk1.0-0t64 \
libatk-bridge2.0-0t64 \
libx11-xcb1 \
libxcb1 \
libxcomposite1 \
libxdamage1 \
libxfixes3 \
libxrandr2 \
libgbm1 \
libpango-1.0-0 \
libcairo2 \
libasound2t64 \
libnss3 \
libxshmfence1 \
libgtk-3-0
```

---

## 4. Swap Memory Setup (CRITICAL for Small VMs)

If your VM has **≤ 1GB RAM**, Chromium may crash without swap.

### Create swap:

```
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

### Make swap permanent:

```
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 5. Verify swap is active

```
free -h
```

You should see:

```
Swap: 2.0G
```

---

# 🚀 How the Bot Runs

## 🔁 Runner Script

`run_bot.sh`:

```
#!/bin/bash

cd /root

while true
do
    /root/botenv/bin/python -u /root/Final_bot.py
    echo "Bot crashed. Restarting in 5 seconds..."
    sleep 5
done
```

* Runs bot in loop
* Restarts on crash
* Uses `-u` for real-time logs

---

## ⚡ systemd Service

Location:

```
/etc/systemd/system/bot.service
```

Contents:

```
[Unit]
Description=Consultation Bot
After=network.target

[Service]
ExecStart=/root/run_bot.sh
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

---

# 🔄 Auto Start Setup (Already Done)

```
systemctl daemon-reload
systemctl enable bot
systemctl start bot
```

---

# 📊 How to Check Bot Status

## ✅ Check if bot is running

```
systemctl status bot
```

You want to see:

```
active (running)
```

---

## 🔁 Restart bot manually

```
systemctl restart bot
```

---

## ⛔ Stop bot

```
systemctl stop bot
```

---

# 📜 How to View Logs

## 🔴 Live logs (MOST IMPORTANT)

```
journalctl -u bot -f
```

This shows:

* Bot started
* Login
* CLICKING events
* Errors

---

## 📌 Last 50 log lines

```
journalctl -u bot -n 50
```

---

## 📅 Logs from today

```
journalctl -u bot --since today
```

---

## 🎯 Only booking attempts

```
journalctl -u bot -f | grep CLICKING
```

---

# 🧪 Manual Run (Debugging)

To run bot manually:

```
/root/botenv/bin/python -u /root/Final_bot.py
```

OR

```
/root/run_bot.sh
```

---

# 🧰 Troubleshooting

## ❌ Bot not running

```
systemctl status bot
```

Check for:

* `failed`
* `exit-code`

---

## ❌ No logs showing

Make sure:

* Python uses `-u`

Then run:

```
journalctl -u bot -n 50
```

---

## ❌ Playwright errors (Chromium crash)

Most likely cause: **low memory**

### Fix:

* Ensure swap is enabled (see section above)
* Restart bot:

```
systemctl restart bot
```

---

## ❌ Script not executing

Check:

```
chmod +x /root/run_bot.sh
```

---

## ❌ Time issues

Check system time:

```
timedatectl
```

Set timezone:

```
timedatectl set-timezone Asia/Kolkata
```

---

# 🔁 Reboot Behavior

After reboot:

* VM starts
* systemd starts bot
* bot runs automatically

Check after reboot:

```
systemctl status bot
```

---

# 🧠 Final Notes

* Bot is fully automated
* No manual intervention needed
* Logs are only accessible via `journalctl`
* Multiple VMs increase booking success
* Small VMs REQUIRE swap for stability

---

# 🚀 End of README
