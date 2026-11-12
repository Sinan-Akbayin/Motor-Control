"""Step 11c3 for BLDC_V_0.1: analog nets on top of the 11c2 copper, by explicit coordinates.

usage (KiCad's bundled Python, KiCad closed or on a copy):
  python route_11c3.py <route_11c2.kicad_pcb> <out.kicad_pcb>

The input must be the output of tools/route_11c2.py; nothing is removed, only tracks and vias are
added and the zones are refilled. All coordinates are board mm (x right, y down).

Nets: CURR_A/B/C (AD8418A outputs U6/U7/U8 -> MCU), I_DC (U11 -> MCU), SENS_A/B/C (phase voltage
dividers -> MCU), SENS_VDC (bus divider -> MCU).

Layer use: F.Cu runs lie over the unbroken In1 GND plane. Long runs through the power band are on
B.Cu, below In1 GND and In2 VDC, in the lanes between the bridges or under the DC (VDC) islands,
not under a switch-node zone. The MCU pins of CURR_A/B/C and SENS_C are boxed in by bypass
capacitors, so they go to a via under the MCU body.

Same temp-folder handling as route_11c2.py (pcbnew's Save() rewrites the .kicad_pro next to it).
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_11c2 import Board, PITCH, sh  # noqa: E402

W = 0.25          # analog track
WP = 0.2          # at 0.5 mm pitch MCU pins and between 0603 pads


def curr(B):
    t, v = B.track, B.via
    # amplifier output (pin 5) -> via north-east of the amplifier, same shape on each bridge
    for k, net in enumerate(('CURR_A', 'CURR_B', 'CURR_C')):
        dx = k * PITCH
        t(net, sh([(128.3, 156.0), (127.75, 156.55), (126.4, 156.55), (125.905, 157.05), (125.905, 158.125)], dx), W)
        v(net, 128.3 + dx, 156.0)

    # CURR_A / CURR_B: MCU pins 21 / 25 leave on the outer (west) side to vias next to the pin row, so
    # that F.Cu and B.Cu under the south-west corner of the body stay free for the south pins 26-32
    # (11c4). B.Cu lanes south: CURR_A x 117.0, CURR_B x 119.45; x 117.6 between them is PCB_TEMP (11c4).
    t('CURR_A', [(119.75, 124.0), (119.0, 124.0), (118.55, 124.15)], WP)
    v('CURR_A', 118.55, 124.15)
    t('CURR_A', [(118.55, 124.15), (117.0, 125.7), (117.0, 132.9), (118.1, 134.0), (126.6, 134.0), (128.6, 136.0),
                 (128.6, 155.7), (128.3, 156.0)], W, 'B')

    # CURR_B: via in the free corner between pins 25 and 26, B.Cu south, east along y 133, down the
    # A/B lane, under the DRV caps and the VDC island of bridge B, then down east of bridge B
    t('CURR_B', [(119.75, 126.0), (119.45, 126.0), (119.45, 126.75)], WP)
    v('CURR_B', 119.45, 126.75)
    t('CURR_B', [(119.45, 126.75), (119.45, 132.45), (120.0, 133.0), (137.4, 133.0), (137.4, 135.5), (138.9, 137.0),
                 (138.9, 142.0), (139.5, 142.6), (157.0, 142.6), (157.6, 143.2), (157.6, 155.2),
                 (156.8, 156.0)], W, 'B')

    # CURR_C: MCU pin 38 -> via under the body -> B.Cu east out of the MCU, north of U5, north of
    # bridge C, down east of bridge C
    t('CURR_C', [(127.5, 127.75), (127.5, 126.2)], WP)
    v('CURR_C', 127.5, 126.2)
    t('CURR_C', [(127.5, 126.2), (127.5, 123.6), (128.1, 123.0), (139.5, 123.0), (141.5, 125.0), (141.5, 130.4),
                 (143.5, 132.4), (170.5, 132.4), (172.9, 134.8), (172.9, 139.3), (173.5, 139.9), (185.5, 139.9),
                 (186.1, 140.5), (186.1, 155.2), (185.3, 156.0)], W, 'B')


def i_dc(B):
    # U11 pin 5 -> MCU pin 20, F.Cu: between R1 and the GND via of C30, then between C10 and R12
    B.track('I_DC', [(119.75, 123.5), (118.6, 123.5), (118.44, 123.34), (114.5, 123.34), (113.8, 124.04),
                     (113.8, 124.5), (113.4, 124.9), (108.3, 124.9), (107.905, 124.525)], WP)


def sens(B):
    t, v = B.track, B.via
    # divider tap: R18 pad 2 -> R17 pad 1 -> C38 pad 1, and a via west of the cluster
    for k, net in enumerate(('SENS_A', 'SENS_B', 'SENS_C')):
        dx = k * PITCH
        t(net, sh([(115.9, 157.775), (115.45, 157.95), (114.4, 159.0), (113.9, 159.425)], dx), WP)
        t(net, sh([(111.4, 159.4), (113.9, 159.4)], dx), W)
        t(net, sh([(112.9, 159.4), (112.9, 162.28), (113.9, 162.28)], dx), WP)
        v(net, 111.4 + dx, 159.4)

    # SENS_A: MCU pin 45 -> F.Cu south between C13 and C7, west below the MCU caps, via, B.Cu west
    # of bridge A
    # (the two jogs are steep, 0.25 over 0.75 mm, so the parallel diagonals keep 0.27 mm between them)
    t('SENS_A', [(131.0, 127.75), (131.0, 128.5), (131.25, 129.25), (131.25, 132.3), (130.55, 133.0),
                 (119.6, 133.0), (118.4, 134.2), (118.4, 135.8)], WP)
    v('SENS_A', 118.4, 135.8)
    t('SENS_A', [(118.4, 135.8), (112.4, 135.8), (111.4, 136.8), (111.4, 159.4)], W, 'B')

    # SENS_B: MCU pin 46 -> F.Cu south next to SENS_A, via above the GLA track, B.Cu down the A/B lane
    t('SENS_B', [(131.5, 127.75), (131.5, 128.5), (131.75, 129.25), (131.75, 137.0)], WP)
    v('SENS_B', 131.75, 137.0)
    # x 138.5: clear of the through-hole pad 2 of C32 (bulk capacitor)
    t('SENS_B', [(131.75, 137.0), (138.5, 143.75), (138.5, 158.0), (139.9, 159.4)], W, 'B')

    # SENS_C: MCU pin 44 -> via under the body -> B.Cu east inside CURR_C, down the B/C lane
    t('SENS_C', [(130.5, 127.75), (130.5, 126.3)], WP)
    v('SENS_C', 130.5, 126.3)
    t('SENS_C', [(130.5, 126.3), (130.5, 125.0), (131.5, 124.0), (139.0, 124.0), (140.5, 125.5), (140.5, 130.9),
                 (143.0, 133.4), (166.5, 133.4), (167.5, 134.4), (167.5, 158.5), (168.4, 159.4)], W, 'B')


def sens_vdc(B):
    t = B.track
    # R13 pad 1 - R14 pad 2 (diagonal between the four pads), C36 pad 1 along the top
    t('SENS_VDC', [(135.675, 134.6), (135.9, 134.9), (137.1, 136.1), (137.325, 136.4)], WP)
    t('SENS_VDC', [(133.02, 135.5), (133.02, 134.6), (135.675, 134.6)], WP)
    # -> MCU pin 69. A track east of the MCU would wall off the east pins (DRV bus, USB), so the pin
    # goes west under the body to a via, B.Cu south (west of CURR_C) and east below the MCU caps,
    # and comes up next to R13
    t('SENS_VDC', [(135.25, 117.0), (128.8, 117.0), (126.6, 119.2)], WP)
    B.via('SENS_VDC', 126.6, 119.2)
    t('SENS_VDC', [(126.6, 119.2), (126.6, 129.9), (127.1, 130.4), (134.1, 130.4), (135.7, 132.0)], W, 'B')
    B.via('SENS_VDC', 135.7, 132.0)
    t('SENS_VDC', [(135.7, 132.0), (135.675, 134.6)], WP)


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
        curr(B)
        i_dc(B)
        sens(B)
        sens_vdc(B)
        B.fill_and_save(work)
        shutil.copyfile(work, dst)
    print('added', B.count)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
