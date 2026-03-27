# Section 6: Budget & Resource Plan

All costs in AUD. AliExpress prices are current listings from the companion spreadsheet (`Palimpsest_Path_Budget.xlsx`); allow for exchange rate variation. The spreadsheet is the live tracking document — update it as procurement proceeds.

---

## 6.1 Procurement Approach

The project is designed for maximum DIY leverage. The project lead holds a soldering iron and basic tools, which eliminates the largest cost variable in electronics prototyping. The two primary build decisions — timber chalk stations and purchased IP65 sensor enclosures — reflect a deliberate trade-off: aesthetic quality on the boardwalk-facing elements (timber, painted to match the environment) versus functional reliability on the electronics-facing elements (rated weatherproof enclosures).

Electronics components are sourced via AliExpress. The primary caveat is lead time: allow 3–5 weeks for delivery from China, which means electronics ordering must happen in the first days of Phase 0, well before Week 1.

The WordPress site (sidewalkcircus.org) is an existing asset with current hosting. If hosting or domain renewal falls within the project period, those costs should be added to Section F of the budget spreadsheet.

---

## 6.2 Budget Summary

The live budget spreadsheet (`Palimpsest_Path_Budget.xlsx`) accompanies this document and is the authoritative cost tracker. The table below provides a narrative summary by category. All unit costs and quantities are editable in the spreadsheet.

> ⚠ **Battery cost note:** The 18650 LiPo cell (LiitoKala HG2) is sold in 2-packs at approximately AUD $18.09, giving a per-cell cost of ~$9.05 — significantly higher than earlier estimates of ~$2.20. The spreadsheet reflects the correct figure. Consider purchasing 2 cells only (1 active + 1 spare per unit) to reduce cost if budget is tight.

### A — Electronics (AliExpress, allow 3–5 weeks delivery)

| Item | Notes | Qty | Unit (AUD) | Total (AUD) | Status |
|------|-------|-----|-----------|-------------|--------|
| Raspberry Pi Pico W (×2) | One per sensor unit. MicroPython firmware. Lower power draw than ESP32; no Wi-Fi needed for this use case. Buy with pins pre-soldered (Pico Micro Welding variant). | 2 | ~$5.44 | ~$10.88 | To order |
| E18-D80NK IR proximity sensors | 2 pairs per unit = 8 sensors total. Outdoor-rated, up to 80cm range. | 8 | ~$3.54 | ~$28.32 | To order |
| SPI MicroSD adapter module | 1 per microcontroller, standard SPI wiring. | 2 | ~$1.64 | ~$3.28 | To order |
| MicroSD cards 8GB Class 10 | Buy 4: 2 active + 2 spares for weekly swap. ⚠ Verify capacity with H2testw on arrival — reviews note fake capacity risk. | 4 | ~$1.71 | ~$6.84 | To order ⚠ |
| DS3231 RTC module | Real-time clock; maintains timestamps after power loss. | 2 | ~$4.11 | ~$8.22 | To order |
| 18650 LiPo battery 3000mAh (LiitoKala HG2) | Sold in 2-packs @ AUD ~$18.09 (= ~$9.05 each). ⚠ Earlier estimates of $2.20/cell were incorrect — actual cost is ~$9.05. Consider 2 cells only (1 active + 1 spare) to reduce cost. | 4 | ~$9.05 | ~$36.20 | To order ⚠ |
| TP4056 battery charge/protect module | Safe charging for 18650 cells. Type-C variant with protection circuit. | 2 | ~$1.46 | ~$2.92 | To order |
| Dupont jumper wires & proto board | For sensor wiring and breadboard prototyping. | 1 | ~$3.32 | ~$3.32 | To order |
| Misc: heat shrink, cable glands, terminal blocks | Weatherproofing and secure connections. Cable glands and terminal blocks may need to be sourced locally (Jaycar/Bunnings). | 1 | ~$5.00 | ~$5.00 | To order |
| **Section A Subtotal** | | | | **~$104.98** | |

### B — Sensor Enclosures (IP65 ABS)

| Item | Notes | Qty | Unit (AUD) | Total (AUD) | Status |
|------|-------|-----|-----------|-------------|--------|
| IP65 ABS weatherproof enclosure 150×100×70mm | One per sensor unit. Select correct size variant at checkout. | 2 | ~$6.00 | ~$12.00 | To order |
| Stainless steel hose clamps / mounting brackets | 304 stainless. For secure bannister attachment. Select 40mm range variant. | 4 | ~$3.25 | ~$13.00 | To order |
| Silicone sealant — neutral cure | For cable entry weatherproofing. Do NOT use acid-cure (corrodes electronics). Available at Bunnings. | 1 | ~$6.00 | ~$6.00 | Hardware store |
| **Section B Subtotal** | | | | **~$31.00** | |

### C — Chalk Stations (timber, self-build)

| Item | Notes | Qty | Unit (AUD) | Total (AUD) | Status |
|------|-------|-----|-----------|-------------|--------|
| Treated pine DAR 90×19mm — approx 6 lineal metres | For 2 chalk station boxes (main + spare). Offcuts from timber yard. | 1 | ~$12.00 | ~$12.00 | Hardware store |
| Exterior-grade ply 9mm — 600×600mm sheet | Lid panels. | 1 | ~$8.00 | ~$8.00 | Hardware store |
| Stainless screws, hinges, hasp latch | Stainless for boardwalk/coastal environment. | 1 | ~$9.00 | ~$9.00 | Hardware store |
| Exterior paint or decking oil (small tin) | Weatherproofing — ochre or green to match boardwalk palette. | 1 | ~$12.00 | ~$12.00 | Hardware store |
| Bannister mounting clamps / brackets | For attaching chalk station boxes to bannister rail. | 4 | ~$2.50 | ~$10.00 | Hardware store |
| **Section C Subtotal** | | | | **~$51.00** | |

