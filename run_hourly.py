"""
run_hourly.py - keeps a long-running bot fresh by restarting it on a timer.

It launches a script (default: click_bot.py), lets it run for N minutes, then
stops it AND everything it started (the Playwright driver and Chromium), and
launches it again. click_bot.py itself is not modified.

Usage (run from the folder that contains the bot):
    python run_hourly.py                      # click_bot.py, restart every 60 min
    python run_hourly.py click_bot.py --minutes 45

Safety behaviour:
  * If the bot ticked a slot recently (it prints a line containing "CLICKING"),
    the restart waits until --grace seconds have passed since that tick, so a
    tick that is still being confirmed is not cut off. It never waits longer
    than --max-wait seconds.
  * If the bot crashes or exits by itself, it is started again after 5 s.
  * Ctrl+C stops the wrapper and the bot together.
"""
import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [runner] {msg}", flush=True)


def kill_tree(proc):
    """Stop the bot and every process it started."""
    try:
        if os.name == "nt":
            # /T = whole process tree, /F = force
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # The bot was started in its own process group, so signal the group.
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(proc.pid, signal.SIGKILL)  # catch any stragglers
            except ProcessLookupError:
                pass
    finally:
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            log("warning: bot process did not exit cleanly")


def pump_output(proc, state):
    """Echo the bot's output and remember when it last ticked a slot."""
    for line in proc.stdout:
        print(line, end="", flush=True)
        if "CLICKING" in line:
            state["last_click"] = time.time()


def run_once(script, run_seconds, grace, max_wait):
    state = {"last_click": 0.0}

    popen_kwargs = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    # "-u" = unbuffered, otherwise the bot's prints reach us in delayed chunks.
    proc = subprocess.Popen(
        [sys.executable, "-u", script],
        cwd=os.path.dirname(script),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
        **popen_kwargs,
    )
    threading.Thread(target=pump_output, args=(proc, state), daemon=True).start()

    started = time.time()
    log(f"started {os.path.basename(script)} (pid {proc.pid}); restart in {run_seconds / 60:g} min")

    try:
        while proc.poll() is None:
            time.sleep(1)
            if time.time() - started >= run_seconds:
                deadline = time.time() + max_wait
                while time.time() - state["last_click"] < grace and time.time() < deadline:
                    time.sleep(1)
                log("time is up, restarting the bot")
                break
        else:
            log(f"bot exited by itself (code {proc.returncode})")
    finally:
        kill_tree(proc)


def main():
    ap = argparse.ArgumentParser(description="Restart a bot script on a timer.")
    ap.add_argument("script", nargs="?", default="click_bot.py")
    ap.add_argument("--minutes", type=float, default=60, help="how long each run lasts")
    ap.add_argument("--grace", type=float, default=60, help="seconds to wait after a tick before restarting")
    ap.add_argument("--max-wait", type=float, default=300, help="longest the restart may be delayed")
    args = ap.parse_args()

    script = os.path.abspath(args.script)
    if not os.path.isfile(script):
        sys.exit(f"Cannot find {script}. Run this from the folder that contains the bot.")

    # Make a plain "kill" also stop the bot (Ctrl+C already does).
    def _stop(*_):
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGTERM, _stop)
    except (ValueError, OSError):
        pass

    try:
        while True:
            run_once(script, args.minutes * 60, args.grace, args.max_wait)
            time.sleep(5)
    except KeyboardInterrupt:
        log("stopped by user")


if __name__ == "__main__":
    main()
