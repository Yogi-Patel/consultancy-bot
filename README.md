# Consultation Booking Bots: README

Bots for the Manipal **Statistical Consultancy Services** portal (course curriculum). They log in as a Data Science student, watch the *Upcoming Consultations* table, and tick the checkbox on slots for the faculty you list, while respecting weekly and daily limits and a 30-minute overlap rule.

*Last checked against the live portal on 21 October 2026. See section 10 for what was and was not verified.*

---

## 1. Quick start

Install once:

```
pip install playwright psutil
playwright install chromium
```

(`psutil` is optional but needed for the memory limit in `run_hourly.py`, the memory figure on its status line, and the memory readout in the `_lowmem2` scripts.)

### Where are you running it?

| Where | Use this script | Notes |
|---|---|---|
| **Your own PC** | `local_bot.py` | Gives the detailed log (prints your bookings and the reason for each skip) and clears the console every 500 scans with `cls`, which only works on Windows. |
| **A cloud platform** | `click_bot.py` | **Go through `cloud_readme` as well as this README before deploying.** |
| **A PC with fairly little resources** | `click_bot.py` | Quiet log and one tick per scan. |

Open the script you want to use and check the settings at the top (section 6). Then run it with the hourly restart wrapper:

```
python run_hourly.py click_bot.py      # cloud platform, or a PC with little resources
python run_hourly.py local_bot.py      # your own PC
```

**For anything longer than a few minutes, use the `_lowmem2` version of the same script** (see known issue 8). On the original scripts, Python's memory grew by roughly 100 MB a minute in testing:

```
python run_hourly.py click_bot_lowmem2.py      # click_bot.py with the memory fix
python run_hourly.py local_bot_lowmem2.py      # local_bot.py with the memory fix
```

Stop with **Ctrl+C**. The wrapper stops the bot and its Chromium together.

**How to tell it is working:** look at the **last line of the console**. It is a live status line that updates every second, even when no log lines are appearing:

```
14:10:42 | last scan 1 s ago | 1,234 scans | 480 MB | restart in 17 min
```

If the clock moves and `last scan` stays at 0 to 2 seconds, the bot is working. See "The live status line" in section 3.

---

## 2. How the portal page works

Pages (all under `https://portal.manipal.edu/statistics/`):

| Page | What it is |
|---|---|
| `I11` | Login. Pick the role in the dropdown (Faculty = `F`, **Student = `S`**), click Continue, then enter roll number and password. |
| `I8` | Home page after login. Shows "Today's" and "Upcoming" consultation lists. Not used by the bots. |
| `I7` | **Consultation Details**: the page the bots work on. |

The page is `I7`, with a link called "Consultation Details" in the menu. The bots click that link after logging in.

### Workflow (how booking works, as described by you)
- Slots that can be taken appear at the **top of the Upcoming Consultations table**.
- You **tick the checkbox** on time, wait about **20 seconds**, then refresh to see whether you got it.
- Consultations you have selected, under your name, appear in the **last table on the page** (headed "Consultations Selected"), which is how you see how many you have in each week.

### The four tables on `I7` (in page order)

| # | Table id | Heading | Columns | Notes |
|---|---|---|---|---|
| 1 | `Griddets` | Consultations : | 12 (tick box first) | Long paginated list. No script uses it. |
| 2 | `grdstudconsult` | Consultations Selected : | 11 | Consultations under your name. It showed one booking, dated 11/04/2026, on 21 Oct. |
| 3 | `grdupevents` | **Upcoming Consultations :** | 12 (tick box first) | **The table the bots tick.** |
| 4 | `grdstudupconsult` | Consultations Selected : (same heading again) | Not seen (assumed 11) | **The last table. Your upcoming selections** (per your description). It was empty on 21 Oct and shows "No Consultation Today" when empty. |

### Column positions the scripts rely on (counting from 0)

**Upcoming table (12 cells per row):** 0 tick box, 1 Request No, 2 student, 3 consultee, 4 department, 5 institution, 6 course, 7 roll no / email, **8 date**, **9 time**, 10 faculty, 11 guide.

