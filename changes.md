# Changes in version 0.2

This file lists every change made to the design since the upstream state
(`develop` @ 9ee8c38, <https://github.com/Sinan-Akbayin/Motor-Control>).
It is the basis for the pull request description. Each entry says what changed and why.

Status: work in progress. Entries are added as each step is finished.

## Project and libraries

- Schematic files saved in the KiCad 10 format. Open them with KiCad 10 or newer.
- U9 (LMR38020 buck) footprint linked to `Package_SO:TI_SO-PowerPAD-8_ThermalVias` (the old footprint library was missing).
- New project footprint library `BLDC_Project.pretty` with `Power_Welding_Pad_10x10mm`, used by the power pads J5, J6, J7, J13 and J14.
- L6 (CAN choke), CR2 (CAN ESD) and J8 (CAN connector) linked to the registered vendor libraries.
- Removed symbol instance data left over from two other projects (`STM32F4_REV2`, `CAN_2x_485`). It blocked editing; the netlist did not change.
- `.gitignore`: KiCad lock files (`*.lck`), local history (`.history/`) and recovered sheets (`*.recovered.*`) are ignored. The tracked autosave sheets and lock files were removed.

## Power supply

- **3.3 V rail fixed.** The MCU, the CAN transceiver supply and the pull-ups were on net `+3.3V`, while the regulator output was on `+3V3`. The two nets were not connected, so the MCU had no supply. All of them are now on one `+3.3V` net.
- **Buck feedback fixed.** U9 FB was connected only to C49; the R36/R37 divider was not on FB, so the regulator ran without feedback. FB now goes to the divider: Vout = 1.0 V × (1 + 40.2 kΩ / 10 kΩ) = 5.02 V.
- **USB VBUS no longer tied to +5V.** VBUS was hard-wired to the buck output, so the board could drive current back into the USB host. VBUS is now its own net. A BAT54C diode-OR (D5) feeds the 3.3 V regulator input (`LDO_IN`) from either +5V or VBUS, so USB alone can power the 3.3 V logic for programming.
- **3.3 V regulator U3 (AMS1117).** The generic `AMS1117` symbol was replaced by the fixed-output `AMS1117-3.3` symbol (same SOT-223 footprint). The output capacitor C17 changed from 4.7 µF ceramic (0603) to 22 µF solid tantalum (case B, 10 V, AVX TAJB226K010RNJ). The AMS1117 datasheet (Application Hints, Stability) states that 22 µF solid tantalum on the output keeps the regulator stable under all operating conditions.
- **Known limitation: AMS1117 dropout.** The AMS1117 needs up to 1.3 V between input and output, so its input must be at least 3.3 V + 1.3 V = 4.6 V. Its input comes from +5V or VBUS through the BAT54C diode D5, which drops up to 0.5 V at 30 mA and 0.8 V at 100 mA (Diodes DS11005). In the worst case the input is therefore 4.2–4.5 V, and the 3.3 V rail can sag. With typical values the margin is about 0.25 V.
- **Analog supply.** The `WREF+` labels were replaced by the `+3.3VA` net. The 39 nH inductor L1 between +3.3V and +3.3VA was replaced by a ferrite bead (BLM18PG221SN1D).
- **Reset.** Added a 100 nF capacitor (C66) on NRST.
- J4 (USB Micro-B) now uses the standard KiCad symbol; the shield is connected to GND.

- **Supply nets drawn with power symbols instead of labels.** VBUS uses the standard `power:VBUS` symbol. LDO_IN and 5V_ISO use `power:VCC` and VDC_IN and VDC_F use `power:VDC`, each with its Value set to the net name (since KiCad 7, the Value of a power symbol sets the net name). Supply nets now look the same on every sheet, and the names are global, so the sheet prefix is gone (`/MCU_STM32/VBUS` → `VBUS`). Connections did not change; the netlist was compared before and after.
- **The isolated CAN rail was renamed from `5V_ISO_CAN` to `5V_ISO`.**
- PWR_FLAGs were added on VDC_IN and VDC_F. Power symbols are power inputs, and these nets are fed through passive parts (the J13 pad and the F1 fuse), so ERC needs the flag to know where the power comes from.
- **Symbol orientation.** Every ground symbol now points down and every supply symbol points up, on all sheets. Six symbols were turned or moved (four on the Communications sheet, two on the MCU sheet). Connections did not change; the netlist was compared before and after.

## Gate driver (DRV8350S)

- Added pull-ups to +3.3V on the open-drain outputs: R38 10 kΩ on nFAULT and R39 4.7 kΩ on SDO (SPI_MISO). Both outputs are open-drain and need a pull-up (DRV8350 datasheet SLVSDY6A, p. 41 and Table 21).

## MCU pin assignment (STM32G473VET6)

Pins were reassigned so that the motor-control peripherals of the STM32G4 can be used (checked against datasheet DS12712, Table 12):

| Signal | Old | New | Reason |
|---|---|---|---|
| CURR_A, CURR_B, CURR_C | slow ADC channels | PA1, PA3, PE7 | Fast ADC channels and comparator inputs (COMP1, COMP2, COMP4) for over-current trips |
| I_DC (new) | — | PA0 | DC bus current, fast ADC channel and COMP3 input |
| TEMP_IN | PB10 | PC0 | PB10 has no ADC input |
| FAULT_N | — | PB7 | TIM8 break input: a driver fault stops the PWM in hardware |
| HALL_A/B/C (encoder A/B/Z) | — | PE2, PE3, PE4 (TIM3 CH1–CH3); HALL_C also on PD2 (TIM3_ETR) | One timer reads either Hall sensors or a quadrature encoder with index |
| SENS_A, SENS_B, SENS_C | — | PE14, PE15, PE13 | Phase voltage inputs on ADC3/ADC4 |
| I2C_SDA | PB7 | PB9 | PB7 is now the break input |
| CAN_LED | — | PE5 | Freed pin |

The old pins are marked as not connected.

## Isolated CAN

- **C46/C47 on CAN_H/CAN_L: 100 nF → 100 pF (0603, 50 V, C0G).** The two capacitors go from each bus line to ground, so between CAN_H and CAN_L they act as half their value in series. With 100 nF each, the 60 Ω bus load gives a time constant of about 60 Ω × 50 nF = 3 µs. One bit at 1 Mbit/s lasts 1 µs, so the edges could not settle. 100 pF keeps the EMI filtering and adds only about 3 ns. The old Comment field also disagreed with the value (it said 10 nF, 16 V).
- **ERC: PWR_FLAG added on the two ISO1050 (U11) supply nets.** VCC1 is fed through L2, a TDK MMZ2012Y202B ferrite bead (0.5 Ω DC resistance, drawn with a resistor symbol) and VCC2 by the B0505S isolated converter U8. KiCad cannot see a power source through these parts, so it reported two "power pin not driven" errors. The flags remove those false errors. The connections did not change.
- **New R41, 240 Ω (1206) from 5V_ISO to GND1: minimum load for the isolated converter U8 (B0505S-1WR2).** U8 is unregulated and needs at least 10 % of its rated load (20 mA). Below that, its output voltage is not specified (Mornsun B_S-1WR2 datasheet, Design Reference §3). When the CAN bus is idle, ISO1050 draws only 8–12 mA (TI SLLS983L, §6.5). R41 adds 5 V / 240 Ω = 20.8 mA and dissipates 0.10 W. At 10 % load the U8 output is 5.25 V typical and 5.5 V worst case (datasheet regulation curve, page 3). ISO1050 VCC2 is specified for 4.75–5.25 V (§6.3), with an absolute maximum of 6 V (§6.1). So the worst case stays below the absolute maximum, but not inside the recommended range.

## Indicators

- The CAN LED (D3) had its cathode resistor R28 tied to +3.3V, so it could never light. R28 now goes to GND.

## Hall sensor / encoder connector

- J2 had no +5V or GND pin, so Hall sensors could not be powered. J2 is now a 6-pin JST-EH (S6B) shared by Hall sensors and an encoder (only one is fitted at a time).
- J2 pin order: 1 +5V, 2 HA/A, 3 HB/B, 4 HC/Z (index), 5 external NTC, 6 GND. The supply is on the first pin and ground on the last, as on the other connectors of the board.
- Series resistors R30–R32 changed from 0 Ω to 100 Ω to limit current into the MCU pins.

## DC bus (new sheet `DC_Bus.kicad_sch`)

- Input protection: J13 (VDC_IN pad) → F1 30 A 58 VDC ATO blade fuse (Optifuse APR58-30A) → D4 TVS → bus.
- DC bus current sensing: R40 1 mΩ 2512 shunt on the high side and U10 AD8418A amplifier to the MCU (I_DC, PA0). REF1 = +3.3VA and REF2 = GND give a bidirectional output of 20 mV/A around mid-scale.
- Bulk capacitors: 8 × EEE-FN1J101V (63 V) replaced by 4 × Panasonic EEV-FK2A101M (100 µF, 100 V). 63 V capacitors are not safe on a 48 V bus that reaches 54.6 V when fully charged, plus transients.
- **Bulk capacitors changed again (they are on the DRV8350 sheet), to 6 × Rubycon 100ZLJ220M12.5X25 (220 µF, 100 V, Ø12.5 × 25 mm, through-hole).** The four EEV-FK2A101M could carry only about 3.2 A of ripple current in total (793 mA each, distributor data). The ripple current in the DC bus capacitors of a three-phase inverter reaches about 0.65 times the phase current, so they limited the board to about 5 A RMS per phase. The six ZLJ capacitors are rated 2.21 A each at 100 kHz and 105 °C (Rubycon ZLJ datasheet), about 12.2 A in total at 20 kHz. That covers the 9.8 A needed at the 15 A RMS target. C2, C4, C51 and C52 changed part; C68 and C69 are new. The capacitors now use the standard `Device:C_Polarized` symbol. The old symbol had pins named `+` and `-`, which did not match the pad numbers 1 and 2 of the footprint.
- **TVS D4: SMCJ58A → 5.0SMDJ58A (same SMC package and footprint).** The weakest parts on the bus have an absolute maximum of 80 V: the DRV8350S VM pin (TI SLVSDY6A, §7.1) and the AD8418A inputs (80 V survival, ADI datasheet Rev. E). The LMR38020 is rated 85 V (TI SNVSC40E, §7.1). Both diodes clamp at 93.6 V at their rated pulse current, but the larger one has a lower dynamic resistance. The SMCJ58A stays at or below 80 V only up to about 6 A; the 5.0SMDJ58A does so up to about 21 A (distributor data, to be checked against the Littelfuse datasheet).

## Ratings

- Theoretical specifications (voltage range, continuous and peak current, measurement ranges) were calculated and added to the README. The board is rated 15 A RMS per phase without a heatsink, limited by MOSFET heating. This is an estimate until a thermal test confirms it.

## Part numbers

- MPN fields added for L1, D4, D5, F1, U10 and the bulk capacitors.
