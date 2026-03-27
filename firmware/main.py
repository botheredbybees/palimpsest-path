# main.py — Palimpsest Path sensor node firmware
# ──────────────────────────────────────────────────────────────────────────────
# MicroPython for Raspberry Pi Pico (RP2040)
# Two E18-D80NK IR sensors → DS3231 RTC timestamps → daily CSV on SD card.
#
# Requires on the Pico filesystem:
#   config.py   — all tunable constants (this directory)
#   sdcard.py   — SPI SD card driver (from MicroPython 'drivers' repo or frozen)
# ──────────────────────────────────────────────────────────────────────────────

import array
import machine
import os
import utime

import sdcard
from config import (
    UNIT_ID,
    I2C_BUS, I2C_SDA, I2C_SCL, DS3231_ADDR,
    SPI_BUS, SPI_SCK, SPI_MOSI, SPI_MISO, SD_CS, SD_MOUNT,
    SENSOR_1_PIN, SENSOR_2_PIN,
    DEBOUNCE_MS, SEQUENCE_WINDOW_MS, MIN_TRANSIT_MS, MAX_TRANSIT_MS,
    CSV_HEADER, RAM_BUFFER_MAX,
    LED_PIN, LED_ERR_RTC, LED_ERR_SD_WRITE, LED_ERR_SD_MOUNT,
)

# ── Onboard LED ───────────────────────────────────────────────────────────────
_led = machine.Pin(LED_PIN, machine.Pin.OUT)


def _blink(code):
    """
    Blink the onboard LED `code` times to signal an error condition.
    Called only from the main loop (not ISR context) — safe to use sleep.

    Error codes (see config.py):
      LED_ERR_RTC      (2) — DS3231 read failed
      LED_ERR_SD_WRITE (3) — SD card write failed, row buffered to RAM
      LED_ERR_SD_MOUNT (5) — SD card failed to mount on boot
    """
    for _ in range(code):
        _led.on()
        utime.sleep_ms(200)
        _led.off()
        utime.sleep_ms(200)
    utime.sleep_ms(600)   # pause between repeated error signals


# ── DS3231 RTC ────────────────────────────────────────────────────────────────
# I²C address 0x68 is fixed in silicon on all DS3231 chips.
# Registers 0x00–0x06 hold BCD-encoded: sec, min, hr, dow, date, month, year.
# We mask bit 7 of seconds (oscillator-halt flag) and bit 6 of hours (12/24 flag).
_i2c = machine.I2C(
    I2C_BUS,
    sda=machine.Pin(I2C_SDA),
    scl=machine.Pin(I2C_SCL),
    freq=400_000,
)


def _bcd(b):
    """Decode a BCD byte → integer. E.g. 0x25 → 25."""
    return (b >> 4) * 10 + (b & 0x0F)


def rtc_datetime():
    """
    Read the DS3231 and return (year, month, day, hour, minute, second).
    Returns None and blinks LED_ERR_RTC if the I²C transaction fails.
    """
    try:
        d = _i2c.readfrom_mem(DS3231_ADDR, 0x00, 7)
        ss = _bcd(d[0] & 0x7F)   # mask oscillator-halt bit
        mm = _bcd(d[1])
        hh = _bcd(d[2] & 0x3F)   # mask 12/24-hr and century bits
        dd = _bcd(d[4])
        mo = _bcd(d[5] & 0x1F)   # mask century flag
        yy = 2000 + _bcd(d[6])
        return (yy, mo, dd, hh, mm, ss)
    except OSError:
        _blink(LED_ERR_RTC)
        return None


def rtc_iso():
    """
    Return an ISO 8601 timestamp string: "YYYY-MM-DDTHH:MM:SS".
    Returns an empty string if the RTC is unreachable (allows logging to
    continue with a blank timestamp rather than crashing).
    """
    dt = rtc_datetime()
    if dt is None:
        return ""
    yy, mo, dd, hh, mm, ss = dt
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
        yy, mo, dd, hh, mm, ss
    )


def rtc_date_str():
    """Return YYYY-MM-DD date string for constructing daily filenames."""
    dt = rtc_datetime()
    if dt is None:
        return "0000-00-00"
    return "{:04d}-{:02d}-{:02d}".format(dt[0], dt[1], dt[2])


# ── SD card ───────────────────────────────────────────────────────────────────
# We open → write → close on every event rather than keeping the file open.
# This ensures each row is flushed to FAT even on unexpected power loss.
# At the expected rate of ≤300 events/day the open/close overhead is negligible.
_sd_ok   = False
_ram_buf = []    # list[str] — fallback when SD is unavailable