**Selected tables (11 cells per row; seen in table 2, assumed for table 4):** 0 Request No, **1 student**, 2 consultee, 3 department, 4 institution, 5 course, 6 roll no / email, **7 date**, **8 time**, **9 faculty email**, 10 guide.

If the portal changes and the bots stop reading dates, check these positions first.

---

## 3. The scripts and how they differ

| | `click_bot.py` | `local_bot.py` | `click_unclick_bot.py` | `Last_working_Code - 31st March 2026.py` | `test_bot.py` |
|---|---|---|---|---|---|
| **Role** | **Recommended base.** Cloud platform, or a PC with little resources | **Your own PC.** Same logic, noisier, Windows | Experimental | Old reference | Debugging |
| Browser | Headless | Headless | Headless + Linux flags (`--no-sandbox`, `--disable-dev-shm-usage`) | Headless | **Visible window** |
| Skips images, fonts, CSS | Yes | Yes | Yes | No | No |
| Faculty (priority order) | suresha, bhagyajyothi, satya | suresha, bhagyajyothi, satya | suresha, bhagyajyothi, satya, vasudev, **varunsg** | suresha, satya, vasudev, bhagyajyothi | suresha, satya, vasudev |
| Commented out | vasudev, varunsg | vasudev, varunsg | none | n/a | n/a |
| Weekly / daily cap | 2 / 2 | 4 / 3 | 3 / 3 | 2 / none | none |
| Ticks per scan | **One**, then re-reads your bookings | **All eligible** in one pass | One, using click, untick, click | All eligible | All eligible |
| Wait after tick | **3 s** | **3 s** | 20 s (plus 1 s between toggles) | 20 s | 20 s |
| Pause between scans | 0.15 s | 0.15 s | 0.1 s | 1 s | 3 s |
| Reads your bookings from | last table (`table.last`), columns 1/7/8/9 | last table, columns 1/7/8/9 | last table, columns 1/7/8/9 | "Consultations Selected" sections, columns 8/9/10 | same as March |
| Logging | Minimal | Most verbose: prints your bookings and skip reasons | Minimal | Moderate, 10-minute "still running" note | Plain prints |
| Same faculty back-to-back | Allowed | Allowed | Allowed | Allowed | **Not allowed** (any overlap blocks) |
| Other | | `cls` every 500 scans (Windows only) | Two old versions left as comments at the bottom | | Email code present but disabled |

### Which to use
- **`click_bot.py`** is the best base, and the one to use on a **cloud platform or a PC with fairly little resources**. It reads your bookings from the right table, ticks one slot per scan and then re-reads your bookings, so the weekly and daily caps stay accurate.
- **`local_bot.py`** is for running on **your own PC**. It gives the detailed log and grabs several slots in the same pass. It does not update its counts between ticks, so it can go over your weekly or daily limit.
- **`click_unclick_bot.py`** only if plain ticks do not register. The click, untick, click sequence is not part of the normal workflow, and each toggle may send its own request to the server, so it could release the slot.
- **`Last_working_Code`** and **`test_bot.py`** read your bookings with columns 8/9/10, which does not fit the current 11-column table. They would probably not see your bookings, so the caps would not work. Keep `test_bot.py` only for watching what the page does in a visible browser.

### What the `_lowmem2` scripts print

They print a line only when something changes, so **a quiet console is normal**. The live status line at the bottom (explained after this table) shows that it is still scanning. Over a 60-second test where the portal changed on a script, the previous version printed 130 lines (`click_bot`) and 541 lines (`local_bot`); these print 20.

