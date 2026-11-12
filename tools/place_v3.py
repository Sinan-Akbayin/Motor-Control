"""Placement v3 for BLDC_V_0.1 = placement v2 with the control section re-planned around the MCU pins.

usage (KiCad's bundled Python, KiCad closed or on a copy):
  python place_v3.py place <in.kicad_pcb> <out.kicad_pcb>
  python place_v3.py check <board.kicad_pcb> [ref.kicad_pcb]

Why v3 (see docs/WORK.md, step 11b3). STM32G473 LQFP100 pin groups, by package side:
  side 1 (pins 1-25):   HALL, HSE, NRST, TEMP, I_DC, CURR_A, CURR_B
  side 2 (pins 26-50):  EXT_SPI, UART, DO, CURR_C, SENS_C/A/B
  side 3 (pins 51-75):  DRV SPI, DRV_ENABLE, INHx, SENS_VDC, USB
  side 4 (pins 76-100): SWD, I2C, INLx, CAN, FAULT, BOOT0, LEDs
v2 used MCU rotation 270 (side 1 north, side 2 west): every analog pin faced away from the power
stage and USB faced away from its connector. v3 uses rotation 0: side 1 west, side 2 south (analog
toward the power band), side 3 east (DRV, USB), side 4 north (SWD, I2C, CAN).

Unchanged from v2: board outline, power band (bridges, bulk caps, pads), input column, DRV8350S
cluster, buck cluster, isolated CAN cluster, mounting holes, J1, J2, J8, J11, U3.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_v2 as v2  # noqa: E402

MCU_C = (127.5, 120.0)
MCU_ROT = 0
J10_X, J9_X = 110.64, 129.54        # swapped: HALL connector above the MCU's west side (pins 1-3)
PHASE_PAD_X = (137.1, 149.4, 161.7)  # J5, J6, J7
LDO_DX = 2.5                       # LDO group moved east: keeps x 138.3..142.5 free for INLx/FAULT


def build_table():
    v2.MCU_C, v2.MCU_ROT = MCU_C, MCU_ROT
    t = _v2_table()
    # connectors: HALL/ENC left, EXT_SPI right (reached on B.Cu from MCU side 2; JST pins are THT)
    t['J10'] = (J10_X, v2.CONN_Y, 0)
    t['J9'] = (J9_X, v2.CONN_Y, 0)
    # hall / temp input filters under J10, same arrangement as v2 relative to the connector
    x0 = J10_X + 4.26
    for i, r in enumerate(['R35', 'C57', 'R36', 'C58', 'R37', 'C59']):
        t[r] = (x0 + 1.45 * i, 103.6, 90)
    for i, r in enumerate(['R32', 'R33', 'R34', 'R31']):
        t[r] = (x0 + 1.8 * i, 107.2, 90)
    t['C55'] = (x0 + 6.95, 107.2, 90)
    # LDO group east of the MCU->DRV corridor
    t.update({'U2': (146.0 + LDO_DX, 116.0, 0), 'C4': (140.8 + LDO_DX, 116.0, 90),
              'C8': (147.5, 122.0, 0), 'D2': (152.2, 122.0, 0)})
    # boot jumper out of the space north of the DRV8350S control pins (BOOT0 is a static level)
    t.update({'J3': (155.0, 125.3, 0), 'R3': (158.0, 125.3, 90)})
    # LEDs in one row under J9, north of the MCU; leaves y 104..111 free for the side-4 fan-out
    # resistor left of its LED: resistor pad 2 and LED pad 1 (cathode net) face each other
    for r, x in (('R30', 124.5), ('D4', 127.9), ('R2', 130.8), ('D1', 133.7), ('R4', 136.6), ('D3', 139.5)):
        t[r] = (x, 103.0, 0)
    # SENS_VDC divider south-east of the MCU, between its bypass caps and bulk cap C31
    t.update({'R13': (136.5, 134.6, 0), 'R14': (136.5, 136.4, 0), 'C36': (133.5, 135.5, 0)})
    # bottom edge (user 2026-11-11): supply group VDC_IN, GND | mounting hole H3 | motor group A, B, C
    # at one pitch (12.3 mm, the same as VDC_IN -> GND). H3 sits in the gap between the two groups.
    t.update({'J5': (PHASE_PAD_X[0], v2.PAD_Y, 0), 'J6': (PHASE_PAD_X[1], v2.PAD_Y, 0),
              'J7': (PHASE_PAD_X[2], v2.PAD_Y, 0), 'H3': (127.95, 171.0, 0)})
    return t


_v2_table = v2.build_table
v2.build_table = build_table

if __name__ == '__main__':
    if sys.argv[1] == 'place':
        v2.place(sys.argv[2], sys.argv[3])
    else:
        v2.check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
