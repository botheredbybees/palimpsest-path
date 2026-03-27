# Technical Appendix: Sensor Hardware & Firmware

**Raspberry Pi Pico W — IR Beam Counter Units**

---

## Power: 18650 → Pico

The Pico Micro has no built-in LiPo charging circuit, so the TP4056 module sits between the 18650 cell and the Pico.

```
18650 cell
  (+) → TP4056 B+
  (-) → TP4056 B-

TP4056 OUT+ → Pico VSYS (pin 39)
TP4056 OUT- → Pico GND  (pin 38)
```

**Why VSYS and not VBUS or 3V3?**

- VSYS (pin 39) accepts 1.8–5.5V and feeds the Pico's internal 3.3V regulator — a fully charged 18650 at 4.2V is handled cleanly.
- VBUS (pin 40) is for 5V USB power only.
- Never feed raw battery into 3V3 (pin 36) — that bypasses the regulator and will damage the chip.

The TP4056 OUT voltage tracks the 18650 discharge curve (4.2V → ~3.0V cutoff), which is entirely within VSYS tolerance. At 3000 mAh with the Pico in dormant mode (~1.3 µA sleep, ~25 mA active during a beam-break event lasting milliseconds), runtime is measured in weeks between charges.

---

## Full Pinout / Wiring Table

### SD Card Module (SPI0)

| SD Module Pin | Pico Pin | GPIO |
|--------------|----------|------|
| VCC | 3V3 OUT (pin 36) | — |
| GND | GND (pin 38) | — |
| CS (SS) | Pin 9 | GP6 |
| MOSI | Pin 10 | GP7 |
| SCK | Pin 11 | GP8 (SCK) |
| MISO | Pin 12 | GP9 (MISO) |

> Note: Some SD modules want 5V on VCC but have a 3.3V-tolerant data side. Most cheap SPI SD modules include a voltage divider and work fine on 3.3V.

### DS3231 RTC Module (I²C0)

| DS3231 Pin | Pico Pin | GPIO |
|-----------|----------|------|
| VCC | 3V3 OUT (pin 36) | — |
| GND | GND (pin 38) | — |
| SDA | Pin 1 | GP0 (I2C0 SDA) |
| SCL | Pin 2 | GP1 (I2C0 SCL) |

The DS3231 also has a **SQW/INT pin** — wire this to a free GPIO (e.g. GP2, pin 4) if you want the RTC to wake the Pico from dormant mode on a timed interrupt. For this project it's optional (sensor interrupts drive the wake), but useful for a daily "flush buffer to SD" event.

### E18-D80NK IR Proximity Sensors (×2)

The E18-D80NK is an **NPN open-collector output** sensor. Output goes LOW when beam is detected/blocked (active-low). It runs on **5V supply**.

**Power:** The sensor needs 5V. Two options:

- **Option A (recommended):** Add a small step-up/boost module (MT3608, ~AUD $0.50 each on AliExpress) between the TP4056 output and the sensor VCC to generate 5V.
- **Option B (acceptable shortcut):** Many E18-D80NK units work adequately down to ~4.5V. A fresh 18650 at 4.2V is marginal — field-test before relying on it.

**Logic level:** The NPN open-collector output needs a pull-up to 3.3V (not 5V) on the Pico GPIO side. Use a 10 kΩ resistor from the signal wire to 3.3V — this keeps the logic signal within Pico-safe levels.

| E18-D80NK Pin | Connection |
|--------------|-----------|
| Brown (VCC) | 5V (boost module out, or VBUS on USB) |
| Blue (GND) | GND |
| Black (Signal) | 10 kΩ pull-up to 3.3V, then to Pico GPIO |

- **Sensor A (Entry):** Signal → GP14 (pin 19)
- **Sensor B (Exit):** Signal → GP15 (pin 20)

GP14 and GP15 support hardware interrupts, which is what you need for the event-driven firmware.

---

## Complete Wiring Diagram (ASCII)

```
                   PICO MICRO
                ┌─────────────┐
    GP0 (SDA) ──┤ 1       40 ├── VBUS (USB 5V only)
    GP1 (SCL) ──┤ 2       39 ├── VSYS ← TP4056 OUT+
    GP2 (RTC?)──┤ 4       38 ├── GND  ← TP4056 OUT-
                │             │
    GP6  (CS) ──┤ 9       36 ├── 3V3 OUT → SD VCC, DS3231 VCC
    GP7 (MOSI)──┤ 10           │            + pull-up resistors
    GP8  (SCK)──┤ 11           │
    GP9 (MISO)──┤ 12           │
                │             │
   GP14 (SenA)──┤ 19           │
   GP15 (SenB)──┤ 20           │
                └─────────────┘

POWER CHAIN:
18650 → TP4056 → VSYS(pin39) / GND(pin38)
Optional: TP4056 OUT → MT3608 boost → 5V → E18-D80NK VCC

SIGNAL PULL-UPS (for each E18-D80NK):
3V3 ──[10kΩ]──┬── E18 signal wire
              └── GP14 or GP15
```

