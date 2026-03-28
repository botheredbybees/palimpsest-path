# test_sensors.py — Palimpsest Path pre-deployment hardware self-test
# ──────────────────────────────────────────────────────────────────────────────
# Run this script on each Pico BEFORE deploying main.py.
# Connect via USB REPL (Thonny, mpremote, rshell) to see test output.
#
# Tests performed:
#   1. DS3231 RTC  — I²C scan, register read, timestamp sanity check
#   2. Sensor 1    — beam-break detection on SENSOR_1_PIN (outer / entry-facing)
#   3. Sensor 2    — beam-break detection on SENSOR_2_PIN (inner / gallery-facing)
#   4. SD card     — mount, write, read-back, delete, unmount
#
# LED feedback during tests:
#   Slow double-blink (looping) — waiting for user action
#   3 rapid blinks              — PASS
#   1 long blink                — FAIL
#   10 rapid blinks             — all tests passed (deployment ready)
#   Solid on                    — one or more tests failed
# ──────────────────────────────────────────────────────────────────────────────

import os
import utime
from machine import I2C, SPI, Pin

import sdcard
from config import (
    I2C_BUS, I2C_SDA, I2C_SCL, DS3231_ADDR,
    SPI_BUS, SPI_SCK, SPI_MOSI, SPI_MISO, SD_CS, SD_MOUNT,
    SENSOR_1_PIN, SENSOR_2_PIN,
    LED_PIN, UNIT_ID,
)

# ── Constants ─────────────────────────────────────────────────────────────────
POLL_SECONDS   = 10    # seconds to wait for user to block each sensor beam
RTC_YEAR_MIN   = 2024  # sanity-check lower bound for DS3231 year register
RTC_YEAR_MAX   = 2040  # sanity-check upper bound

_led = Pin(LED_PIN, Pin.OUT)


# ── LED helpers ───────────────────────────────────────────────────────────────

def _blink_pass():
    """3 rapid blinks: PASS."""
    for _ in range(3):
        _led.on();  utime.sleep_ms(100)
        _led.off(); utime.sleep_ms(100)
    utime.sleep_ms(300)


def _blink_fail():
    """1 long blink: FAIL."""
    _led.on();  utime.sleep_ms(1_000)
    _led.off(); utime.sleep_ms(400)


def _blink_waiting():
    """One slow double-blink cycle: still waiting for user input."""
    _led.on();  utime.sleep_ms(200)
    _led.off(); utime.sleep_ms(100)
    _led.on();  utime.sleep_ms(200)
    _led.off(); utime.sleep_ms(500)


# ── BCD decoder (same logic as main.py, local copy to keep this self-contained)
def _bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


# ── Test 1: DS3231 RTC ────────────────────────────────────────────────────────

def test_rtc():
    """
    Verify the DS3231 RTC is reachable and holds a plausible timestamp.

    Steps:
      1. Scan the I²C bus — confirm DS3231 responds at 0x68.
      2. Read registers 0x00–0x06 (sec, min, hr, dow, date, month, year).
      3. Check the oscillator-halt flag (bit 7 of register 0); warn if set.
      4. Decode BCD values and validate ranges.

    Returns True on PASS, False on any failure.
    """
    print("\n[TEST 1/4] DS3231 RTC")
    print("  I²C bus {}: SDA=GP{}, SCL=GP{}".format(I2C_BUS, I2C_SDA, I2C_SCL))
    print("  Expected address: 0x{:02X}".format(DS3231_ADDR))

    try:
        i2c = I2C(I2C_BUS, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400_000)

        # ── Bus scan ──────────────────────────────────────────────────────────
        devices = i2c.scan()
        if DS3231_ADDR not in devices:
            print("  FAIL — 0x{:02X} not found on I²C bus.".format(DS3231_ADDR))
            print("         Devices present: {}".format([hex(d) for d in devices]))
            print("         Check: VCC/GND wiring, SDA/SCL not swapped, pull-up resistors.")
            _blink_fail()
            return False
        print("  I²C scan: found 0x{:02X} ({} device(s) total)".format(
            DS3231_ADDR, len(devices)))

        # ── Read time registers ───────────────────────────────────────────────
        d = i2c.readfrom_mem(DS3231_ADDR, 0x00, 7)

        # Oscillator-halt flag: bit 7 of register 0x00.
        # Set when the DS3231 lost power and the oscillator stopped.
        # Time will be wrong; must be re-set before deployment.
        if d[0] & 0x80:
            print("  WARN  — Oscillator-halt (CH) flag is set.")
            print("          The clock has not been running. Set the time before deployment.")
            print("          See firmware/README.md for the RTC clock-setting snippet.")

        ss = _bcd(d[0] & 0x7F)
        mm = _bcd(d[1])
        hh = _bcd(d[2] & 0x3F)   # mask 12/24-hr bit
        dd = _bcd(d[4])
        mo = _bcd(d[5] & 0x1F)   # mask century bit
        yy = 2000 + _bcd(d[6])

        ts_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            yy, mo, dd, hh, mm, ss)
        print("  Timestamp read: {}".format(ts_str))

        # ── Sanity checks ─────────────────────────────────────────────────────
        errors = []
        if not (RTC_YEAR_MIN <= yy <= RTC_YEAR_MAX):
            errors.append("year {} out of range ({}-{})".format(yy, RTC_YEAR_MIN, RTC_YEAR_MAX))
        if not (1 <= mo <= 12):
            errors.append("month {} invalid".format(mo))
        if not (1 <= dd <= 31):
            errors.append("day {} invalid".format(dd))
        if not (0 <= hh <= 23):
            errors.append("hour {} invalid".format(hh))
        if not (0 <= mm <= 59):
            errors.append("minute {} invalid".format(mm))
        if not (0 <= ss <= 59):
            errors.append("second {} invalid".format(ss))

        if errors:
            print("  FAIL  — Implausible register values:")
            for e in errors:
                print("          - {}".format(e))
            print("          Set the RTC clock before deployment (see README.md).")
            _blink_fail()
            return False

        print("  PASS  — RTC responding; timestamp looks valid.")
        _blink_pass()
        return True

    except OSError as e:
        print("  FAIL  — I²C OSError: {}".format(e))
        print("          Check wiring and that 3.3 V is present on DS3231 VCC.")
        _blink_fail()
        return False


