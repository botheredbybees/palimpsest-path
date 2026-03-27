# config.py — Palimpsest Path sensor node configuration
# ──────────────────────────────────────────────────────────────────────────────
# Copy this file to the Pico alongside main.py.
# The ONLY constant you must change between units is UNIT_ID below.
# All other constants match the wiring in docs/technical-appendix.md.
# ──────────────────────────────────────────────────────────────────────────────

# ── Unit identity ─────────────────────────────────────────────────────────────
# Set to "UNIT_A" for the entry end of the boardwalk gallery.
# Set to "UNIT_B" for the exit end.
UNIT_ID = "UNIT_A"

# ── I²C — DS3231 RTC ──────────────────────────────────────────────────────────
# The DS3231's I²C address is hardware-fixed at 0x68 on all chips.
# There is no address-select pin; you cannot change it.
I2C_BUS     = 0        # I²C0 peripheral
I2C_SDA     = 0        # GP0, pin 1
I2C_SCL     = 1        # GP1, pin 2
DS3231_ADDR = 0x68     # fixed — do not change

# ── SPI — SD card ─────────────────────────────────────────────────────────────
# Initialise at 1 MHz; the sdcard driver may renegotiate higher after mount.
# SPI0 pins match the wiring table in docs/technical-appendix.md.
SPI_BUS  = 0           # SPI0 peripheral
SPI_SCK  = 8           # GP8,  pin 11
SPI_MOSI = 7           # GP7,  pin 10
SPI_MISO = 9           # GP9,  pin 12
SD_CS    = 6           # GP6,  pin 9  (chip select, active-low)
SD_MOUNT = "/sd"       # VFS mount point

# ── IR sensors (E18-D80NK, NPN open-collector) ────────────────────────────────
# External 10 kΩ pull-ups to 3.3 V are fitted on the PCB.
# Do NOT enable internal pull-ups in firmware — they would fight the external
# resistors and alter the intended impedance.
#
# Physical orientation requirement:
#   SENSOR_1_PIN = the sensor closest to the *outside* (street / public approach)
#   SENSOR_2_PIN = the sensor closest to the *gallery interior*
#
# A person walking INTO the gallery triggers sensor 1 first, then sensor 2.
# A person walking OUT triggers sensor 2 first, then sensor 1.
# Direction is inferred from which pin falls first (see SEQUENCE_WINDOW_MS).
SENSOR_1_PIN = 14      # GP14, pin 19 — outer / entry-facing
SENSOR_2_PIN = 15      # GP15, pin 20 — inner / gallery-facing

# ── Timing thresholds ─────────────────────────────────────────────────────────
# DEBOUNCE_MS: ignore re-triggers within this window after a falling edge.
# The E18-D80NK has ~10 ms hardware response time; 50 ms adds a software guard.
DEBOUNCE_MS = 50

# SEQUENCE_WINDOW_MS: max gap between the two sensors' falling edges to be
# treated as a single directional pass. 2000 ms ≈ a very slow walker covering
# the ~0.3–0.5 m sensor spacing. Widen if direction reads "unknown" too often.
SEQUENCE_WINDOW_MS = 2_000

# MIN_TRANSIT_MS: discard beam-break events shorter than this. Filters leaves,
# insects, and electrical noise spikes.
MIN_TRANSIT_MS = 50

# MAX_TRANSIT_MS: discard events longer than this (person leaning on the post,
# sensor obstructed by debris). 30 s is generous but avoids false state-lock.
MAX_TRANSIT_MS = 30_000

# ── CSV layout ────────────────────────────────────────────────────────────────
CSV_HEADER = "timestamp,unit_id,direction,beam,transit_ms"

# ── RAM fallback buffer ───────────────────────────────────────────────────────
# Rows are buffered here when the SD card is unavailable.
# At ~80 bytes per row, 100 rows ≈ 8 KB — well within the Pico's 264 KB SRAM.
RAM_BUFFER_MAX = 100

# ── LED error codes (number of blinks on GP25 onboard LED) ───────────────────
LED_PIN          = 25  # GP25 — onboard LED on standard Pico
LED_ERR_RTC      = 2   # 2 blinks: RTC read failed (timestamp logged as empty)
LED_ERR_SD_WRITE = 3   # 3 blinks: SD write failed (row buffered to RAM)
LED_ERR_SD_MOUNT = 5   # 5 blinks: SD card failed to mount on boot