| Line | When it appears |
|---|---|
| `Bot started`, `Logging in...`, `Login successful` | At start, and again only if the session drops |
| `=== CURRENT BOOKINGS ===` block, or `No consultations booked yet.` | Once at start, then only when your bookings change. A failed read of the table prints nothing, so it cannot cause a false "no bookings" line |
| `Free slot:`, `Already selected:`, `Skipped (weekly limit)`, `Skipped (daily limit)`, `Skipped (overlap)`, `Skipped (no checkbox)` followed by the request number, faculty and date | When a slot for one of your faculty appears or its status changes |
| `No longer listed: ...` | When a slot disappears |
| `No matching consultations right now.` | Once at start, and when the last matching slot disappears |
| `CLICKING: ...` | Every time it ticks a box. This exact word is what `run_hourly.py` watches for, so it was left unchanged |
| An error line (first line of the message only) | Once. Identical repeats are counted: `(that error repeated N more times)`, then `Back to normal: no errors on the last scan.` |
| `Fresh browser context started ... bot memory was N MB` | The first refresh only, then again only if the bot's memory has moved by 25 MB or more (`REFRESH_MEMORY_STEP_MB`). Without `psutil`, only the first one |

Other points:
- Lines show the **request number** where older logs said "student" (known issue 2).
- `local_bot_lowmem2.py` no longer clears the screen every 500 scans (`cls` removed), because with quiet logging it would erase the history you want to keep.
- The last line of the console is a live status line that updates every second. That is the sign of life while the bot is quiet.

### The live status line

The bottom line of the console is redrawn every second. It is never written into the scrollback: log lines scroll up above it.

**Started through `run_hourly.py`** (the normal way):

```
14:10:42 | last scan 1 s ago | 1,234 scans | 480 MB | restart in 17 min
```

| Part | What it tells you |
|---|---|
| `14:10:42` | The current time, from the wrapper. If it stops moving, the console is paused or the wrapper is stuck. |
| `last scan 1 s ago` | The bot's heartbeat: seconds since the bot last finished a scan. **Normal is 0 to 2.** If it keeps growing, the bot is not completing scans (page broken, portal down, login lost). An error line will have been printed above it. |
| `1,234 scans` | Scans completed since the bot last (re)started. A scan that hit an error is not counted. |
| `480 MB` | Memory used by the bot and its browser together. Needs `psutil`. |
| `restart in 17 min` | Countdown to the next scheduled restart (it switches to seconds in the last 90 s). |

Until the first scan completes after a (re)start, the line shows `running` in place of the scan fields.

**Started directly** (`python click_bot_lowmem2.py`): the bot draws its own line, `Last scan 14:10:42 | 1,234 scans`. If that time stops changing, the bot is stuck.

Good to know:
- `last scan` proves the bot is **scanning**. It does not say whether any slots exist. For that, read the log lines above it (`Free slot`, `Already selected`, `No matching consultations right now.`).
- It is drawn only when the output is a console. If you redirect the output to a file (`> bot.log`), no status line and no control characters are written.
- The original scripts (`click_bot.py`, `local_bot.py`) send no scan reports, so through the wrapper their status line shows `running` with the clock, memory and restart countdown, but no `last scan`.

---

## 4. Running the scripts

Run from the folder that contains them.

```
python click_bot.py
python local_bot.py
python click_unclick_bot.py
python test_bot.py
python "Last_working_Code - 31st March 2026.py"
```

Save the output to a file (the console then stays empty):

```
python click_bot.py > bot.log 2>&1
```

---

## 5. `run_hourly.py`: automatic restart wrapper

It runs a bot, stops it (and the Chromium it started) after N minutes, and starts it again. It also restarts the bot early if the bot and its browser together use more than a memory limit (default 1500 MB, needs `psutil`). It does not change the bot. While it runs, the bottom line of the console shows the live status line (section 3).

