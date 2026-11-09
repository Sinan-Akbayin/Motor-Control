# Motor-Control

KiCad hardware design for a three-phase BLDC motor drive, built around an STM32G473 microcontroller and a DRV8350S gate driver.

> **Status:** version 0.2 in progress. The schematic revision is done (ERC: 0 errors). The PCB layout will be redone from scratch, and the [open items](#open-items) are not finished.

## Hardware overview

| Block | Parts | Notes |
|---|---|---|
| MCU | STM32G473VET6 | LQFP100, 24 MHz crystal |
| Gate driver | DRV8350S | SPI interface and enable line to the MCU; nFAULT goes to the TIM8 break input |
| Power stage | 6 × BSC070N10NS5 N-channel MOSFETs | Three half-bridges, 5 Ω gate resistors |
| Current sensing | 4 × AD8418A, 3 × 1.5 mΩ phase shunts, 1 × 1 mΩ DC bus shunt | Phase shunts between each half-bridge and its motor phase; bus shunt on the high side |
| Voltage sensing | 39 kΩ / 2.2 kΩ dividers | DC bus and all three phases |
| DC bus input | 30 A 58 VDC ATO fuse, 5.0SMDJ58A TVS (5 kW) | Overcurrent and overvoltage protection for a 48 V nominal bus |
| DC bus capacitors | 6 × Rubycon 100ZLJ220M12.5X25 (220 µF, 100 V, through-hole) | 1320 µF in total; together they carry about 12 A RMS of ripple current at 20 kHz, enough for 15 A RMS phase current |
| Power supply | LMR38020 buck, AMS1117-3.3 regulator | DC bus to 5 V, then 5 V to 3.3 V; a BAT54C diode-OR feeds the 3.3 V regulator from the 5 V rail or USB VBUS, so USB alone can power the 3.3 V logic (with little voltage margin, see changes.md) |
| CAN | ISO1050 isolated transceiver, B0505S-1WR2 isolated 5 V converter | ACM2012 choke and PESD2CAN ESD protection; a 240 Ω resistor gives the converter its minimum load |
| USB | Micro-B connector, USBLC6-2SC6 | ESD protection on D+ and D- |
| Temperature sensing | 10 kΩ NTC | On the board, plus an input for an external sensor on J2 |
| PCB | — | 4 copper layers, 100 × 100 mm outline |

## Theoretical specifications

These values are calculated from datasheets. They have not been measured on a board yet. The design point is a 48 V bus, 20 kHz PWM, 40 °C ambient air and a MOSFET junction temperature of at most 110 °C.

| Parameter | Value | What limits it |
|---|---|---|
| Nominal input voltage | 48 V (13-cell Li-ion pack, 54.6 V when fully charged) | — |
| Input voltage range | 9 V to 58 V | Low end: DRV8350S supply, 9 V minimum. High end: the 58 V stand-off voltage of the TVS diode D4; above about 64 V the TVS starts to conduct |
| Absolute maximum bus voltage | 80 V, short transients only | DRV8350S VM pin (80 V absolute maximum) and AD8418A inputs (80 V survival). These are damage limits, not operating limits: the DRV8350S is specified up to 75 V and the AD8418A up to 70 V. At 80 V the bus voltage divider would also put 4.27 V on the MCU pin, above its 3.3 V supply |
| Continuous phase current | 15 A RMS without a heatsink (estimate, to be confirmed by a thermal test) | MOSFET heating: about 1.4 W per MOSFET with 50 K/W junction-to-air. The datasheet gives 50 K/W for a single MOSFET on a test board with 6 cm² of copper; six MOSFETs close together on this board may run hotter |
| Continuous phase current with a heatsink | about 18 A RMS | DC bus capacitor ripple current: 6 × 2.21 A at 100 kHz, about 12.2 A at 20 kHz |
| Peak phase current (short pulses) | ±50 A | Range of the phase current measurement. ±50 A gives 0.15 V to 3.15 V at the ADC; the firmware sets the over-current trip below this |
| DC input current | about 17 A at 15 A RMS phase current | 30 A fuse |
| Output power | about 0.8 kW at 48 V and 15 A RMS | Assumes space-vector PWM at full modulation, a power factor of 0.9, and no losses. With plain sine PWM it is about 0.7 kW |
| PWM frequency | 20 kHz (design point used for the numbers above) | Higher frequencies raise MOSFET switching losses |
| Phase current measurement | 30 mV/A, 1.65 V at 0 A, range about ±53 A | 1.5 mΩ shunt × AD8418A gain of 20. The ideal range is ±55 A (0 V to 3.3 V); the amplifier output cannot reach the supply rails exactly |
| DC bus current measurement | 20 mV/A, 1.65 V at 0 A, range about ±80 A | 1 mΩ shunt × AD8418A gain of 20 (ideal ±82.5 A) |
| DC bus voltage measurement | 0 V to 61.8 V for 0 V to 3.3 V at the ADC | 39 kΩ / 2.2 kΩ divider |
| Overvoltage clamp | about 80 V or less for surge currents up to about 21 A (estimate) | 5.0SMDJ58A: 93.6 V at 53.5 A (distributor data). The datasheet guarantees only the 93.6 V point |
| Interfaces | Isolated CAN, USB, UART, I2C, SPI, SWD, Hall sensors or encoder | — |

How the main numbers were found:

- **MOSFET heating.** BSC070N10NS5 on-resistance is at most 7.0 mΩ at 25 °C. At about 110 °C it is taken as 1.6 times higher, 11.2 mΩ (an estimate; read the exact factor from the datasheet curve). In a half-bridge, each MOSFET conducts about half of the time. At 15 A RMS one MOSFET loses 15² × 0.0112 / 2 = 1.26 W in conduction and about 0.15 W in switching (assuming 50 ns per switching edge; the real value depends on the gate drive current set in the DRV8350S). 1.4 W × 50 K/W = 70 K, so the junction reaches 40 + 70 = 110 °C.
- **Capacitor ripple.** In a three-phase inverter, the RMS ripple current in the DC bus capacitors can reach about 0.65 times the RMS phase current. At 15 A this is 9.8 A. Each capacitor is rated 2.21 A at 100 kHz and 105 °C (Rubycon ZLJ datasheet). At 20 kHz the rating is about 8 % lower, so six capacitors carry 6 × 2.21 × 0.92 ≈ 12.2 A.
- **TVS clamp.** At its rated pulse (53.5 A) the 5.0SMDJ58A clamps at 93.6 V. Its breakdown voltage is at most 71.2 V, so its dynamic resistance is about (93.6 − 71.2) / 53.5 ≈ 0.42 Ω. The clamp stays at or below 80 V while the surge current is at most (80 − 71.2) / 0.42 ≈ 21 A. This is a straight-line estimate; check it against the surge waveform expected in use.

## Connectors

| Ref | Function |
|---|---|
| J13, J14 | DC bus power pads: VDC_IN (before the fuse) and GND |
| J5, J6, J7 | Motor phase pads: A, B and C |
| J8 | CAN bus: CAN_H, CAN_L, and pin 3 to the isolated ground through 10 Ω |
| J12 | Jumper for the 120 Ω CAN termination: fit it across pins 2 and 3 |
| J2 | 6-pin JST-EH for Hall sensors or an encoder (one at a time): 1 +5 V, 2 HA/A, 3 HB/B, 4 HC/Z (index), 5 external NTC, 6 GND |
| J3 | 10-pin SWD header with SWO and NRST |
| J4 | USB Micro-B |
| J1 | BOOT0 selection |
| J9 | UART, digital output DO_1 |
| J10 | I2C |
| J11 | External SPI |

## MCU pins

| Function | Pins |
|---|---|
| Gate driver high-side inputs A, B, C | PC6, PC7, PC8 |
| Gate driver low-side inputs A, B, C | PC10, PC11, PC12 |
| Gate driver SPI: CS, SCK, MISO, MOSI | PB12, PB13, PB14, PB15 |
| Gate driver enable, fault | PD15, PB7 (TIM8_BKIN) |
| Phase current A, B, C | PA1, PA3, PE7 (fast ADC channels, COMP1/2/4 inputs) |
| DC bus current | PA0 (fast ADC channel, COMP3 input) |
| Phase voltage A, B, C | PE14, PE15, PE13 |
| DC bus voltage | PA8 |
| Temperature: board, external | PC3, PC0 |
| Hall sensors / encoder A, B, C(Z) | PE2, PE3, PE4 (TIM3 CH1–CH3); C(Z) also on PD2 (TIM3_ETR) |
| CAN: RX, TX | PD0, PD1 |
| USB: D-, D+ | PA11, PA12 |
| SWD: SWDIO, SWCLK, SWO | PA13, PA14, PB3 |
| UART: RX, TX | PC4, PC5 |
| Digital output DO_1 | PB0 |
| I2C: SCL, SDA | PA15, PB9 |
| External SPI: CS, SCK, MISO, MOSI | PA4, PA5, PA6, PA7 |
| LEDs: CAN, process | PE5, PE1 |

## Repository layout

All design files are in [BLDC_V_0.1/](BLDC_V_0.1):

| File | Content |
|---|---|
| `BLDC_V_0.1.kicad_pro` | Main KiCad project file |
| `BLDC_V_0.1.kicad_sch` | Top-level schematic |
| `MCU_STM32.kicad_sch` | MCU, power pins, programming and USB |
| `DRV8350.kicad_sch` | Gate driver, buck converter, bulk capacitors, temperature and voltage measurement |
| `DC_Bus.kicad_sch` | DC bus input: fuse, TVS, bus current shunt and amplifier |
| `Half-Bridge.kicad_sch` | One half-bridge with its current and voltage sensing, used three times |
| `Communications.kicad_sch` | Connectors, isolated CAN, ESD protection |
| `BLDC_V_0.1.kicad_pcb` | PCB layout |
| `Libraries/` | Third-party symbols, footprints and 3D models |
| `BLDC_Project.pretty/` | Project footprint library: the 10 × 10 mm power pads |

The schematics use the KiCad 10 format, so open them with KiCad 10 or newer. The PCB file is still in KiCad 7 format and will be redone.

[changes.md](changes.md), in the repository root, lists every change made since the upstream design and the reason for each one.

## Open items

- Finish the PCB routing.
- Confirm the PCB stack-up with the intended fabricator.
- Check the TVS, MOSFET and capacitor numbers against the manufacturers' current datasheets. Some values in the specifications above come from distributor listings; each one is marked there.
- The TVS cannot absorb braking energy. If the battery is disconnected while the motor brakes, the bus voltage rises, so the firmware must limit or stop braking when the bus voltage gets too high.
- Add one 10 µF and two 100 nF X7R ceramic capacitors near the MOSFETs.

## Licence

Copyright Sezgin Akbayin 2023.

The design files are licensed under the CERN Open Hardware Licence Version 2 - Permissive ([CERN-OHL-P-2.0](LICENSE)). The design is provided without any warranty.

Source location: <https://github.com/Sinan-Akbayin/Motor-Control>

The contents of `BLDC_V_0.1/Libraries/` come from third parties and are not covered by this licence. They remain subject to their own licence terms.
