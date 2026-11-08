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
| DC bus input | 30 A 58 VDC ATO fuse, SMCJ58A TVS | Overcurrent and overvoltage protection for a 48 V nominal bus |
| DC bus capacitors | 4 × Panasonic EEV-FK2A101M (100 µF, 100 V) | 400 µF in total, sized for 20 A RMS phase current at 20 kHz PWM |
| Power supply | LMR38020 buck, LP38693MP-3.3 regulator | DC bus to 5 V, then 5 V to 3.3 V; a BAT54C diode-OR feeds the 3.3 V regulator from the 5 V rail or USB VBUS, so USB alone can power the 3.3 V logic |
| CAN | ISOW1044 (transceiver with built-in isolated DC/DC) | Isolated, with ACM2012 choke and PESD2CAN ESD protection |
| USB | Micro-B connector, USBLC6-2SC6 | ESD protection on D+ and D- |
| Temperature sensing | 10 kΩ NTC | On the board, plus an input for an external sensor on J2 |
| PCB | — | 4 copper layers, 100 × 100 mm outline |

## Connectors

| Ref | Function |
|---|---|
| J13, J14 | DC bus power pads: VDC_IN (before the fuse) and GND |
| J5, J6, J7 | Motor phase pads: A, B and C |
| J8 | CAN bus: CAN_H, CAN_L, and pin 3 to the isolated ground through 10 Ω |
| J12 | Jumper for the 120 Ω CAN termination: fit it across pins 2 and 3 |
| J2 | 6-pin JST-EH for Hall sensors or an encoder (one at a time): 1 HA/A, 2 HB/B, 3 HC/Z (index), 4 external NTC, 5 +5 V, 6 GND |
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

The schematics use the KiCad 10 format, so open them with KiCad 10 or newer. The PCB file is still in KiCad 7 format and will be redone.

## Open items

- Finish the PCB routing.
- Confirm the PCB stack-up with the intended fabricator.
- The TVS clamp voltage (up to 93.6 V) is above the LMR38020 input limit (85 V absolute maximum).
- Confirm the motor current rating; the bulk capacitors assume 20 A RMS phase current.
- Add one 10 µF and two 100 nF X7R ceramic capacitors near the MOSFETs.

## Licence

Copyright Sezgin Akbayin 2023.

The design files are licensed under the CERN Open Hardware Licence Version 2 - Permissive ([CERN-OHL-P-2.0](LICENSE)). The design is provided without any warranty.

Source location: <https://github.com/Sinan-Akbayin/Motor-Control>

The contents of `BLDC_V_0.1/Libraries/` come from third parties and are not covered by this licence. They remain subject to their own licence terms.