```
python run_hourly.py                                   # click_bot.py, restart every 60 minutes
python run_hourly.py click_bot.py                      # same, explicit
python run_hourly.py click_bot.py --minutes 45         # restart every 45 minutes
python run_hourly.py local_bot.py --minutes 30         # use a different bot
python run_hourly.py click_bot.py --minutes 2          # short test cycle: watch it restart
python run_hourly.py click_bot.py --grace 90           # wait 90 s after a tick before restarting
python run_hourly.py click_bot.py --max-wait 120       # never delay a restart more than 2 minutes
python run_hourly.py click_bot_lowmem2.py --max-mb 1000   # restart if bot + browser pass 1000 MB
python run_hourly.py click_bot_lowmem2.py --max-mb 0      # switch the memory limit off
python run_hourly.py "Last_working_Code - 31st March 2026.py"
python run_hourly.py --help
```

| Option | Default | Meaning |
|---|---|---|
| `script` | `click_bot.py` | Which bot to run, as a path relative to where you run the command. |
| `--minutes` | 60 | How long each run lasts. |
| `--grace` | 60 | If the bot ticked a slot this recently (it prints a line containing `CLICKING`), the restart waits. |
| `--max-wait` | 300 | The longest the restart can be delayed by `--grace`. |
| `--max-mb` | 1500 | Restart the bot if it, the Playwright driver and Chromium together pass this many MB. `0` turns it off. Without `psutil` it is off and a warning is printed. A fresh bot with its browser used about 480 MB in testing, so do not set it near that. |

Behaviour to know about:
- If the bot crashes or exits by itself, it is started again after 5 seconds. If it exits immediately every time (for example after a typo), the wrapper keeps retrying every 5 seconds, so stop it with Ctrl+C.
- The bot is offline while it relaunches and logs in again, which can take from several seconds to about a minute. Avoid hours when slots usually appear.
- The grace logic depends on the log text `CLICKING`. If you change that line in a bot, the wrapper stops noticing ticks.
- The wrapper starts the bot with the environment variable `BOT_STATUS_PIPE=1`. A `_lowmem2` bot then sends its scan reports to the wrapper (they are not printed) and the wrapper draws the status line. Without the wrapper, the bot draws its own.
- The wrapper no longer prints a memory line every 5 minutes: the memory is part of the status line.
- With `psutil` missing, the memory limit is off, the status line has no memory figure, and a warning is printed once.

---

## 6. Check before every run

1. **Credentials:** `ROLLNO`, `PASSWORD` and `LOGIN_TEXT` at the top of the script. `LOGIN_TEXT` must match the greeting on the page ("Hello" followed by your name). The password is stored in plain text. Do not share the files or upload them anywhere.
2. **Faculty list** (`priority_order`): is everyone you want active, and nobody you don't? On 21 Oct 2026 all three rows showing were with `varunsg.kumar`, who is commented out in `click_bot.py` and `local_bot.py`.
3. **Caps:** the weekly and daily limits in the script should match what your course allows. The scripts use 2/2, 3/3 and 4/3.
4. **Wait after a tick:** the workflow is about 20 seconds. `click_bot.py` and `local_bot.py` wait only 3 seconds.
5. **The PC:** plugged in, set not to sleep, and heavy apps closed. Sleep ends the session.
6. **Test first:** do one short cycle (`--minutes 2`) and check Task Manager that no extra Chrome processes are left over.
7. **Allowed use:** automated booking and refreshing the portal several times a second may not be allowed or may get the account throttled. Check with your department.

---

## 7. Known issues (not yet fixed in the scripts)

