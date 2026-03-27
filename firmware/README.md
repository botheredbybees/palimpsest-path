# Palimpsest Path — Sensor Node Firmware

MicroPython firmware for the two Raspberry Pi Pico (RP2040) sensor units
on the Cygnet Boardwalk gallery.

---

## Files to copy to each Pico

| File | Purpose |
|------|---------|
| `config.py` | All tunable constants — **edit `UNIT_ID` before flashing** |
| `main.py` | Firmware entry point (runs automatically on boot) |
| `sdcard.py` | SPI SD card driver — see note below |

`sdcard.py` is not part of the standard MicroPython firmware image for the Pico.
Download it from the official MicroPython drivers repository:
`micropython/micropython-lib` → `micropython/drivers/storage/sdcard/sdcard.py`
Copy it to the Pico alongside `main.py` and `config.py`.

---

## Setting UNIT_ID before deployment

Open `config.py` and change the first constant:

```python
# Entry end of the boardwalk gallery
UNIT_ID = "UNIT_A"

# Exit end of the boardwalk gallery
UNIT_ID = "UNIT_B"
```

That is the **only** change needed between the two units. All pin assignments
and thresholds are shared.

---

## Sensor orientation (important)

The direction detection (Option B — sequential) relies on knowing which sensor
faces outward (toward the public approach) and which faces inward (toward the
gallery). In `config.py`:

```
SENSOR_1_PIN = 14   ← outer sensor — first triggered by someone entering
SENSOR_2_PIN = 15   ← inner sensor — second triggered by someone entering
```

Mount both units identically: Sensor 1 (GP14) closest to the street/public side,
Sensor 2 (GP15) closest to the gallery interior. If a unit is mounted mirrored,
inbound and outbound labels will be swapped for that unit.

---

## SD card file structure

The firmware creates one directory per unit and one CSV per calendar day:

```
SD card root/
└── UNIT_A/                          ← created automatically
    ├── 2025-06-01_UNIT_A.csv
    ├── 2025-06-02_UNIT_A.csv
    └── …
```

Each file starts with a header row:

```
timestamp,unit_id,direction,beam,transit_ms
```

Example rows:

```
2025-06-01T09:14:32,UNIT_A,inbound,1,412
2025-06-01T09:14:33,UNIT_A,inbound,2,388
2025-06-01T09:17:55,UNIT_A,outbound,2,501
2025-06-01T09:17:56,UNIT_A,outbound,1,467
```

**Field notes:**
- `direction`: `inbound`, `outbound`, or `unknown` (single-sensor event, or
  two sensors fired more than `SEQUENCE_WINDOW_MS` apart)
- `beam`: `1` = outer sensor (GP14), `2` = inner sensor (GP15)
- `transit_ms`: duration in milliseconds that **this individual sensor's beam**
  was blocked. A solo walker ≈ 200–600 ms; a group ≈ several seconds

One row is logged per sensor per pass, so a person triggering both sensors
produces two consecutive rows.

---

## LED error codes

| Blink pattern | Meaning | Action |
|---------------|---------|--------|
| 1 × 500 ms on startup | Normal boot | — |
| 2 blinks | RTC read failed | Check DS3231 wiring; timestamp field will be blank |
| 3 blinks | SD write failed | Row buffered to RAM; check SD card and retry |
| 5 blinks | SD mount failed | Check SD module wiring; firmware continues RAM-only |

Rows buffered to RAM are flushed automatically when the SD card becomes
available again. The RAM buffer holds up to 100 rows (≈ 8 KB).

---

## Setting the DS3231 clock

The firmware reads the RTC but does not set it. Set the DS3231 clock before
deployment using a short one-off script on the Pico:

```python
from machine import I2C, Pin

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)

def dec_to_bcd(v):
    return ((v // 10) << 4) | (v % 10)

# Set to: 2025-06-01 09:00:00 (Sunday = day 1)
i2c.writeto_mem(0x68, 0x00, bytes([
    dec_to_bcd(0),    # seconds
    dec_to_bcd(0),    # minutes
    dec_to_bcd(9),    # hours (24-hr)
    dec_to_bcd(1),    # day of week (1=Sun)
    dec_to_bcd(1),    # date
    dec_to_bcd(6),    # month
    dec_to_bcd(25),   # year (2025 → 25)
]))
print("RTC set.")
```

Run this once, then copy `main.py`, `config.py`, and `sdcard.py` to the Pico.
The DS3231 maintains time independently from the Pico's power supply via its
onboard coin cell.

---

## Transferring data for analysis

1. Remove the SD card from the unit
2. Copy the `UNIT_A/` (or `UNIT_B/`) directory to `data/raw/UNIT_A/`
   (or `data/raw/UNIT_B/`) on your analysis computer
3. Return the SD card to the unit (existing files are not overwritten —
   the firmware appends to the daily file if it already exists)
4. Run the analysis script (see below)

---

## Running the analysis script

### Requirements

```
pip install pandas scikit-learn matplotlib numpy
```

### Configuration

Edit the `USER CONFIGURATION` block at the top of `analysis/analysis.py`:

```python
DATA_DIR           = "data/raw"       # path to UNIT_A/ and UNIT_B/ subdirs
RAIN_CSV           = "data/rain-events.csv"  # optional; see format below
INTERVENTION_START = "2025-06-01"     # first day of Week 1
POST_INT_START     = "2025-08-03"     # first day of Week 9
```

### Rain events CSV (optional)

Create `data/rain-events.csv` with at minimum a `date` column:

```
date,severity,notes
2025-06-14,heavy,full washout
2025-06-15,light,partial
```

If this file is absent, the rain overlay chart is produced without annotations.

### Run

From the repository root:

```bash
python analysis/analysis.py
```

### Outputs

| File | Description |
|------|-------------|
| `data/analysis/figures/01_weekly_boxplots.png` | Dwell time box plots by phase |
| `data/analysis/figures/02_proportion_bars.png` | Transit/Pause/Dwell proportions |
| `data/analysis/figures/03_rain_overlay.png` | Daily dwell time with rain events |
| `data/analysis/figures/04_post_intervention_trend.png` | Trend line analysis |
| `data/processed/weekly-summary.csv` | Weekly aggregate statistics |