def sd_mount():
    """
    Initialise SPI0 and mount the SD card as a FAT32 VFS at SD_MOUNT.
    Sets global _sd_ok; blinks LED_ERR_SD_MOUNT and continues on failure.
    """
    global _sd_ok
    try:
        spi = machine.SPI(
            SPI_BUS,
            baudrate=1_000_000,   # conservative init rate; sdcard.py may go faster
            polarity=0,
            phase=0,
            sck=machine.Pin(SPI_SCK),
            mosi=machine.Pin(SPI_MOSI),
            miso=machine.Pin(SPI_MISO),
        )
        cs = machine.Pin(SD_CS, machine.Pin.OUT)
        sd = sdcard.SDCard(spi, cs)
        vfs = os.VfsFat(sd)
        os.mount(vfs, SD_MOUNT)
        _sd_ok = True
    except Exception:
        _blink(LED_ERR_SD_MOUNT)
        _sd_ok = False


def _ensure_dir(path):
    """Create directory at path if it does not already exist."""
    try:
        os.mkdir(path)
    except OSError:
        pass   # already exists — not an error


def _csv_path(date_str):
    """Construct the full SD path for today's CSV file."""
    return "{}/{}/{}_{}.csv".format(SD_MOUNT, UNIT_ID, date_str, UNIT_ID)


def _write_line_to_sd(line, date_str):
    """
    Internal helper: open the daily CSV, write a line, close.
    Creates the per-unit directory and header row if this is a new file.
    Raises on any OS error so the caller can handle it.
    """
    unit_dir = "{}/{}".format(SD_MOUNT, UNIT_ID)
    _ensure_dir(unit_dir)
    path = _csv_path(date_str)
    # Write header if file is new
    try:
        os.stat(path)
        write_header = False
    except OSError:
        write_header = True
    with open(path, 'a') as f:
        if write_header:
            f.write(CSV_HEADER + "\n")
        f.write(line + "\n")


def _flush_ram_buf(date_str):
    """
    Attempt to write all buffered rows to SD.
    Silently abandons if writing fails — rows remain in buffer for next attempt.
    """
    global _ram_buf
    if not _ram_buf:
        return
    try:
        unit_dir = "{}/{}".format(SD_MOUNT, UNIT_ID)
        _ensure_dir(unit_dir)
        path = _csv_path(date_str)
        try:
            os.stat(path)
            write_header = False
        except OSError:
            write_header = True
        with open(path, 'a') as f:
            if write_header:
                f.write(CSV_HEADER + "\n")
            for row in _ram_buf:
                f.write(row + "\n")
        _ram_buf = []   # clear only on full success
    except Exception:
        pass


def sd_write(line):
    """
    Write a CSV row string to the daily SD file.
    On failure: blink LED_ERR_SD_WRITE, buffer the row in RAM, and continue.
    On the next successful write, the RAM buffer is flushed first.
    If the RAM buffer is full, the oldest row is discarded (ring behaviour).
    """
    global _sd_ok
    date_str = rtc_date_str()

    # Try to flush any previously buffered rows before writing the new one
    if _ram_buf and _sd_ok:
        _flush_ram_buf(date_str)

    try:
        _write_line_to_sd(line, date_str)
        _sd_ok = True
    except Exception:
        _sd_ok = False
        _blink(LED_ERR_SD_WRITE)
        if len(_ram_buf) >= RAM_BUFFER_MAX:
            _ram_buf.pop(0)    # discard oldest to make room
        _ram_buf.append(line)


# ── ISR-safe sensor state ─────────────────────────────────────────────────────
# All arrays are pre-allocated at module load time.
# ISR handlers MUST NOT allocate heap memory (no list operations, no f-strings
# with expressions, no new objects). array.array writes are in-place and safe.
#
# Index 0 → Sensor 1 (SENSOR_1_PIN, outer)
# Index 1 → Sensor 2 (SENSOR_2_PIN, inner)

_fall_time   = array.array('l', [0, 0])  # ticks_ms() when beam was broken
_rise_time   = array.array('l', [0, 0])  # ticks_ms() when beam was restored
_last_fall   = array.array('l', [0, 0])  # ticks_ms() of previous fall (debounce)
_beam_active = array.array('b', [0, 0])  # 1 = beam currently broken
_event_ready = array.array('b', [0, 0])  # 1 = complete fall+rise event waiting


def _make_irq(idx):
    """
    Return an ISR handler for sensor at array index `idx`.

    Uses a closure to bind `idx` at creation time. The closure itself allocates
    on the heap once (here, at startup), but the returned function never
    allocates — it only reads the pin value and writes to pre-allocated arrays.

    Falling edge (beam broken):
      - Debounce check: ignore if within DEBOUNCE_MS of the last falling edge
      - Record fall_time; mark beam active

    Rising edge (beam restored):
      - If beam was active: record rise_time, clear active, set event_ready
    """
    def handler(pin):
        now = utime.ticks_ms()
        if pin.value() == 0:                          # FALLING — beam broken
            if utime.ticks_diff(now, _last_fall[idx]) < DEBOUNCE_MS:
                return                                # debounce: ignore
            _fall_time[idx]   = now
            _last_fall[idx]   = now
            _beam_active[idx] = 1
        else:                                         # RISING — beam restored
            if _beam_active[idx]:
                _rise_time[idx]   = now
                _beam_active[idx] = 0
                _event_ready[idx] = 1
    return handler


