"""
run_hourly.py - keeps a long-running bot fresh by restarting it on a timer.

It launches a script (default: click_bot.py), lets it run for N minutes, then
stops it AND everything it started (the Playwright driver and Chromium), and
launches it again. click_bot.py itself is not modified.

Usage (run from the folder that contains the bot):
    python run_hourly.py                      # click_bot.py, restart every 60 min
    python run_hourly.py click_bot.py --minutes 45

Live status line (last line of the console, updates every second):
    14:10:42 | last scan 1 s ago | 1,234 scans | 480 MB | restart in 17 min
  The clock proves the wrapper is alive; "last scan N s ago" proves the bot is:
  if the bot hangs, N keeps growing. The scan count comes from the *_lowmem2
  bots (older bots just show "running"). Memory needs psutil. When the output
  is not a console (for example redirected to a file) no status line is drawn.

Safety behaviour:
  * Memory limit: if the bot plus everything it started (Playwright driver and
    Chromium) uses more than --max-mb (default 1500), the bot is restarted. This
    needs the psutil package (pip install psutil); without it the limit is off
    and a warning is printed. Use --max-mb 0 to switch the limit off.
  * If the bot ticked a slot recently (it prints a line containing "CLICKING"),
    the restart waits until --grace seconds have passed since that tick, so a
    tick that is still being confirmed is not cut off. It never waits longer
    than --max-wait seconds.
  * If the bot crashes or exits by itself, it is started again after 5 s.
  * Ctrl+C stops the wrapper and the bot together.
"""
import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

# ---- console output with a live status line at the bottom -------------------
_out_lock = threading.Lock()
_status_line = ""            # text currently drawn on the last line ("" = none)
_IS_TTY = sys.stdout.isatty()

if _IS_TTY and os.name == "nt":
    os.system("")            # switches on escape-code support in older Windows consoles


def emit(text):
    """Print a line; the live status line is cleared first and redrawn below it."""
    with _out_lock:
        if _IS_TTY and _status_line:
            sys.stdout.write("\r\x1b[K")
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
        if _IS_TTY and _status_line:
            sys.stdout.write(_status_line)
        sys.stdout.flush()


def draw_status(text):
    global _status_line
    if not _IS_TTY:
        return
    width = shutil.get_terminal_size((80, 20)).columns - 1
    with _out_lock:
        _status_line = text[:width]
        sys.stdout.write("\r\x1b[K" + _status_line)
        sys.stdout.flush()


def clear_status():
    global _status_line
    with _out_lock:
        if _IS_TTY and _status_line:
            sys.stdout.write("\r\x1b[K")
            sys.stdout.flush()
        _status_line = ""


def log(msg):
    emit(f"[{datetime.now().strftime('%H:%M:%S')}] [runner] {msg}")


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


def tree_mb(proc):
    """Memory in MB used by the bot and all its child processes, or None if unknown."""
    try:
        import psutil
    except ImportError:
        return None
    try:
        parent = psutil.Process(proc.pid)
        total = 0
        for p in [parent] + parent.children(recursive=True):
            try:
                total += p.memory_info().rss
            except psutil.Error:
                pass
        return total / (1024 * 1024)
    except psutil.Error:
        return None


STATUS_RE = re.compile(r"^\x01STATUS scans=(\d+) last=(\S+)")


def pump_output(proc, state):
    """Echo the bot's output, note scan reports, and remember when it last ticked a slot."""
    for line in proc.stdout:
        m = STATUS_RE.match(line)
        if m:                                   # a scan report: used for the status line, not printed
            state["scans"] = int(m.group(1))
            state["last_scan"] = time.time()    # when the wrapper heard it
            continue
        emit(line)
        if "CLICKING" in line:
            state["last_click"] = time.time()


def status_text(state, started, run_seconds, mem):
    now = time.time()
    parts = [datetime.now().strftime("%H:%M:%S")]
    if state.get("scans"):
        parts.append(f"last scan {int(now - state['last_scan'])} s ago")
        parts.append(f"{state['scans']:,} scans")
    else:
        parts.append("running")
    if mem is not None:
        parts.append(f"{mem:.0f} MB")
    left = max(0.0, run_seconds - (now - started))
    parts.append(f"restart in {left / 60:.0f} min" if left >= 90 else f"restart in {left:.0f} s")
    return " | ".join(parts)


def run_once(script, run_seconds, grace, max_wait, max_mb):
    state = {"last_click": 0.0}

    popen_kwargs = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    # BOT_STATUS_PIPE tells the bot to report scans to us instead of drawing its own status line.
    env = dict(os.environ, PYTHONIOENCODING="utf-8", BOT_STATUS_PIPE="1")

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

    mem = None
    last_check = 0.0
    warned = False
    try:
        while proc.poll() is None:
            time.sleep(1)
            now = time.time()
            if now - last_check >= 5:
                last_check = now
                mem = tree_mb(proc)
                if mem is None and max_mb and not warned:
                    log("psutil is not installed, so the memory limit is OFF and the status line "
                        "cannot show memory (fix: pip install psutil)")
                    warned = True
            reason = None
            if now - started >= run_seconds:
                reason = "time is up"
            elif max_mb and mem is not None and mem > max_mb:
                reason = f"memory limit reached ({mem:.0f} MB > {max_mb:g} MB)"
            if reason:
                deadline = time.time() + max_wait
                while time.time() - state["last_click"] < grace and time.time() < deadline:
                    draw_status(status_text(state, started, run_seconds, mem))
                    time.sleep(1)
                log(f"{reason}, restarting the bot")
                break
            draw_status(status_text(state, started, run_seconds, mem))
        else:
            log(f"bot exited by itself (code {proc.returncode})")
    finally:
        clear_status()
        kill_tree(proc)


def main():
    ap = argparse.ArgumentParser(description="Restart a bot script on a timer.")
    ap.add_argument("script", nargs="?", default="click_bot.py")
    ap.add_argument("--minutes", type=float, default=60, help="how long each run lasts")
    ap.add_argument("--grace", type=float, default=60, help="seconds to wait after a tick before restarting")
    ap.add_argument("--max-wait", type=float, default=300, help="longest the restart may be delayed")
    ap.add_argument("--max-mb", type=float, default=1500,
                    help="restart the bot if it and its browser use more than this many MB (0 = off; needs psutil)")
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
            run_once(script, args.minutes * 60, args.grace, args.max_wait, args.max_mb)
            time.sleep(5)
    except KeyboardInterrupt:
        clear_status()
        log("stopped by user")


if __name__ == "__main__":
    main()
