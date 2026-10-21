# Consultation Booking Bots: README

Bots for the Manipal **Statistical Consultancy Services** portal (course curriculum). They log in as a Data Science student, watch the *Upcoming Consultations* table, and tick the checkbox on slots for the faculty you list, while respecting weekly and daily limits and a 30-minute overlap rule.

*Last checked against the live portal on 21 October 2026. See section 10 for what was and was not verified.*

---

## 1. Quick start

Install once:

```
pip install playwright
playwright install chromium
```

Open the script you want to use and check the settings at the top (section 6). Then run it with the hourly restart wrapper:

```
python run_hourly.py click_bot.py
```

Stop with **Ctrl+C**. The wrapper stops the bot and its Chromium together.

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
| **Role** | **Recommended base** | Same logic, noisier, Windows | Experimental | Old reference | Debugging |
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
- **`click_bot.py`** is the best base. It reads your bookings from the right table, ticks one slot per scan and then re-reads your bookings, so the weekly and daily caps stay accurate.
- **`local_bot.py`** if you want to grab several slots in the same pass and want the detailed log. It does not update its counts between ticks, so it can go over your weekly or daily limit.
- **`click_unclick_bot.py`** only if plain ticks do not register. The click, untick, click sequence is not part of the normal workflow, and each toggle may send its own request to the server, so it could release the slot.
- **`Last_working_Code`** and **`test_bot.py`** read your bookings with columns 8/9/10, which does not fit the current 11-column table. They would probably not see your bookings, so the caps would not work. Keep `test_bot.py` only for watching what the page does in a visible browser.

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

It runs a bot, stops it (and the Chromium it started) after N minutes, and starts it again. This stops Chromium's memory from creeping up over a long run. It does not change the bot.

```
python run_hourly.py                                   # click_bot.py, restart every 60 minutes
python run_hourly.py click_bot.py                      # same, explicit
python run_hourly.py click_bot.py --minutes 45         # restart every 45 minutes
python run_hourly.py local_bot.py --minutes 30         # use a different bot
python run_hourly.py click_bot.py --minutes 2          # short test cycle: watch it restart
python run_hourly.py click_bot.py --grace 90           # wait 90 s after a tick before restarting
python run_hourly.py click_bot.py --max-wait 120       # never delay a restart more than 2 minutes
python run_hourly.py "Last_working_Code - 31st March 2026.py"
python run_hourly.py --help
```

| Option | Default | Meaning |
|---|---|---|
| `script` | `click_bot.py` | Which bot to run, as a path relative to where you run the command. |
| `--minutes` | 60 | How long each run lasts. |
| `--grace` | 60 | If the bot ticked a slot this recently (it prints a line containing `CLICKING`), the restart waits. |
| `--max-wait` | 300 | The longest the restart can be delayed by `--grace`. |

Behaviour to know about:
- If the bot crashes or exits by itself, it is started again after 5 seconds. If it exits immediately every time (for example after a typo), the wrapper keeps retrying every 5 seconds, so stop it with Ctrl+C.
- The bot is offline while it relaunches and logs in again, which can take from several seconds to about a minute. Avoid hours when slots usually appear.
- The grace logic depends on the log text `CLICKING`. If you change that line in a bot, the wrapper stops noticing ticks.

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
4. **Console noise:** `Scanning...` prints about 7 times a second and the real events get buried. `click_bot.py` also never prints your bookings.
5. **`local_bot.py`** ticks all eligible rows in one pass without updating its counts, so it can exceed the caps.
6. **Housekeeping:** password in plain text, bare `except:` blocks that hide errors, `browser.close()` after an endless loop (never runs), `cls` only works on Windows, and `click_unclick_bot.py` has two dead copies of old code at the bottom.
7. **Different caps** in different scripts (see the table above).

---

## 8. Memory and performance

- **Printing does not use meaningful RAM.** The terminal keeps a capped scrollback. A log file of `Scanning...` lines grows well under 1 MB an hour at 7 lines a second.
- **Chromium memory can creep up** over hours of reloading every 0.15 s. The hourly restart (section 5) is the main fix.
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

---

## Files

| File | Purpose |
|---|---|
| `click_bot.py` | Recommended bot |
| `local_bot.py` | Verbose variant, ticks all eligible rows |
| `click_unclick_bot.py` | Experimental click/untick/click variant |
| `Last_working_Code - 31st March 2026.py` | Old reference version |
| `test_bot.py` | Visible-browser debugging version |
| `run_hourly.py` | Restart wrapper |
| `README.md` | This file |