# ── Tests 2 & 3: IR Sensors ───────────────────────────────────────────────────

def test_sensor(pin_num, label, poll_s=POLL_SECONDS):
    """
    Verify one E18-D80NK IR sensor responds to a manual beam interruption.

    The user is prompted to wave their hand through the sensor beam within
    `poll_s` seconds. The LED blinks slowly while waiting. On detection, the
    beam-break duration (transit_ms) is measured and reported.

    Parameters
    ----------
    pin_num : int
        GPIO pin number (e.g. 14 or 15).
    label : str
        Human-readable sensor name for REPL output.
    poll_s : int
        Seconds to wait for a beam-break before declaring FAIL.

    Returns
    -------
    bool
        True on PASS, False on FAIL or timeout.

    Notes
    -----
    The pin is configured with no internal pull-up (external 10 kΩ to 3.3 V
    is present on the PCB). An idle beam reads HIGH (1); blocked beam reads
    LOW (0).
    """
    print("\n[TEST] {}".format(label))
    print("  GPIO: GP{}  (no internal pull-up — external 10 kΩ expected)".format(pin_num))

    # No Pin.PULL_UP — external 10 kΩ pull-up to 3.3 V is on the PCB
    pin = Pin(pin_num, Pin.IN)
    utime.sleep_ms(10)   # allow pin to settle

    # ── Idle-state check ──────────────────────────────────────────────────────
    idle_val = pin.value()
    if idle_val == 0:
        print("  WARN  — Pin is already LOW at start of test.")
        print("          Beam may be blocked, or NPN collector is shorted to GND.")
        print("          Remove any obstruction and re-run if this is unexpected.")
    else:
        print("  Idle state: HIGH (beam clear) ✓")

    # ── Wait for beam break ───────────────────────────────────────────────────
    print("  Block the sensor beam within {} seconds...".format(poll_s))
    t_start = utime.ticks_ms()
    detected = False

    while utime.ticks_diff(utime.ticks_ms(), t_start) < poll_s * 1000:
        if pin.value() == 0:   # FALLING: beam broken
            detected = True
            break
        _blink_waiting()

    _led.off()

    if not detected:
        print("  FAIL  — No beam break detected within {} s.".format(poll_s))
        print("          Check: 5 V present on sensor VCC (boost module output),")
        print("                 sensor aimed correctly, signal wire connected to GP{}.".format(pin_num))
        _blink_fail()
        return False

    # ── Measure transit duration ──────────────────────────────────────────────
    t_fall = utime.ticks_ms()
    while pin.value() == 0:
        utime.sleep_ms(1)   # wait for rising edge
    transit_ms = utime.ticks_diff(utime.ticks_ms(), t_fall)

    print("  PASS  — Beam break detected.")
    print("          Transit duration: {} ms  (solo walker expected ~200–600 ms)".format(transit_ms))
    _blink_pass()
    return True


# ── Test 4: SD Card ───────────────────────────────────────────────────────────