### D — Chalk & Art Materials

| Item | Notes | Qty | Unit (AUD) | Total (AUD) | Status |
|------|-------|-----|-----------|-------------|--------|
| Calcium carbonate chalk — bulk (blues, greens, ochres, white) | Earth-safe, pH-neutral. 3 bulk packs should cover 8 weeks with high engagement. | 3 | ~$8.00 | ~$24.00 | To order |
| Small chalkboard panels for prompt display | One per chalk station, exterior-mounted. | 3 | ~$4.50 | ~$13.50 | To order |
| Chalk marker pens | For writing weekly prompts on chalkboard panels. | 1 | ~$6.00 | ~$6.00 | Hardware store |
| **Section D Subtotal** | | | | **~$43.50** | |

### E — Signage & Print (home print + laminate)

| Item | Notes | Qty | Unit (AUD) | Total (AUD) | Status |
|------|-------|-----|-----------|-------------|--------|
| A4/A5 glossy inkjet photo paper (20 sheets) | For QR code sign printing. | 1 | ~$8.00 | ~$8.00 | Hardware store |
| Laminator pouches A5 — 125 micron (pack of 25) | Minimum 125 micron for outdoor durability. Thicker is better. | 1 | ~$9.00 | ~$9.00 | Hardware store |
| A6 postcard stock for shop/library QR cards | Home print. Plain copy paper is sufficient for indoor display. | 1 | ~$4.00 | ~$4.00 | Hardware store |
| Cable ties for sign mounting | Attaching laminated signs to boardwalk structures. | 1 | ~$2.50 | ~$2.50 | Hardware store |
| **Section E Subtotal** | | | | **~$23.50** | |

### F — Digital Infrastructure (sidewalkcircus.org)

| Item | Notes | Qty | Unit (AUD) | Total (AUD) | Status |
|------|-------|-----|-----------|-------------|--------|
| WordPress hosting | sidewalkcircus.org is an existing asset. Add cost if renewal due during project period. | 1 | $0 | $0 | Existing |
| Domain renewal | Add if renewal falls within project period. | 1 | $0 | $0 | Existing |
| WPForms, QR generation tools | Free tiers are fully sufficient for this project scale. | 1 | $0 | $0 | Free |
| **Section F Subtotal** | | | | **$0** | |

### G — Contingency

| Item | Notes | Qty | Unit (AUD) | Total (AUD) | Status |
|------|-------|-----|-----------|-------------|--------|
| Hardware replacement (sensor failure / weather damage) | Covers one full Pico W unit replacement if needed. | 1 | ~$15.00 | ~$15.00 | Reserve |
| Chalk replenishment (high-engagement weeks) | Extra chalk if participation exceeds expectations. | 1 | ~$8.00 | ~$8.00 | Reserve |
| Signage reprint (lamination failure) | Reprint 2–3 signs if outdoor laminate fails. | 1 | ~$5.00 | ~$5.00 | Reserve |
| **Section G Subtotal** | | | | **~$28.00** | |

### Total

| | |
|-|-|
| **TOTAL PROJECT BUDGET (ESTIMATED)** | **~$281.98** |

> Note: the corrected battery cost (~$9.05/cell vs. the earlier estimate of ~$2.20) increases Section A by approximately $27 relative to earlier figures. The spreadsheet reflects the correct total.

---

## 6.3 Procurement Timeline

The critical path item is AliExpress delivery. Electronics must be ordered on the first day of Phase 0 to guarantee arrival before Week 1.

| When | Section | Action |
|------|---------|--------|
| **Phase 0 Day 1** | A — Electronics | Order all AliExpress items immediately. 3–5 week delivery window means this cannot wait. |
| **Phase 0 Week 1** | B — Enclosures | Order IP65 enclosures. Can come from AliExpress or local electrical supplier. |
| **Phase 0 Week 1** | C — Timber build | Source timber. Build chalk station boxes. Paint/oil and allow to cure (7 days minimum). |
| **Phase 0 Week 2** | D — Chalk | Order chalk. Also available locally at art supply shops if lead time is tight. |
| **Phase 0 Week 2** | E — Signage | Design and print QR signage once sidewalkcircus.org/participate is live. Laminate. |
| **Phase 0 Week 2** | A — Electronics | Assemble and test Pico W sensor units once AliExpress components arrive. Install on boardwalk. |
| **Phase 0 Week 2** | F — Digital | Confirm WordPress hosting status. Build site pages. Test QR codes on multiple devices. |

---

## 6.4 Resource Notes & Cost Reduction Options

- AliExpress prices fluctuate. The budget spreadsheet uses blue-text input cells — update unit costs as you receive actual quotes before ordering.
- Timber offcuts from a local timber yard or salvage source could reduce Section C costs by $10–15.
- If the project attracts co-presenter support from Cygnet Community Arts Council or Huon Valley Arts, chalk and signage costs may be shareable.
- The chalk station build is the most time-intensive item. Allow a full weekend for construction, painting, and curing before testing the mounting on the boardwalk.
- If AliExpress delivery is delayed past the Phase 0 window, Jaycar Electronics (Hobart) or Core Electronics (online, Australian) carry Raspberry Pi Pico W boards and IR sensors at higher cost but with immediate availability. Budget approximately $25–35 AUD per microcontroller unit via local supply vs ~$10 via AliExpress.
- The companion budget spreadsheet (`Palimpsest_Path_Budget.xlsx`) contains all line items with editable quantities and unit costs. Update it as procurement proceeds and use the Status column to track order state.
