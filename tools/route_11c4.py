"""Step 11c4 for BLDC_V_0.1: the remaining nets on top of the 11c3 copper, by explicit coordinates.

usage (KiCad's bundled Python, KiCad closed or on a copy):
  python route_11c4.py <route_11c3.kicad_pcb> <out.kicad_pcb>

No autorouter (user 2026-11-11). Nothing is removed; tracks and vias are added, R1 is turned 180 deg
in place, zones are refilled. All coordinates are board mm (x right, y down).

MCU U1 (LQFP100, centre 127.5,120): west pins 1-25 at x 119.75, y 114.0 + 0.5*(n-1); south pins
26-50 at y 127.75, x 121.5 + 0.5*(n-26); east pins 51-75 at x 135.25, y 126.0 - 0.5*(n-51); north
pins 76-100 at y 112.25, x 133.5 - 0.5*(n-76). Pads are 1.19 long: inner end 0.595 inside.
F.Cu under the MCU body is free, so a pin that cannot leave outward goes to a via under the body.

Done in this file
  batch A  north-west of the MCU: LED cathodes, J10 -> hall series resistors, HALL_A/B/C, TEMP_IN,
           CAN_LED, HSE crystal
  batch B  DRV bus (SPI, INHx, INLx, DRV_ENABLE, FAULT_N)
  batch C  south pins, NRST, BOOT0, PCB_TEMP + R11, north-pin bus (PROCCESS_LED, I2C, CAN), SWD, USB, VBUS
  (the plan below is the original one; batch D = supplies, GND vias, isolated CAN side, buck feedback)

Plan for the rest (not drawn yet)
  DRV bus  The MCU and U5 pin orders are mirror images, so the 12 nets cannot share one layer.
           F.Cu keeps CS, SCK, MOSI. INHA/B/C and DRV_ENABLE run east on F.Cu to "entry" vias north
           of that bundle, drop south on B.Cu and come up at "exit" vias. INLA/B/C and FAULT_N go
           to a via under the MCU body and reach the exit vias on B.Cu. MISO needs a B.Cu hop over
           MOSI and a branch to R5. B.Cu is only free east of x 142.2 and north of y 131.8 there
           (CURR_C / SENS_C lanes). Exit vias, two rows: LC (143.0,130.8) HC (143.8,130.0)
           LB (144.6,130.8) HB (145.4,130.0) LA (146.2,130.8) HA (147.0,130.0) EN (147.8,130.8);
           F.Cu stubs: lanes x 143.8/144.2/144.6/145.0 into U5 pins 28..25, straight into 24..22.
           FAULT_N: pin 17 -> north -> east -> R6 pad 2 as a loop that encloses R5; MISO reaches
           R5 pad 2 through its own via (153.0,131.3) and pin 18 through a via at (149.6,131.2).
  SENS_VDC the 11c3 F.Cu track along x 138.9 walls off the east pins: replace it with a stub under
           the body (pin 69 west along y 117.0 to a via at 126.6,117.0), B.Cu south along x 126.6,
           east along y 130.4, via (135.7,132.0), F.Cu down to R13 pad 1
  under-body vias also for NRST (pin 14), PCB_TEMP (pin 18), BOOT0, I2C_SDA, PROCCESS_LED
  then     south pins (EXT_SPI, UART, DO_1), SWD, USB, I2C_SCL, CAN_RX/TX, buck feedback, LDO,
           isolated CAN side, +3.3VA and +5V branches, GND / +3.3V vias, F.Cu GND pour north of
           y 133 (not on the isolated side) as the last step
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_11c2 import Board  # noqa: E402

W = 0.25          # signal track
WP = 0.2          # at 0.5 mm pitch pins and between 0402/0603 pads


def leds(B):
    # series resistor pad 2 -> LED cathode, neighbours in the row under J9
    for net, x1, x2 in (('Net-(D4-K)', 125.33, 126.96), ('Net-(D1-K)', 131.31, 132.76),
                        ('Net-(D3-K)', 137.11, 138.56)):
        B.track(net, [(x1, 103.0), (x2, 103.0)], W)


def hall(B):
    t, v = B.track, B.via
    # J10 pins 2-4 -> series resistors R35/R36/R37 pad 1 (lanes between the 0402/0603 pads)
    t('Net-(J10-Pin_2)', [(113.14, 99.6), (113.14, 103.6), (113.96, 104.42), (114.9, 104.42)], W)
    t('Net-(J10-Pin_3)', [(115.64, 99.6), (115.64, 100.1), (117.0, 101.46), (117.0, 104.42), (117.8, 104.42)], WP)
    t('Net-(J10-Pin_4)', [(118.14, 99.6), (118.14, 100.1), (119.89, 101.85), (119.89, 104.42), (120.7, 104.42)], WP)
    # filter side: pull-up pad 2 -> filter cap pad 1 -> series resistor pad 2
    t('HALL_A', [(114.9, 106.38), (115.71, 105.57), (115.71, 104.08), (116.35, 104.08)], WP)
    t('HALL_A', [(115.71, 104.08), (115.71, 102.78), (114.9, 102.78)], WP)
    t('HALL_B', [(116.7, 106.38), (116.7, 105.7), (117.0, 105.4), (118.3, 105.4), (118.61, 105.09),
                 (118.61, 104.08), (119.25, 104.08)], WP)
    t('HALL_B', [(118.61, 104.08), (118.61, 102.78), (117.8, 102.78)], WP)
    t('HALL_C', [(118.5, 106.38), (119.0, 105.88), (119.48, 105.4), (121.2, 105.4), (121.51, 105.09),
                 (121.51, 104.08), (122.15, 104.08)], WP)
    t('HALL_C', [(121.51, 104.08), (121.51, 102.78), (120.7, 102.78)], WP)
    # MCU pin 1 (HALL_A): through the gap between C6 and C3, then north-west to R32 pad 2
    t('HALL_A', [(119.75, 114.0), (119.0, 114.0), (118.9, 113.9), (116.45, 113.9), (114.0, 111.45),
                 (114.0, 106.8), (114.42, 106.38), (114.9, 106.38)], WP)
    # MCU pin 2 (HALL_B): same gap, then a B.Cu hop under HALL_A to the lane between R33 and R34
    t('HALL_B', [(119.75, 114.5), (118.85, 114.5), (118.67, 114.32), (115.3, 114.32)], WP)
    v('HALL_B', 115.3, 114.32)
    t('HALL_B', [(115.3, 114.32), (115.3, 112.0), (117.6, 109.7), (117.6, 109.4)], W, 'B')
    v('HALL_B', 117.6, 109.4)
    t('HALL_B', [(117.6, 109.4), (117.6, 107.2), (117.1, 106.7), (116.7, 106.38)], WP)
    # MCU pins 3 and 84 (both HALL_C) joined under the body; B.Cu from a via on that link to the
    # lane between R34 and R31
    # (the link runs south of the under-body vias of FAULT_N / BOOT0, north of the CAN_LED via)
    t('HALL_C', [(119.75, 115.0), (120.7, 115.0), (121.2, 114.8), (122.3, 114.8), (122.8, 115.3), (128.8, 115.3),
                 (129.5, 114.6), (129.5, 112.25)], WP)
    v('HALL_C', 121.2, 114.8)
    t('HALL_C', [(121.2, 114.8), (121.2, 111.5), (119.4, 109.7)], W, 'B')
    v('HALL_C', 119.4, 109.7)
    t('HALL_C', [(119.4, 109.7), (119.4, 107.2), (118.9, 106.7), (118.5, 106.38)], WP)


def temp_in(B):
    t, v = B.track, B.via
    # R31 pad 2 -> C55 pad 1, west of C55's GND pad
    t('TEMP_IN', [(120.3, 106.38), (120.85, 106.38), (121.1, 106.63), (121.1, 107.43), (121.35, 107.68),
                  (121.85, 107.68), (122.9, 107.7)], WP)
    v('TEMP_IN', 122.9, 107.7)
    # B.Cu: north to J10 pin 5 (through-hole), south to a via under the MCU body at pin 15
    t('TEMP_IN', [(120.64, 99.6), (120.64, 100.34), (122.9, 102.6), (122.9, 108.3), (122.2, 109.0),
                  (122.2, 121.0)], W, 'B')
    v('TEMP_IN', 122.2, 121.0)
    t('TEMP_IN', [(119.75, 121.0), (122.2, 121.0)], WP)


def can_led(B):
    t, v = B.track, B.via
    t('CAN_LED', [(119.75, 115.5), (120.6, 115.5), (121.2, 116.1), (123.2, 116.1)], WP)
    v('CAN_LED', 123.2, 116.1)
    # B.Cu straight north next to TEMP_IN to a via south of the LED row, then F.Cu to D4 (the B.Cu
    # corridor x 124.5..125.8 east of it belongs to the EXT_SPI lanes)
    t('CAN_LED', [(123.2, 116.1), (123.6, 115.7), (123.6, 105.6)], W, 'B')
    v('CAN_LED', 123.6, 105.6)
    t('CAN_LED', [(123.6, 105.6), (124.2, 105.0), (128.44, 105.0), (128.84, 104.6), (128.84, 103.0)], W)


def hse(B):
    t = B.track
    # R1 turned 180 deg: HSE_OUT pad now faces the MCU, the crystal-side pad faces Y1 pad 3
    B.b.FindFootprintByReference('R1').SetOrientationDegrees(180)
    t('HSE_IN', [(119.75, 119.5), (118.4, 119.5), (117.9, 119.0), (117.1, 118.95)], WP)
    t('HSE_IN', [(117.1, 118.95), (116.4, 118.4), (115.4, 117.4), (115.12, 117.2), (115.12, 116.9)], WP)
    t('HSE_OUT', [(119.75, 120.0), (118.9, 120.0), (118.45, 120.45), (118.45, 122.25), (118.1, 122.6),
                  (117.11, 122.6)], WP)
    t('Net-(C2-Pad1)', [(116.09, 122.6), (116.09, 122.1), (115.3, 121.3), (114.9, 120.65)], WP)
    t('Net-(C2-Pad1)', [(114.9, 120.65), (112.8, 120.78)], W)


# ------------------------------------------------------------------------------------ batch B
# B.Cu lanes through the gap between the via pairs of C11 and C9 (x 138.05), north to south:
# NRST 115.2, FAULT_N 115.7, BOOT0 116.2, INLA 116.7, INLB 117.2, INLC 117.7, PCB_TEMP 118.2
EXIT = {'INLC': (143.0, 130.2), 'INHC': (143.8, 129.4), 'INLB': (144.6, 130.2), 'INHB': (145.4, 129.4),
        'INLA': (146.2, 130.2), 'INHA': (147.0, 129.4), 'DRV_ENABLE': (147.8, 130.2)}
ENTRY = {'INHC': (143.8, 122.0), 'INHB': (145.4, 123.8), 'INHA': (147.0, 124.6), 'DRV_ENABLE': (147.8, 125.4)}


def drv_bus(B):
    t, v = B.track, B.via
    # --- F.Cu: CS, SCK, MOSI all the way; MISO as far as its via (it has to cross MOSI)
    t('SPI_MOSI', [(135.25, 124.5), (136.4, 124.5), (138.1, 126.2), (146.0, 126.2), (149.45, 129.65),
                   (149.45, 131.4), (148.95, 132.4), (148.95, 133.6)], WP)
    t('SPI_SCK', [(135.25, 125.5), (136.2, 125.5), (138.2, 127.5), (146.65, 127.5), (148.95, 129.8),
                  (148.95, 131.4), (148.45, 132.4), (148.45, 133.6)], WP)
    t('DRV_CS', [(135.25, 126.0), (136.1, 126.0), (138.1, 128.0), (146.5, 128.0), (148.45, 129.95),
                 (148.45, 131.4), (147.95, 132.4), (147.95, 133.6)], WP)
    t('SPI_MISO', [(135.25, 125.0), (136.3, 125.0), (138.15, 126.85), (142.3, 126.85)], WP)
    v('SPI_MISO', 142.3, 126.85)
    # MISO on B.Cu: south between CURR_C and the exit vias, east below them, up east of MOSI,
    # on to a via next to R5 (pull-up)
    t('SPI_MISO', [(142.3, 126.85), (142.3, 130.55), (143.35, 131.6), (153.0, 131.6)], W, 'B')
    v('SPI_MISO', 150.15, 131.6)
    v('SPI_MISO', 153.0, 131.6)
    t('SPI_MISO', [(150.15, 131.6), (149.45, 133.0), (149.45, 133.6)], WP)
    t('SPI_MISO', [(153.0, 131.6), (153.0, 132.99)], WP)

    # --- INHA/B/C, DRV_ENABLE: F.Cu north of the SPI bundle to the entry vias, B.Cu under the bundle
    t('INHC', [(135.25, 118.0), (135.95, 118.0), (136.45, 117.5), (139.3, 117.5), (143.8, 122.0)], WP)
    t('INHB', [(135.25, 118.5), (136.05, 118.5), (136.6, 117.95), (138.85, 117.95), (144.7, 123.8), (145.4, 123.8)], WP)
    t('INHA', [(135.25, 119.0), (136.15, 119.0), (136.75, 118.4), (138.7, 118.4), (144.9, 124.6), (147.0, 124.6)], WP)
    t('DRV_ENABLE', [(135.25, 120.5), (136.2, 120.5), (136.45, 120.75), (140.45, 120.75), (145.1, 125.4),
                     (147.8, 125.4)], WP)
    for net, (x, y) in ENTRY.items():
        v(net, x, y)
        t(net, [(x, y), EXIT[net]], W, 'B')

    # --- INLA/B/C: via under the MCU body, B.Cu through the gap, south in the lanes between the
    # entry vias
    t('INLA', [(132.0, 112.25), (132.0, 113.6), (132.2, 113.8), (132.2, 114.5)], WP)
    t('INLB', [(131.5, 112.25), (131.5, 114.6), (131.3, 114.8), (131.3, 115.4)], WP)
    t('INLC', [(131.0, 112.25), (131.0, 113.6), (130.4, 114.2), (130.4, 116.3)], WP)
    v('INLA', 132.2, 114.5)
    v('INLB', 131.3, 115.4)
    v('INLC', 130.4, 116.3)
    t('INLA', [(132.2, 114.5), (134.4, 116.7), (144.4, 116.7), (146.2, 118.5), EXIT['INLA']], W, 'B')
    t('INLB', [(131.3, 115.4), (133.1, 117.2), (143.3, 117.2), (144.6, 118.5), EXIT['INLB']], W, 'B')
    t('INLC', [(130.4, 116.3), (131.8, 117.7), (142.2, 117.7), (143.0, 118.5), EXIT['INLC']], W, 'B')
    for net, (x, y) in EXIT.items():
        v(net, x, y)

    # --- exit vias -> U5: west pins 28..25 in four lanes, top pins 24..22 straight down
    t('INLC', [(143.0, 130.2), (143.0, 131.2), (143.7, 131.9), (143.7, 135.75), (145.8, 135.75)], WP)
    t('INHC', [(143.8, 129.4), (143.8, 130.6), (144.15, 130.95), (144.15, 135.25), (145.8, 135.25)], WP)
    t('INLB', [(144.6, 130.2), (144.6, 134.75), (145.8, 134.75)], WP)
    t('INHB', [(145.4, 129.4), (145.4, 131.0), (145.1, 131.3), (145.1, 134.25), (145.8, 134.25)], WP)
    t('INLA', [(146.2, 130.2), (146.2, 132.2), (146.45, 132.6), (146.45, 133.6)], WP)
    t('INHA', [(147.0, 129.4), (147.0, 132.2), (146.95, 132.6), (146.95, 133.6)], WP)
    t('DRV_ENABLE', [(147.8, 130.2), (147.8, 131.3), (147.45, 132.0), (147.45, 133.6)], WP)

    # --- FAULT_N: MCU pin 94 -> F.Cu east under the body (over the EXT_SPI / NRST B.Cu lanes) -> via
    # -> B.Cu under the north pins, through the gap, south-east to a via north of R5/R6; F.Cu loop
    # pin 17 -> R6 pad 2 around the MISO vias
    t('FAULT_N', [(124.5, 112.25), (124.5, 113.0), (125.0, 113.5), (128.6, 113.5)], WP)
    v('FAULT_N', 128.6, 113.5)
    t('FAULT_N', [(128.6, 113.5), (129.3, 112.8), (134.65, 112.8), (137.55, 115.7), (148.2, 115.7),
                  (152.0, 119.5), (152.0, 130.3)], W, 'B')
    v('FAULT_N', 152.0, 130.3)
    t('FAULT_N', [(152.0, 130.3), (152.0, 130.9)], WP)
    t('FAULT_N', [(149.95, 133.6), (149.95, 133.0), (150.85, 132.1), (150.85, 131.3), (151.25, 130.9),
                  (153.25, 130.9), (154.6, 132.25), (154.6, 132.99)], WP)


# ------------------------------------------------------------------------------------ batch C
def south_pins(B):
    """MCU south pins 26-32. EXT_SPI: F.Cu north under the body to two via rows, B.Cu straight north
    (x 124.55..125.75) under the north pins to J9, entering the pins from the north side. UART / DO_1:
    F.Cu fan to the north-east, vias, B.Cu west in the band y 122.05..122.85 to J8."""
    t, v = B.track, B.via
    for net, xp, ya, xv, yv, xl, yd, yr, xj in (
            ('EXT_SPI_CS', 121.5, 125.4, 123.0, 120.5, 124.55, 120.15, 97.0, 139.54),
            ('EXT_SPI_SCK', 122.0, 125.5, 123.65, 121.0, 124.95, 120.1, 97.4, 137.04),
            ('EXT_SPI_MISO', 122.5, 125.6, 124.3, 120.5, 125.35, 120.05, 97.8, 134.54),
            ('EXT_SPI_MOSI', 123.0, 125.7, 124.95, 121.0, 125.75, 120.0, 98.2, 132.04)):
        t(net, [(xp, 127.75), (xp, ya), (xv, ya - (xv - xp)), (xv, yv)], WP)
        v(net, xv, yv)
        t(net, [(xv, yv), (xv, yd), (xl, yd - (xl - xv)), (xl, yr + 0.4), (xl + 0.4, yr), (xj - 0.4, yr),
                (xj, yr + 0.4), (xj, 99.6)], WP, 'B')
    # UART_1_RX (pin 30), UART_1_TX (31), DO_1 (32)
    t('UART_1_RX', [(123.5, 127.75), (123.5, 126.1), (124.7, 124.9)], WP)
    v('UART_1_RX', 124.7, 124.9)
    t('UART_1_TX', [(124.0, 127.75), (124.0, 126.575), (124.3, 126.275)], WP)
    v('UART_1_TX', 124.3, 126.275)
    t('DO_1', [(124.5, 127.75), (124.5, 127.05), (125.65, 125.9)], WP)
    v('DO_1', 125.65, 125.9)
    t('DO_1', [(125.65, 125.9), (125.65, 122.6), (125.1, 122.05), (110.65, 122.05), (109.95, 121.35),
               (109.95, 113.0), (109.45, 112.5), (107.4, 112.5)], WP, 'B')
    t('UART_1_RX', [(124.7, 124.9), (124.7, 122.75), (124.4, 122.45), (110.45, 122.45), (109.45, 121.45),
                    (109.45, 115.5), (108.95, 115.0), (107.4, 115.0)], WP, 'B')
    # TX crosses under the RX stub so that the lane order matches the J8 pin order
    t('UART_1_TX', [(124.3, 126.275), (123.4, 126.275), (122.9, 125.775), (122.9, 123.35), (122.4, 122.85),
                    (110.25, 122.85), (108.95, 121.55), (108.95, 117.95), (108.5, 117.5), (107.4, 117.5)], WP, 'B')


def nrst(B):
    t, v = B.track, B.via
    # pin 14 -> via at the pin (B.Cu west to C10) -> F.Cu east under the body, north of the EXT_SPI vias
    t('NRST', [(119.75, 120.5), (120.6, 120.5), (120.95, 120.3), (121.4, 119.85), (127.7, 119.85)], WP)
    v('NRST', 120.95, 120.3)
    v('NRST', 127.7, 119.85)
    t('NRST', [(120.95, 120.3), (114.7, 120.3), (113.6, 121.4)], W, 'B')
    v('NRST', 113.6, 121.4)
    t('NRST', [(113.6, 121.4), (113.6, 123.45), (113.1, 123.95)], WP)
    # B.Cu north, under the north pins (northmost lane y 112.3), gap lane y 115.2, up the channel
    # between the J2 pad columns
    t('NRST', [(127.7, 119.85), (127.7, 113.0), (128.4, 112.3), (134.9, 112.3), (137.8, 115.2), (145.9, 115.2),
               (146.5, 114.6), (146.5, 110.54)], W, 'B')
    v('NRST', 146.5, 110.54)
    t('NRST', [(146.5, 110.54), (148.45, 110.54)], W)


def boot0(B):
    t, v = B.track, B.via
    t('BOOT0', [(124.0, 112.25), (124.0, 113.6), (124.8, 114.4), (128.6, 114.4)], WP)
    v('BOOT0', 128.6, 114.4)
    t('BOOT0', [(128.6, 114.4), (129.0, 114.4), (130.1, 113.3), (134.4, 113.3), (137.3, 116.2), (146.9, 116.2),
                (151.2, 120.5), (151.2, 126.57)], W, 'B')
    v('BOOT0', 151.2, 126.57)
    t('BOOT0', [(151.2, 126.57), (156.6, 126.57), (156.6, 124.79), (158.0, 124.79)], W)
    t('Net-(J3-Pin_2)', [(158.0, 125.81), (158.0, 127.84), (155.0, 127.84)], W)


def pcb_temp(B):
    t, v = B.track, B.via
    # pin 18 -> via under the body -> B.Cu: west to R12 / C30, and south between the CURR_A / CURR_B lanes
    t('PCB_TEMP', [(119.75, 122.5), (120.5, 122.5), (121.3, 123.3), (121.3, 123.55)], WP)
    v('PCB_TEMP', 121.3, 123.55)
    t('PCB_TEMP', [(121.3, 123.55), (121.05, 123.3), (119.8, 123.3), (114.6, 123.3), (113.8, 124.1),
                   (113.8, 126.83)], W, 'B')
    v('PCB_TEMP', 113.8, 126.83)
    t('PCB_TEMP', [(113.8, 126.83), (115.0, 126.83), (116.6, 126.78)], W)
    t('PCB_TEMP', [(119.8, 123.3), (119.3, 123.8), (119.3, 124.9), (117.6, 126.6), (117.6, 132.3),
                   (118.8, 133.5)], W, 'B')


def r11(B):
    """PCB_TEMP east branch -> R11.2 and +3.3V -> R11.1. R11 is boxed in on F (VDC island, SHB x 155.95),
    so both arrive on B.Cu: east between CURR_B (y 133) and CURR_A (y 134), south inside the CURR_B bend,
    through the throat between CURR_B (x 138.9) and the SENS_B diagonal, east at y 143.1 / 143.6 (the GND
    via at 144.6,144.4 keeps PCB_TEMP off y 143.7), vias at the east edge of the R11 pads (via overlaps the
    pad by 0.22, same net)."""
    t, v = B.track, B.via
    t('PCB_TEMP', [(118.8, 133.5), (132.0, 133.5), (133.1, 134.6), (136.0, 134.6), (136.4, 135.0), (136.4, 135.9),
                   (137.9, 137.4), (137.9, 142.44), (139.06, 143.6), (155.15, 143.6), (155.15, 149.78)], W, 'B')
    v('PCB_TEMP', 155.15, 149.78)
    # +3.3V: from the existing via south of C-pair at (133.6,131.7) on F to a new via, then B.Cu outside PCB_TEMP
    t('+3.3V', [(133.6, 131.7), (133.6, 133.9)], W)
    v('+3.3V', 133.6, 133.9)
    t('+3.3V', [(133.6, 133.9), (136.5, 133.9), (136.9, 134.3), (136.9, 135.7), (138.4, 137.2), (138.4, 142.23),
                (139.27, 143.1), (155.9, 143.1), (156.2, 143.4), (156.2, 150.9), (155.67, 151.43),
                (155.15, 151.43)], W, 'B')
    v('+3.3V', 155.15, 151.43)


def north_bus(B):
    """North pins on F.Cu. PROCCESS_LED to D1.2 at y 105.5. I2C / CAN: lanes N->S SDA 107.6, CAN_TX 108.9,
    CAN_RX 109.35, SCL 109.8 (north of C18 and of the SWCLK via), south-east into the corridor between J2
    and U2 (y 111.25 .. 112.54), north between J2 and C29 (x 150.0 .. 151.35), east south of U3
    (y 106.85 .. 108.2, south of the USB_D+ via), north-east between U3 and the +5V corner, east north of L2
    (y 102.4 .. 104.5). SDA up into J11.2; SCL via + B.Cu into J11.3; CAN_RX on F to U10.2; CAN_TX B.Cu hop
    under CAN_RX to U10.3. Lane pitch 0.45 (0.25 gap) at WP."""
    t, v = B.track, B.via
    t('PROCCESS_LED', [(122.5, 112.25), (122.5, 109.1), (126.1, 105.5), (134.64, 105.5), (134.64, 103.0)], WP)
    t('I2C_SDA', [(123.5, 112.25), (123.5, 108.8), (124.7, 107.6), (138.8, 107.6), (142.45, 111.25),
                  (150.0, 111.25), (150.0, 106.85), (154.4, 106.85), (158.85, 102.4), (161.64, 102.4),
                  (161.64, 99.6)], WP)
    t('CAN_TX', [(130.0, 112.25), (130.0, 108.9), (139.5, 108.9), (142.28, 111.68), (150.45, 111.68),
                 (150.45, 107.3), (154.59, 107.3), (158.89, 103.0), (170.4, 103.0)], WP)
    v('CAN_TX', 170.4, 103.0)
    t('CAN_TX', [(170.4, 103.0), (170.4, 109.77), (170.9, 110.27), (172.9, 110.27)], W, 'B')
    v('CAN_TX', 172.9, 110.27)
    t('CAN_TX', [(172.9, 110.27), (175.07, 110.27)], W)
    t('CAN_RX', [(130.5, 112.25), (130.5, 109.35), (139.35, 109.35), (142.11, 112.11), (150.9, 112.11),
                 (150.9, 107.75), (154.77, 107.75), (158.92, 103.6), (169.5, 103.6), (169.5, 107.74),
                 (175.07, 107.74)], WP)
    t('I2C_SCL', [(132.5, 112.25), (132.5, 109.8), (139.2, 109.8), (141.94, 112.54), (151.35, 112.54),
                  (151.35, 108.2), (154.96, 108.2), (158.66, 104.5), (164.14, 104.5)], WP)
    v('I2C_SCL', 164.14, 104.5)
    t('I2C_SCL', [(164.14, 104.5), (164.14, 99.6)], W, 'B')


def swd(B):
    """SWCLK / SWDIO: vias just north of pins 77 / 76, B.Cu north-east and east at y 106.73 / 107.37.
    SWCLK comes up at a via in the channel between the J2 pad columns, SWDIO runs under J2 to a via east of
    pad 2. SWO: F.Cu y 108.25 to a via west of the I2C / CAN turn, B.Cu y 108.0 to a channel via."""
    t, v = B.track, B.via
    t('SWCLK', [(133.0, 112.25), (133.0, 111.2), (133.2, 111.0), (133.2, 110.45)], WP)
    v('SWCLK', 133.2, 110.45)
    t('SWCLK', [(133.2, 110.45), (136.92, 106.73), (146.5, 106.73)], W, 'B')
    v('SWCLK', 146.5, 106.73)
    t('SWCLK', [(146.5, 106.73), (148.45, 106.73)], W)
    t('SWDIO', [(133.5, 112.25), (133.5, 111.5), (134.1, 110.9)], WP)
    v('SWDIO', 134.1, 110.9)
    t('SWDIO', [(134.1, 110.9), (137.63, 107.37), (150.3, 107.37), (150.3, 105.46)], WP, 'B')
    v('SWDIO', 150.3, 105.46)
    t('SWDIO', [(150.3, 105.46), (148.45, 105.46)], W)
    t('SWO', [(126.5, 112.25), (126.5, 108.25), (138.0, 108.25)], WP)
    v('SWO', 138.0, 108.25)
    t('SWO', [(138.0, 108.25), (138.25, 108.0), (146.5, 108.0)], W, 'B')
    v('SWO', 146.5, 108.0)
    t('SWO', [(146.5, 108.0), (148.45, 108.0)], W)


def usb(B):
    """USB_D+/- (pins 73 / 72): F.Cu east at y 115.15 / 115.6 (south of C11), vias, B.Cu pair north-east and
    east at y 109.0 / 109.45 through the J2 channel (between the SWO and NRST vias), north at x 153.05 / 153.5
    (west of the GND via at 154.3,109.0). D+ via south of U3.4, D- under U3 to a via north of U3.6. D+ carries
    two 1.2 mm bumps north of its lane to match the extra length of D- (difference ~0.4 mm).
    USB_CONN_D-: J1.2 south at x 149.95 into U3.1; USB_CONN_D+: x 150.6, diagonal to x 153.0, down between
    the U3 pad columns into pad 3. VBUS (0.4): via south of J1.1, B.Cu y 98 east, x 156.0 south to a via
    east of U3.5 (F stub), on south at x 156.3, diagonal past the GND vias at y 118.2, via (153.0,120.2),
    F.Cu to D2.1."""
    t, v = B.track, B.via
    t('USB_D+', [(135.25, 115.0), (136.2, 115.0), (136.35, 115.15), (139.0, 115.15), (139.9, 114.25)], WP)
    v('USB_D+', 139.9, 114.25)
    t('USB_D+', [(139.9, 114.25), (145.15, 109.0), (147.3, 109.0), (147.3, 107.8), (148.1, 107.8), (148.1, 109.0),
                 (148.9, 109.0), (148.9, 107.8), (149.7, 107.8), (149.7, 109.0), (153.05, 109.0), (153.05, 107.29),
                 (154.14, 106.2)], WP, 'B')
    v('USB_D+', 154.14, 106.2)
    t('USB_D+', [(154.14, 106.2), (154.14, 105.15)], WP)
    t('USB_D-', [(135.25, 115.5), (136.0, 115.5), (136.1, 115.6), (140.1, 115.6), (140.9, 114.8), (140.9, 114.55)], WP)
    v('USB_D-', 140.9, 114.55)
    t('USB_D-', [(140.9, 114.55), (146.0, 109.45), (153.5, 109.45), (153.5, 107.7), (154.8, 106.4),
                 (154.8, 102.3)], WP, 'B')
    v('USB_D-', 154.8, 102.3)
    t('USB_D-', [(154.8, 102.3), (154.13, 102.97), (154.13, 103.25)], WP)
    t('USB_CONN_D-', [(149.95, 96.1), (149.95, 102.6), (150.6, 103.25), (151.87, 103.25)], WP)
    t('USB_CONN_D+', [(150.6, 96.1), (150.6, 99.6), (153.0, 102.0), (153.0, 104.75), (152.6, 105.15),
                      (151.87, 105.15)], WP)
    WV = 0.4
    t('VBUS', [(149.3, 96.1), (149.3, 98.0)], WV)
    v('VBUS', 149.3, 98.0)
    t('VBUS', [(149.3, 98.0), (155.6, 98.0), (156.0, 98.4), (156.0, 104.2), (156.3, 104.5), (156.3, 116.0),
               (153.0, 119.3), (153.0, 120.2)], WV, 'B')
    v('VBUS', 156.0, 104.2)
    t('VBUS', [(156.0, 104.2), (154.13, 104.2)], W)
    v('VBUS', 153.0, 120.2)
    t('VBUS', [(153.0, 120.2), (152.15, 121.05), (151.27, 121.05)], WV)


# ------------------------------------------------------------------------------------ batch D
def plane_taps(B):
    """GND vias to In1 / B pour, +3.3V and +5V vias to their In2 zones, short links between pads."""
    t, v = B.track, B.via
    G = 'GND'
    # GND: one via per small-signal pad (pitch >= 1.6 mm), shared via where two pads are neighbours
    for x, y, px, py in ((106.0, 129.47, None, None),                # U11.2 / U11.3 (between the pads)
                         (110.6, 125.87, 110.6, 126.52),             # C65.2
                         (112.15, 123.47, 112.8, 123.12),            # C10.2
                         (112.8, 119.17, 112.8, 119.82),             # C2.2
                         (114.9, 118.0, 114.9, 118.95),              # Y1.2
                         (115.95, 119.65, 117.1, 120.65),            # Y1.4 (under the crystal)
                         (115.0, 124.425, 115.0, 125.17),            # R12.2
                         (116.73, 116.9, 116.08, 116.9),             # C1.2
                         (116.35, 102.2, 116.35, 103.12),            # C57.2
                         (119.25, 102.2, 119.25, 103.12),            # C58.2
                         (123.675, 102.15, 123.67, 103.0),           # R30.1 (+ C59.2 below)
                         (121.85, 106.07, 121.85, 106.72),           # C55.2
                         (130.29, 102.3, 130.29, 103.0),             # R2.1
                         (136.09, 102.3, 136.09, 103.0),             # R4.1
                         (152.5, 95.775, 151.9, 96.13),              # J1.5
                         (150.863, 103.9, 151.86, 104.2),            # U3.2
                         (149.04, 123.85, 149.04, 122.0),            # C8.2 (south: LDO_IN passes east)
                         (178.575, 102.8, 177.78, 102.8),            # C56.2
                         (172.6, 104.025, 172.6, 104.83),            # C53.2
                         (175.075, 113.51, 175.07, 112.81),          # U10.4
                         (175.6, 130.0, 176.45, 130.0)):             # C54.2
        if px is not None:
            t(G, [(px, py), (x, y)], 0.3)
        v(G, x, y)
    t(G, [(105.36, 129.47), (106.64, 129.47)], 0.3)                  # U11.2 / U11.3 -> via between them
    t(G, [(122.15, 103.12), (123.67, 103.0)], 0.3)                   # C59.2 -> R30.1
    v(G, 150.6, 93.45)                                               # J1 SMD shield tab (via in the tab)
    t(G, [(133.98, 135.5), (134.85, 135.95), (135.68, 136.4)], 0.3)  # C36.2 + R14.1, shared via
    v(G, 134.85, 135.95)
    t(G, [(143.3, 115.22), (144.2, 114.4), (145.35, 113.7)], 0.3)    # C4.2 + U2.1 (LDO GND)
    v(G, 144.2, 114.4)
    # J2 GND pins 3 / 5 / 9 from the west side: link at x 142.9, two vias
    t(G, [(144.55, 106.73), (142.9, 106.73)], 0.3)
    t(G, [(144.55, 108.0), (142.9, 108.0)], 0.3)
    t(G, [(144.55, 110.54), (142.9, 110.54)], 0.3)
    t(G, [(142.9, 106.08), (142.9, 110.54)], 0.3)
    v(G, 142.9, 106.08)
    v(G, 142.9, 110.14)
    # +3.3V (In2 +3.3V zone): pull-ups R31-R34, D3, J2.1, C8.1, J11.1, L3.1, LDO output
    P = '+3.3V'
    for x, y, px, py in ((114.9, 108.775, 114.9, 108.03), (116.7, 108.775, 116.7, 108.03),
                         (118.5, 108.775, 118.5, 108.03), (120.3, 108.775, 120.3, 108.03),
                         (139.588, 103.0, 140.44, 103.0), (144.55, 104.71, 144.55, 105.46),
                         (147.01, 122.0, 145.96, 122.0), (157.94, 99.6, 159.14, 99.6),
                         (171.588, 101.95, 171.59, 103.0)):
        t(P, [(px, py), (x, y)], 0.4 if P == '+3.3V' and px in (145.96, 159.14) else 0.3)
        v(P, x, y)
    t(P, [(145.35, 116.0), (151.65, 116.0)], 0.4)                    # U2 pin 2 -> tab under the body
    v(P, 150.6, 116.0)
    # +5V (In2 +5V zone): C29.1, C54.1, L4.1
    F5 = '+5V'
    for x, y, px, py in ((154.9, 112.525, 154.9, 113.48), (172.9, 130.0, 174.55, 130.0)):
        t(F5, [(px, py), (x, y)], 0.4)
        v(F5, x, y)
    # L4.1 joins C54.1 on F (north of C54.2): the In2 +5V plane stays 6.7 mm from the isolated side
    t(F5, [(178.21, 130.0), (178.21, 128.75), (174.55, 128.75), (174.55, 130.0)], 0.4)


def buck_ldo(B):
    """U4 buck: RT/SYNC, PG, FB divider (R9/R10/C28), local GND and +5V taps; LDO_IN and D2 +5V."""
    t, v = B.track, B.via
    t('Net-(U4-RT{slash}SYNC)', [(161.8, 123.91), (161.88, 126.3)], W)   # U4.4 -> R7.1
    t('GND', [(163.53, 126.3), (163.53, 124.4), (163.9, 123.8)], 0.3)      # R7.2 -> U4 exposed pad
    t('GND', [(170.9, 123.69), (170.9, 123.04)], 0.3)                      # R10.2 -> via
    v('GND', 170.9, 123.04)
    # FB node: U4.5 -> R9.2; branch west/south of R9/C28 (away from SW at y 120) to C28.2 -> R10.1
    FB = 'Net-(U4-FB)'
    t(FB, [(167.2, 123.91), (168.3, 123.91), (168.3, 127.0), (169.92, 127.0), (169.92, 126.3)], WP)
    t(FB, [(168.3, 123.91), (168.52, 123.69), (169.7, 123.69)], WP)
    t(FB, [(169.92, 126.3), (170.9, 125.5), (170.9, 124.71)], WP)
    # divider top (R9.1, C28.1) and R8.1 pull-up: +5V vias to the In2 +5V zone
    t('+5V', [(168.95, 125.35), (169.7, 124.71)], W)
    t('+5V', [(168.95, 125.35), (169.28, 126.3)], W)
    v('+5V', 168.95, 125.35)
    t('+5V', [(165.68, 126.3), (164.925, 126.3)], 0.3)
    v('+5V', 164.925, 126.3)
    # PG: R8.2 -> via, B.Cu under U4.5, via east of U4.6
    PG = 'Net-(U4-PG)'
    t(PG, [(167.32, 126.3), (167.32, 127.3)], W)
    v(PG, 167.32, 127.3)
    t(PG, [(167.32, 127.3), (167.9, 126.7), (167.9, 123.3), (168.6, 122.64)], W, 'B')
    v(PG, 168.6, 122.64)
    t(PG, [(168.6, 122.64), (167.2, 122.64)], W)
    # LDO_IN: C4.1 -> U2.3 -> under the U2 tab -> x 150.1 between C8 and D2 -> between D2 pins 1/2 -> D2.3
    t('LDO_IN', [(143.3, 116.78), (143.3, 117.0), (143.9, 118.3), (145.35, 118.3), (149.75, 118.3),
                 (150.1, 118.65), (150.1, 122.0), (153.14, 122.0)], 0.3)
    # D2.2 (+5V) round the south and east of D2.3 to a via in the In2 +5V zone
    t('+5V', [(151.26, 122.95), (151.26, 123.75), (154.3, 123.75), 0.3, (154.3, 120.5), (154.0, 119.85)], 0.4)
    v('+5V', 154.0, 119.85)


def analog_3v3(B):
    """+3.3VA west branch: from C17.1 (L1 filter output side) to C65 and the U11 supply pins.
    Never tied to +3.3V except through L1. The band amplifiers U6/U7/U8: see analog_band()."""
    A = '+3.3VA'
    B.track(A, [(121.12, 130.0), (117.8, 130.0), (117.5, 129.7), (117.5, 128.75), (111.2, 128.75),
                (110.6, 128.15), (110.6, 127.48)], W)
    B.track(A, [(110.6, 127.48), (109.9, 127.48), (109.4, 127.0), (106.0, 127.0), (106.0, 125.3)], W)
    B.track(A, [(105.36, 125.3), (106.64, 125.3)], W)


def analog_band(B):
    """+3.3VA to the shunt amplifiers U6/U7/U8 (pins 6/7) and their caps C41/C46/C51 (pad 1), width 0.4.
    Trunk: F x 117.65 from the west +3.3VA track to a via, B.Cu x 120.6 between the GND_A / VDC_A via
    columns, then east along y 155.9 under the bridges (In1 GND between it and the F power copper).
    It passes south of the CURR_A / CURR_B lane vias (y 156.0) and north of the bulk-cap THT pads
    (y >= 156.76), and hops on F over the SENS_B (x 138.5) and SENS_C (x 167.5) B.Cu lanes.
    Phase A: B.Cu under U6 / C41 is the PHASE_A_B zone, so U6 gets a via north of pin 7 and C41 an F stub
    through the dead west lobe of the SHA F zone (x 116.95, between R18 and R19). Phases B / C: B.Cu
    under the parts is GND pour, so each amplifier and cap gets a via inside its own F enclosure."""
    A, w = '+3.3VA', 0.4
    t, v = B.track, B.via
    t(A, [(117.8, 130.0), (117.65, 130.15), (117.65, 136.9)], w)
    v(A, 117.65, 136.9)
    t(A, [(117.65, 136.9), (120.6, 136.9), (120.6, 156.8)], w, 'B')
    # phase A: C41 west, U6 east, then the trunk east
    t(A, [(116.95, 156.8), (129.2, 156.8), (130.1, 155.9), (137.85, 155.9)], w, 'B')
    v(A, 116.95, 156.95)
    t(A, [(116.95, 156.95), (116.95, 161.6), (116.5, 162.05), (115.9, 162.28)], w)
    v(A, 123.65, 156.8)
    t(A, [(123.65, 156.8), (123.36, 157.6), (124.64, 157.6)], w)
    # hop over SENS_B, phase B, around the CURR_B via, hop over SENS_C, phase C
    v(A, 137.85, 155.9)
    t(A, [(137.85, 155.9), (139.25, 155.9)], w)
    v(A, 139.25, 155.9)
    t(A, [(139.25, 155.9), (155.2, 155.9), (156.1, 156.8), (157.7, 156.8), (158.6, 155.9), (166.85, 155.9)], w, 'B')
    v(A, 166.85, 155.9)
    t(A, [(166.85, 155.9), (168.2, 155.9)], w)
    v(A, 168.2, 155.9)
    t(A, [(168.2, 155.9), (182.4, 155.9), (182.4, 160.35)], w, 'B')
    for dx in (0.0, 28.5):                       # U7 / C46 and U8 / C51 (bridge pitch 28.5)
        t(A, [(145.6 + dx, 155.9), (145.6 + dx, 160.4)], w, 'B')
        v(A, 145.6 + dx, 160.4)
        t(A, [(145.6 + dx, 160.4), (145.6 + dx, 161.6), (145.0 + dx, 162.2), (144.4 + dx, 162.28)], w)
    t(A, [(153.9, 155.9), (153.9, 160.35)], w, 'B')
    for x in (153.9, 182.4):
        v(A, x, 160.35)
        t(A, [(x, 160.35), (x - 0.76, 159.6), (x - 0.76, 158.4), (x - 2.04, 158.4)], w)


def j10_5v(B):
    """+5V to J10.1 (hall sensor supply, through-hole). The USB group (J1, VBUS B.Cu x 156) and the F.Cu
    lines to J11 wall off the buck output from the west, so the track leaves L2.1 northwards: via north of
    L2.1, B.Cu east of J11.4 (x 168.9), then west along y 95.0 (under J1 between its shield pad rows,
    north of the EXT_SPI B.Cu lanes y >= 95.9) and down into J10.1. Width 0.4."""
    P = '+5V'
    B.via(P, 166.4, 104.75)
    B.track(P, [(166.4, 104.75), (166.4, 105.6)], 0.4)
    B.track(P, [(166.4, 104.75), (168.9, 104.75), (168.9, 95.0), (110.64, 95.0), (110.64, 99.6)], 0.4, 'B')


def iso_can(B):
    """U10 / U9 isolated CAN. Logic side (VCC1, U9-VIN) stays west of x 176.8 (y < 120.5) / 179.3; bus side
    copper stays east of x 180.2 (U9 pins) / 182.95 (U10 pins): nothing in the gap. ISO width 0.3."""
    t, v = B.track, B.via
    I = 0.3
    # logic side: L3.2 -> C56.1 / U10.1 -> C53.1, then B.Cu x 176.4 / 177.3 south to test point TP1
    V1 = 'Net-(U10-VCC1)'
    t(V1, [(173.41, 103.0), (176.22, 102.8)], I)
    t(V1, [(174.6, 103.0), (174.6, 105.19)], I)
    t(V1, [(174.0, 105.19), (173.6, 105.6), (173.6, 106.38), (172.6, 106.38)], I)
    t(V1, [(176.22, 102.8), (176.4, 103.6), (176.4, 104.2)], I)
    v(V1, 176.4, 104.2)
    t(V1, [(176.4, 104.2), (176.4, 120.0), (177.3, 120.9), (177.3, 137.5), (175.5, 137.5)], I, 'B')
    VI = 'Net-(U9-VIN)'                                                  # U9.2 -> L4.2 -> C60.1 -> TP3
    t(VI, [(178.54, 127.0), (178.9, 127.9), (179.79, 129.6), (179.79, 131.2), (179.0, 132.0), (179.0, 132.6)], 0.4)
    t(VI, [(179.0, 132.6), (177.0, 133.5), (175.5, 133.5)], 0.4)
    # bus side: U10 -> common-mode choke L5
    t('Net-(U10-CANH)', [(184.12, 107.73), (186.0, 107.73), (186.6, 108.33), (186.6, 109.52), (187.19, 109.52)], I)
    t('Net-(U10-CANL)', [(184.12, 110.27), (187.7, 110.27), (188.01, 109.91)], I)
    # CAN_L: L5.3 -> J13.2 (F), -> CR1.2; B.Cu J13.2 -> J12.3 -> via west of C63.1
    t('CAN_L', [(188.01, 107.68), (188.6, 107.68), (189.4, 108.5), (194.3, 108.5)], I)
    t('CAN_L', [(188.01, 107.68), (188.01, 106.8), (188.55, 106.26), (188.55, 105.22)], I)
    t('CAN_L', [(194.3, 108.5), (192.8, 110.0), (192.8, 115.0), (190.72, 117.0), (186.3, 117.0), (185.4, 116.1)], I, 'B')
    v('CAN_L', 185.4, 116.1)
    t('CAN_L', [(185.4, 116.1), (186.53, 116.1)], I)
    # CAN_H: L5.4 -> CR1.1 -> y 104.2 (between CR1.3 and CR1.1/2) -> J13.1; via x 190 B.Cu south to R39.1 / C64.2
    t('CAN_H', [(187.19, 107.68), (187.19, 106.6), (186.65, 106.06), (186.65, 105.22)], I)
    t('CAN_H', [(186.65, 105.22), (186.65, 104.2), (194.3, 104.2), (194.3, 105.0)], I)
    v('CAN_H', 190.0, 104.2)
    t('CAN_H', [(190.0, 104.2), (190.0, 112.8), (189.2, 113.6)], I, 'B')
    v('CAN_H', 189.2, 113.6)
    t('CAN_H', [(189.2, 113.6), (188.4, 112.83), (187.6, 112.83)], I)
    t('CAN_H', [(189.2, 113.6), (188.07, 114.4)], I)
    # termination jumper J12.2 <- R39.2 (F); J13 pad 3 <- R40.1 (B.Cu round the east edge)
    t('Net-(J12-Pin_2)', [(187.6, 111.17), (192.0, 111.17), (192.0, 115.6), (192.6, 116.2), (193.26, 117.0)], I)
    t('Net-(J13-Pad3)', [(186.47, 118.3), (186.47, 119.3)], I)
    v('Net-(J13-Pad3)', 186.47, 119.3)
    t('Net-(J13-Pad3)', [(186.47, 119.3), (197.3, 119.3), (197.3, 112.0), (194.3, 112.0)], I, 'B')
    # GND_ISO on F: U10.5 -> C64.1 -> (channel y 115.25) -> C63.2 -> R40.2 -> R38.2 -> C61.2 / U9.3, TP5, CR1.3
    G = 'GND_ISO'
    t(G, [(184.12, 112.81), (185.9, 112.81), (185.9, 113.7), (186.53, 114.4)], I)
    t(G, [(186.53, 114.4), (186.53, 115.25), (188.07, 115.25), (188.07, 116.1)], I)
    t(G, [(188.07, 116.1), (188.1, 117.2), (188.12, 118.3)], I)
    t(G, [(183.5, 116.28), (183.5, 117.2), (188.1, 117.2)], I)
    t(G, [(188.12, 118.3), (188.0, 123.54)], I)
    t(G, [(188.0, 123.54), (189.6, 123.54), (189.6, 129.55), (184.5, 129.55)], I)
    t(G, [(181.08, 127.0), (181.08, 127.8), (182.5, 129.2), (184.5, 129.55)], I)
    t(G, [(189.6, 124.2), (195.5, 124.2), (195.5, 122.0)], I)
    t(G, [(187.6, 103.18), (187.6, 102.0), (197.6, 102.0), (197.6, 122.0), (195.5, 122.0)], I)
    # 5V_ISO: U10.8 via -> B.Cu x 184.6 -> C62.2 via -> U9.4 -> C61.1 via, C60.2; U9.4 -> TP4 (B), R38.1 via
    P = '5V_ISO'
    t(P, [(184.12, 105.19), (184.12, 104.2)], I)
    v(P, 184.12, 104.2)
    t(P, [(184.12, 104.2), (184.6, 104.7), (184.6, 131.0), (185.8, 131.45)], I, 'B')
    t(P, [(183.5, 114.72), (184.6, 114.72)], I)
    v(P, 184.6, 114.72)
    v(P, 185.8, 131.45)
    t(P, [(185.8, 131.45), (184.5, 131.45)], I)
    t(P, [(184.6, 128.6), (182.6, 130.6), (181.5, 132.6)], I, 'B')
    t(P, [(183.62, 127.0), (186.0, 127.0), (190.5, 122.5), (191.5, 122.0)], I, 'B')
    v(P, 186.0, 127.0)
    t(P, [(186.0, 127.0), (187.12, 126.46), (188.0, 126.46)], I)


def f_gnd_pour(B):
    """F.Cu GND pour over the control area (north of y 133, logic side of the isolation gap only), priority
    below every existing zone; it is stitched to In1 / B.Cu by the GND vias placed in the batches above."""
    B.zone('GND', 'F', [(100.0, 92.0), (178.6, 92.0), (178.6, 104.0), (176.8, 104.0), (176.8, 120.5),
                        (177.7, 120.5), (177.7, 133.0), (100.0, 133.0)], prio=0, solid=True, name='GND_F_control')
    # 11d4: east edge 179.3 -> 177.7 = 2.5 mm from U9.3 (same ISO_X as the In1 / B.Cu GND zones in route_11c2)


def f_gnd_stitch(B):
    """Extra GND vias for GND_F_control (11c4e): pieces of the pour that had a single via (W of J10 / C65,
    under the MCU SW corner, J10-J9 gap, S of L3) and the open areas of the main piece that were > 6 mm from
    any GND via. Spots found by search (via inside the fill, F/B/hole clearance, >= 1.6 mm from GND vias)."""
    for x, y in ((103.93, 126.24), (121.12, 124.6), (115.8, 107.21), (121.4, 110.31), (171.1, 106.9),
                 (113.97, 101.07), (117.79, 101.27),
                 (100.7, 92.9), (100.7, 108.8), (165.5, 92.7), (100.8, 119.8), (111.5, 92.7), (140.1, 92.7),
                 (176.1, 92.7), (127.3, 92.7), (162.7, 102.2), (106.5, 101.1), (109.1, 109.5), (119.4, 94.0),
                 (144.9, 98.8), (133.7, 95.8), (159.4, 96.1), (170.6, 97.5), (105.7, 115.2), (100.7, 125.9),
                 (100.7, 99.0)):
        B.via('GND', x, y)


def rest_3v3(B):
    """+3.3V leftovers: J3.1 to a 3V3_In2 via west of the BOOT0 via; R5.1 / R6.1 (boxed in by the SENS_C /
    CURR_C / CURR_B B.Cu lanes and the U5 gate bundle on F) through a small +3.3V In2 tongue that takes
    2.9 x 1.6 mm off the north edge of VDC_In2 (priority 1 > VDC_In2 0) and one shared via."""
    P = '+3.3V'
    B.track(P, [(155.0, 125.3), (154.3, 125.0), (150.4, 125.0)], 0.3)
    B.via(P, 150.4, 125.0)
    B.zone(P, 'In2', [(151.0, 131.5), (155.4, 131.5), (155.4, 134.8), (151.0, 134.8)], prio=1, solid=True,
           clearance=0.3, name='3V3_In2_R5R6')
    B.track(P, [(153.0, 134.01), (154.6, 134.01)], 0.3)
    B.via(P, 153.85, 134.06)


def main(src, dst):
    dst = os.path.abspath(dst)
    stem = os.path.splitext(dst)[0]
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, os.path.basename(dst))
        shutil.copyfile(src, work)
        for ext in ('.kicad_pro', '.kicad_dru'):
            if os.path.exists(stem + ext):
                shutil.copyfile(stem + ext, os.path.splitext(work)[0] + ext)
            else:
                print('warning: no', stem + ext, '- zone fill uses default rules')
        B = Board(work)
        leds(B)
        hall(B)
        temp_in(B)
        can_led(B)
        hse(B)
        drv_bus(B)
        south_pins(B)
        nrst(B)
        boot0(B)
        pcb_temp(B)
        r11(B)
        north_bus(B)
        swd(B)
        usb(B)
        plane_taps(B)
        buck_ldo(B)
        analog_3v3(B)
        analog_band(B)
        j10_5v(B)
        iso_can(B)
        rest_3v3(B)
        f_gnd_pour(B)
        f_gnd_stitch(B)
        B.fill_and_save(work)
        shutil.copyfile(work, dst)
    print('added', B.count)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