---

## MicroPython Firmware

```python
from machine import Pin, SPI, I2C, mem32
import utime, sdcard, os

# --- SPI SD Card ---
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(8), mosi=Pin(7), miso=Pin(9))
cs  = Pin(6, Pin.OUT)
sd  = sdcard.SDCard(spi, cs)
os.mount(sd, '/sd')

# --- I2C RTC (DS3231) ---
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)

def get_rtc_time():
    data = i2c.readfrom_mem(0x68, 0x00, 7)
    # decode BCD bytes: sec, min, hr, dow, date, month, year
    return data  # process as needed

# --- IR Sensors with interrupts ---
sensor_a = Pin(14, Pin.IN, Pin.PULL_UP)
sensor_b = Pin(15, Pin.IN, Pin.PULL_UP)

t_entry = None

def on_sensor_a(pin):
    global t_entry
    t_entry = utime.ticks_ms()

def on_sensor_b(pin):
    global t_entry
    if t_entry is not None:
        transit_ms = utime.ticks_diff(utime.ticks_ms(), t_entry)
        transit_s  = transit_ms / 1000
        if 3 <= transit_s <= 900:  # valid window
            classify_and_log(transit_s)
        t_entry = None

sensor_a.irq(trigger=Pin.IRQ_FALLING, handler=on_sensor_a)
sensor_b.irq(trigger=Pin.IRQ_FALLING, handler=on_sensor_b)

def classify_and_log(transit_s):
    if   transit_s < 10:  category = "transit"
    elif transit_s < 60:  category = "slow"
    else:                 category = "dwell"
    ts = get_rtc_time()
    with open('/sd/log.csv', 'a') as f:
        f.write(f"{ts},{transit_s:.1f},{category}\n")

# --- Main loop ---
# For deep dormant sleep between events, use machine.lightsleep()
# MicroPython's Pico port supports GPIO pin interrupts as wake sources.
while True:
    utime.sleep_ms(100)
```

---

## Bill of Materials

| Component | Qty | Source | Est. Cost (AUD) |
|-----------|-----|--------|-----------------|
| Raspberry Pi Pico W | 2 | Core Electronics / Jaycar | ~$15 each |
| E18-D80NK IR proximity sensor | 4 | AliExpress | ~$3 each |
| DS3231 RTC module | 2 | AliExpress | ~$2 each |
| SPI SD card module | 2 | AliExpress | ~$1.50 each |
| 18650 Li-ion cell (3000 mAh) | 2 | AliExpress / local | ~$8 each |
| TP4056 charging module | 2 | AliExpress | ~$0.50 each |
| MT3608 boost converter module | 2 | AliExpress | ~$0.50 each |
| 10 kΩ resistors (×4 per unit) | 1 pack | Jaycar / AliExpress | ~$2 |
| IP65 ABS enclosure | 2 | AliExpress / Jaycar | ~$8 each |
| Cable glands + neutral-cure silicone | 1 pack | Hardware store | ~$5 |
| Micro SD card (32 GB) | 2 | Local / AliExpress | ~$8 each |

**Estimated total (sensor units only):** ~$100–120 AUD depending on sourcing.

> **Critical path note:** Order AliExpress components on Phase 0 Day 1. Allow 3–5 weeks delivery. If delayed past Phase 0 Week 2, source Pico W and sensors from Jaycar (Hobart) or Core Electronics (online) at higher cost but immediate availability. A delivery delay does not affect chalk station build, signage, or WordPress setup.

---

## Component Compatibility Summary

| Component | Interface | Pins Used | Status |
|-----------|-----------|-----------|--------|
| SD card module | SPI0 | GP6, 7, 8, 9 | ✅ |
| DS3231 RTC | I²C0 | GP0, GP1 | ✅ |
| E18-D80NK Sensor A | GPIO IRQ | GP14 | ✅ (with 10 kΩ pull-up) |
| E18-D80NK Sensor B | GPIO IRQ | GP15 | ✅ (with 10 kΩ pull-up) |
| 18650 via TP4056 | Power | VSYS, GND | ✅ |
| 5V boost for sensors | Power | External | ✅ (MT3608 ~$0.50) |

Everything fits with GPIO pins to spare.

---

## Licence

The firmware skeleton and wiring documentation in this appendix are released under the [MIT Licence](https://opensource.org/licenses/MIT). You are free to use, modify, and redistribute for any purpose with attribution.