# ── Sensor pin setup ──────────────────────────────────────────────────────────
# Pin.IN with no pull argument: external 10 kΩ pull-ups to 3.3 V are on the PCB.
# IRQ_FALLING | IRQ_RISING: we need both edges to measure beam duration.
_sensor_pins = [
    machine.Pin(SENSOR_1_PIN, machine.Pin.IN),
    machine.Pin(SENSOR_2_PIN, machine.Pin.IN),
]
_sensor_pins[0].irq(
    trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING,
    handler=_make_irq(0),
)
_sensor_pins[1].irq(
    trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING,
    handler=_make_irq(1),
)


# ── Direction logic ───────────────────────────────────────────────────────────
def _direction(idx):
    """
    Infer travel direction from which sensor fell first.

    ticks_diff(a, b) returns a - b with wrap-around handling.
    dt = ticks_diff(fall_time[idx], fall_time[other])
      dt < 0  →  idx fell BEFORE other  →  idx was triggered first
      dt > 0  →  idx fell AFTER other   →  other was triggered first

    Sensor 0 = outer (entry-facing):
      Sensor 0 first → "inbound"   (person entering gallery)
      Sensor 1 first → "outbound"  (person leaving gallery)

    Sensor 1 = inner (gallery-facing):
      Sensor 1 first → "outbound"  (person leaving gallery)
      Sensor 0 first → "inbound"   (person entering gallery)

    If the gap between the two fall times exceeds SEQUENCE_WINDOW_MS,
    the two triggers are not treated as a matched pair → "unknown".
    This covers: single-sensor passes (person turned back), simultaneous
    bidirectional traffic, or a sensor obstructed without the other firing.
    """
    other = 1 - idx
    dt = utime.ticks_diff(_fall_time[idx], _fall_time[other])
    if abs(dt) > SEQUENCE_WINDOW_MS:
        return "unknown"
    # dt <= 0: idx fired first (or same tick — treated as idx-first)
    if dt <= 0:
        return "inbound" if idx == 0 else "outbound"
    else:
        return "outbound" if idx == 0 else "inbound"


# ── Event processing ──────────────────────────────────────────────────────────
def _process_event(idx):
    """
    Handle a completed beam-break event for sensor `idx`.

    Calculates transit_ms (beam-blocked duration for this sensor only),
    applies range filters, reads the RTC timestamp, determines direction,
    and writes one CSV row.

    One row is logged per sensor per pass. A person triggering both sensors
    therefore produces two rows with the same direction but potentially
    different transit_ms values — useful for detecting groups (a group
    blocks the beam longer than a solo walker).
    """
    transit_ms = utime.ticks_diff(_rise_time[idx], _fall_time[idx])

    # Discard implausibly short events (noise) and overlong holds
    if transit_ms < MIN_TRANSIT_MS or transit_ms > MAX_TRANSIT_MS:
        return

    ts        = rtc_iso()
    direction = _direction(idx)
    beam      = idx + 1   # 1-indexed for the CSV

    row = "{},{},{},{},{}".format(ts, UNIT_ID, direction, beam, transit_ms)
    sd_write(row)


def _drain_events():
    """
    Process all pending events, looping until none remain.

    SD writes and RTC reads take a few milliseconds each. New events can
    arrive during that time. We keep draining until both flags are clear
    before returning to lightsleep.
    """
    any_pending = True
    while any_pending:
        any_pending = False
        for idx in range(2):
            if _event_ready[idx]:
                _event_ready[idx] = 0   # clear before processing so re-entrant
                _process_event(idx)     # events during this call are caught next lap
                any_pending = True


def _cleanup_stale():
    """
    Clear beam-active state that has exceeded MAX_TRANSIT_MS.

    Guards against a sensor being permanently blocked (debris, vandalism)
    which would prevent future events on that channel from being logged.
    """
    now = utime.ticks_ms()
    for idx in range(2):
        if _beam_active[idx]:
            if utime.ticks_diff(now, _fall_time[idx]) > MAX_TRANSIT_MS:
                _beam_active[idx] = 0
                _event_ready[idx] = 0


# ── Boot sequence ─────────────────────────────────────────────────────────────
sd_mount()

# Single short heartbeat blink confirms successful boot
_led.on()
utime.sleep_ms(500)
_led.off()

# ── Main loop ─────────────────────────────────────────────────────────────────
# machine.lightsleep() halts the CPU until the next GPIO IRQ fires.
# On RP2040, GPIO interrupts remain active during lightsleep; the ISR
# runs, sets _event_ready, and execution resumes here after the IRQ.
# Current draw: ~1.3 mA during lightsleep vs ~25 mA active.
#
# The ISR handles the time-critical part (recording timestamps in µs).
# All file I/O and string formatting happens here in the main loop,
# safely outside interrupt context.
while True:
    machine.lightsleep()
    _drain_events()
    _cleanup_stale()