1. **3-second wait** in `click_bot.py` and `local_bot.py`. If the server has not registered the tick when the page reloads, the row can still look unticked and the bot may tick it again.
2. **Wrong label in the logs:** for Upcoming rows the code reads column 1, which is the Request No, and calls it `student`. The student's name is column 2.
3. **Overlap check:** every ticked row in Upcoming is treated as yours. The ticked rows seen on 21 Oct carried other students' names, so another student's slot could wrongly block one of yours within 30 minutes (different faculty only). This is an inference from the names.
4. **Console noise (fixed in the `_lowmem2` scripts):** the original scripts print `Scanning...` about 7 times a second, so the real events get buried, and `click_bot.py` never prints your bookings. The `_lowmem2` scripts print only when something changes (see "What the `_lowmem2` scripts print" in section 3).
5. **`local_bot.py`** ticks all eligible rows in one pass without updating its counts, so it can exceed the caps.
6. **Housekeeping:** password in plain text, bare `except:` blocks that hide errors, `browser.close()` after an endless loop (never runs), `cls` only works on Windows, and `click_unclick_bot.py` has two dead copies of old code at the bottom.
7. **Different caps** in different scripts (see the table above).
8. **Python's memory climbs during long runs (fixed in the `_lowmem2` scripts, not yet confirmed on the real portal).** On 21 Oct on Windows, Task Manager showed one Python process growing from about 100 MB to over 1 GB within minutes.
   - **Cause (measured on a local test page, not on the real portal):** the `context.route(...)` handler that blocks images, fonts and CSS makes Playwright's Python client keep a Route and a Request object for *every sub-request of every reload* until the browser context closes. On a heavy page (about 60 requests) the bot's Python memory went from 64 MB to 165 MB in 200 reloads, and the Playwright driver grew too.
   - **Fix in `click_bot_lowmem2.py` and `local_bot_lowmem2.py`:** images, fonts and CSS are blocked inside the browser (no per-request Python work), and the bot moves to a fresh browser context every 100 reloads or 2 minutes (login cookies carried over; never within 30 seconds of a tick). In the same test, Python stayed flat at about 35 MB.
   - **Difference to know about:** blocking now works by file extension (`.png`, `.css`, `.woff` and similar, including with a query string). Images or CSS served from addresses with no extension are no longer blocked, so pages may load slightly more.
   - **Backstop:** `run_hourly.py --max-mb` restarts the bot if total memory goes over the limit, whatever the cause.

---

## 8. Memory and performance

- **Printing does not use meaningful RAM.** The terminal keeps a capped scrollback. A log file of `Scanning...` lines grows well under 1 MB an hour at 7 lines a second.
- **The bot's own Python memory** was the bigger problem: see known issue 8. Use the `_lowmem2` scripts.
- **Chromium memory can creep up** over hours of reloading every 0.15 s. The hourly restart and the memory limit (section 5) handle that.
- **How to tell which process is growing:** Task Manager, Details tab, add the "Command line" column. `python.exe` rows are the bot or the wrapper; `chrome-headless-shell.exe` is the browser; `node.exe` is Playwright's driver.
- **Other ways to lighten the load:**
  - Read the tables in one in-page call instead of one call per cell.
  - Poll fast only around the times slots appear, and slowly otherwise.
  - Launch Chromium with `--disable-gpu`, `--disable-extensions` and a V8 heap limit such as `--js-flags=--max-old-space-size=512`. Do not block scripts: the tick needs the page's JavaScript.
  - Watch the Chrome processes in Task Manager during the first hour.
- On the classic Windows Command Prompt, clicking inside the console can pause the output and block the script at its next print.

---

## 9. Troubleshooting

| Symptom | Likely cause | What to check |
|---|---|---|
| Never ticks anything | All rows already ticked; faculty not in `priority_order`; weekly or daily cap reached; a slot within 30 minutes of another with a different faculty | Compare the page with the script's faculty list and caps |
| No bookings shown | Normal when you have none: the last table says "No Consultation Today" | Book one and check the output again |
| Dates not read | Portal layout changed | Recount columns (section 2) and compare with the indices in the script |
| Login keeps repeating | `LOGIN_TEXT` does not match, wrong role value, or wrong password format | The greeting on the page; role `S` |
| `Cannot find click_bot.py` | Run from the wrong folder | `cd` to the folder with the scripts |
| Extra Chrome processes after a crash | Bot was killed without cleanup | Use `run_hourly.py`, or end them in Task Manager |
| Memory keeps climbing | Running an original script (known issue 8) | Switch to a `_lowmem2` script. Its log prints "Fresh browser context started ... bot memory was N MB" about every 100 reloads; that number should stay roughly flat (tens of MB). If it does not, tell whoever maintains this, with those lines |
| `run_hourly.py` restarts the bot over and over with "memory limit reached" | `--max-mb` is set too low for your machine | Raise it, or use `--max-mb 0` |
| No new log lines for minutes | Normal for a `_lowmem2` script: it prints only on changes | Look at the status line at the bottom. Clock moving and `last scan` at 0 to 2 s: it is working. Clock moving but `last scan` keeps growing: the bot is stuck or the page is broken, so read the last error line above it. Clock frozen: the console is paused (click in the window and press Enter) or the wrapper is stuck |
| `last scan` is growing and an error line says a timeout | The portal is down, your session dropped, or the page layout changed | Open the portal in a normal browser. If the page looks different, see section 2 and "Dates not read" |
| Odd characters such as `←[K` or `[2K` in the console | An old console without escape-code support | Use Windows Terminal or PowerShell, or redirect the output to a file (no status line is drawn then) |