def test_sd():
    """
    Verify the SPI SD card module mounts, accepts a write, and reads back
    correctly, then unmounts cleanly.

    A temporary test file is written to ``SD_MOUNT/UNIT_ID/TEST_UNIT_ID.txt``
    and deleted on success. If the unit directory does not yet exist it is
    created (matching the behaviour of the main firmware).

    Returns True on PASS, False on any failure.
    """
    print("\n[TEST 4/4] SD Card")
    print("  SPI{}: SCK=GP{}, MOSI=GP{}, MISO=GP{}, CS=GP{}".format(
        SPI_BUS, SPI_SCK, SPI_MOSI, SPI_MISO, SD_CS))

    try:
        spi = SPI(
            SPI_BUS, baudrate=1_000_000, polarity=0, phase=0,
            sck=Pin(SPI_SCK), mosi=Pin(SPI_MOSI), miso=Pin(SPI_MISO),
        )
        cs = Pin(SD_CS, Pin.OUT)
        sd = sdcard.SDCard(spi, cs)
        vfs = os.VfsFat(sd)
        os.mount(vfs, SD_MOUNT)
        print("  Mounted FAT32 at {}".format(SD_MOUNT))

        # ── Ensure unit directory exists ──────────────────────────────────────
        unit_dir = "{}/{}".format(SD_MOUNT, UNIT_ID)
        try:
            os.mkdir(unit_dir)
            print("  Created: {}".format(unit_dir))
        except OSError:
            print("  Exists:  {}".format(unit_dir))

        # ── Write test file ───────────────────────────────────────────────────
        test_path = "{}/TEST_{}.txt".format(unit_dir, UNIT_ID)
        sentinel  = "palimpsest-self-test-{}".format(UNIT_ID)
        with open(test_path, 'w') as f:
            f.write(sentinel + "\n")
        print("  Wrote:   {}".format(test_path))

        # ── Read back and verify ──────────────────────────────────────────────
        with open(test_path, 'r') as f:
            content = f.read().strip()

        if content != sentinel:
            print("  FAIL  — Read-back mismatch.")
            print("          Expected: {}".format(sentinel))
            print("          Got:      {}".format(content))
            _blink_fail()
            os.umount(SD_MOUNT)
            return False

        print("  Read-back verified ✓")

        # ── Cleanup ───────────────────────────────────────────────────────────
        os.remove(test_path)
        print("  Deleted test file.")

        os.umount(SD_MOUNT)
        print("  PASS  — SD card read/write/delete successful.")
        _blink_pass()
        return True

    except Exception as e:
        print("  FAIL  — {}".format(e))
        print("          Check: card inserted, FAT32 formatted (not exFAT), wiring.")
        _blink_fail()
        try:
            os.umount(SD_MOUNT)
        except Exception:
            pass
        return False


# ── Run all tests ─────────────────────────────────────────────────────────────

def run_all():
    print("=" * 50)
    print("Palimpsest Path — Hardware Self-Test")
    print("Unit: {}".format(UNIT_ID))
    print("=" * 50)
    print("Tip: keep this REPL session open to read results.")

    results = {
        "RTC (DS3231)":
            test_rtc(),
        "Sensor 1 — outer/entry-facing (GP{})".format(SENSOR_1_PIN):
            test_sensor(
                SENSOR_1_PIN,
                "Sensor 1 — outer / entry-facing (GP{})  [TEST 2/4]".format(SENSOR_1_PIN),
            ),
        "Sensor 2 — inner/gallery-facing (GP{})".format(SENSOR_2_PIN):
            test_sensor(
                SENSOR_2_PIN,
                "Sensor 2 — inner / gallery-facing (GP{})  [TEST 3/4]".format(SENSOR_2_PIN),
            ),
        "SD Card":
            test_sd(),
    }

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    all_pass = True
    for name, passed in results.items():
        icon = "PASS" if passed else "FAIL"
        print("  [{}] {}".format(icon, name))
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("All tests passed — unit is ready for deployment.")
        print("Next steps:")
        print("  1. Verify UNIT_ID = '{}' in config.py is correct.".format(UNIT_ID))
        print("  2. Copy main.py, config.py, sdcard.py to the Pico.")
        print("  3. Disconnect REPL and seal the enclosure.")
        # Celebratory rapid blink
        for _ in range(10):
            _led.on();  utime.sleep_ms(60)
            _led.off(); utime.sleep_ms(60)
    else:
        print("One or more tests FAILED. Resolve issues before deployment.")
        print("Refer to firmware/README.md for wiring diagrams and troubleshooting.")
        _led.on()   # solid LED = unresolved failure; power-cycle to reset


run_all()
