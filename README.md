# Motor-Control

KiCad hardware design for a three-phase BLDC motor drive, built around an STM32G473 microcontroller and a DRV8350S gate driver.

> **Status:** version 0.1. The schematic is drawn and the parts are placed on the PCB, but routing and the [open items](#open-items) are not finished.

## Hardware overview

| Block | Parts | Notes |
|---|---|---|
| MCU | STM32G473VET6 | LQFP100, 24 MHz crystal |
| Gate driver | DRV8350S | SPI interface, enable and fault lines to the MCU |
| Power stage | 6 × BSC070N10NS5 N-channel MOSFETs | Three half-bridges, 5 Ω gate resistors |
| Current sensing | 3 × AD8418A, 3 × 1.5 mΩ shunts | Shunt between each half-bridge and its motor phase |
| Voltage sensing | 39 kΩ / 2.2 kΩ dividers | DC bus and all three phases |
| DC bus capacitors | 8 × Panasonic EEE-FN1J101V | Bulk capacitors |
| Power supply | LMR38020 buck, AMS1117 regulator | DC bus to 5 V, then 5 V to 3.3 V |
| CAN | ISO1050 transceiver, B0505S-1WR2 DC/DC | Isolated, with ACM2012 choke and PESD2CAN ESD protection |
| USB | Micro-B connector, USBLC6-2SC6 | ESD protection on D+ and D- |
| Temperature sensing | 10 kΩ NTC | On the board, plus an input for an external sensor on J2 |
| PCB | — | 4 copper layers, 100 × 100 mm outline |

## Connectors

| Ref | Function |
|---|---|
| J13, J14 | DC bus power pads: VDC and GND |
| J5, J6, J7 | Motor phase pads: A, B and C |
| J8 | CAN bus: CAN_H, CAN_L, and pin 3 to the isolated ground through 10 Ω |
| J12 | Jumper for the 120 Ω CAN termination: fit it across pins 2 and 3 |
| J2 | Hall sensors A, B, C and the external temperature input |
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
| Gate driver enable, fault | PD15, PE0 |
| Phase current A, B, C | PD13, PD11, PE8 |
| Phase voltage A, B, C | PD14, PD12, PD10 |
| DC bus voltage | PA8 |
| Temperature: board, external | PC3, PB10 |
| Hall sensors A, B, C | PD9, PD8, PB11 |
| CAN: RX, TX | PD0, PD1 |
| USB: D-, D+ | PA11, PA12 |
| SWD: SWDIO, SWCLK, SWO | PA13, PA14, PB3 |
| UART: RX, TX | PC4, PC5 |
| Digital output DO_1 | PB0 |
| I2C: SCL, SDA | PA15, PB7 |
| External SPI: CS, SCK, MISO, MOSI | PA4, PA5, PA6, PA7 |
| LEDs: CAN, process | PD2, PE1 |

## Repository layout

All design files are in [BLDC_V_0.1/](BLDC_V_0.1):

| File | Content |
|---|---|
| `BLDC_V_0.1.kicad_pro` | Main KiCad project file |
| `BLDC_V_0.1.kicad_sch` | Top-level schematic |
| `MCU_STM32.kicad_sch` | MCU, power pins, programming and USB |
| `DRV8350.kicad_sch` | Gate driver, buck converter, bulk capacitors, temperature and voltage measurement |
| `Half-Bridge.kicad_sch` | One half-bridge with its current and voltage sensing, used three times |
| `Communications.kicad_sch` | Connectors, isolated CAN, ESD protection |
| `BLDC_V_0.1.kicad_pcb` | PCB layout |
| `Libraries/` | Third-party symbols, footprints and 3D models |

The files use the KiCad 7 format, so open them with KiCad 7 or newer.

## Open items

- Finish the PCB routing.
- Confirm the PCB stack-up with the intended fabricator.
- Check the 3.3 V rails: the AMS1117 output (`+3V3`) and the MCU supply (`+3.3V`) are separate nets in the schematic.
- Add one 10 µF and two 100 nF X7R ceramic capacitors near the MOSFETs.

## Licence

Copyright Sezgin Akbayin 2023.

The design files are licensed under the CERN Open Hardware Licence Version 2 - Permissive ([CERN-OHL-P-2.0](LICENSE)). The design is provided without any warranty.

Source location: <https://github.com/Sinan-Akbayin/Motor-Control>

The contents of `BLDC_V_0.1/Libraries/` come from third parties and are not covered by this licence. They remain subject to their own licence terms.