---

## 10. What was and was not verified

**Verified on 21 October 2026**, by reading the live page while signed in (nothing was ticked) and by reading the code:
- The four tables, their ids and order, and the 12/11-column layouts.
- The Upcoming table's date and time at columns 8 and 9, which all five scripts use correctly.
- Every setting in the comparison table in section 3 (caps, waits, faculty lists, browser flags, column indices).

**Not verified:**
- No script was run against the portal.
- The last table was empty that day, so its columns were not seen. The scripts assume the 11-column layout.
- `run_hourly.py` was tested on Linux with a dummy bot only. The Windows stop command (`taskkill /T /F`) and a real Playwright run have not been tested.
- The inference in known issue 3 about ticked rows.
- The memory cause in known issue 8 was found on a local test page with a stand-in for the portal. The real portal's page weight and reload rate were not measured.
- `click_bot_lowmem2.py`, `local_bot_lowmem2.py` and the `--max-mb` limit were tested only on Linux against a local mock of the portal: refreshes by reload count and by time, no refresh while ticking, no image or CSS requests reaching the server, the wrapper restarting on the limit and cleaning up Chromium. Not tested on Windows or on the real portal.
- The change-only logging was tested on Linux against a mock portal that changed on a timeline (slot appears, is ticked, booking appears, overlap skip, slots disappear, page breaks and recovers), and its helper functions were unit-tested. The real portal's pages and the real Windows console were not used, so the exact wording of a real error line may differ.
- The live status line was tested on Linux in a pseudo-terminal drawn by a terminal emulator, against the same mock portal: the clock changed on nearly every second, only one status line was on screen at a time, `last scan` stayed at 0 to 3 s while the mock page was healthy and grew to about 12 s while it was broken, log lines scrolled above the line without leaving copies of it, a bot with no scan reports showed `running`, and with output sent to a file no control characters were written. The Windows consoles (Command Prompt, PowerShell, Windows Terminal) were not tested. The code switches on escape-code support with `os.system("")`, a common step older Windows consoles need.
- `cloud_readme` was not available when this README was written, so nothing here describes its contents. The rule for which script to use where (`local_bot.py` on your own PC, `click_bot.py` on a cloud platform or a low-resource PC) comes from you and was not tested.

---

## Files

| File | Purpose |
|---|---|
| `click_bot.py` | Recommended bot |
| `click_bot_lowmem2.py` | `click_bot.py` plus the memory fix from known issue 8 and change-only logging. Use this one for long runs. |
| `local_bot_lowmem2.py` | `local_bot.py` plus the same memory fix and change-only logging (screen clearing removed). Use this one for long runs on your own PC. |
| `local_bot.py` | Verbose variant, ticks all eligible rows |
| `click_unclick_bot.py` | Experimental click/untick/click variant |
| `Last_working_Code - 31st March 2026.py` | Old reference version |
| `test_bot.py` | Visible-browser debugging version |
| `run_hourly.py` | Restart wrapper |
| `cloud_readme` | Steps for deploying to a cloud platform. Read it together with this README before deploying. |
| `README.md` | This file |
