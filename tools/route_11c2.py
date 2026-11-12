"""Step 11c2 for BLDC_V_0.1: critical copper on top of placement v3, by explicit coordinates.

usage (KiCad's bundled Python, KiCad closed or on a copy):
  python route_11c2.py <placement_v3.kicad_pcb> <out.kicad_pcb> [--rotate-c26]

The input must be the v3 placement (tools/place_v3.py); every existing track, via and zone is
removed first, so the script can be re-run. All coordinates are board mm (x right, y down).

What it draws (see docs/WORK.md, step 11c2):
  planes   In1 GND (not under the isolated CAN side), In2 VDC under the power band with a tongue to
           the buck, In2 +3.3V under the MCU and +5V under the buck, B.Cu GND pour
  power    VDC_IN / VDC_F zones J14 -> F1 -> D5 / R41, R41 pad 2 -> In2 through a via array;
           per bridge: VDC island (FET drain, ceramics, vias to In2), GND island (FET source,
           ceramics, vias to In1/B.Cu), SHx zone, phase-out zone; phase A crosses to J5 on B.Cu
  gate     GHx/SHx pairs and GLx from U5 to the gate resistors and FETs
  kelvin   shunt inner pad edges -> AD8418A inputs (R19/R24/R29 -> U6/U7/U8, R41 -> U11)
  decoup   U5 capacitors, MCU bypass capacitors with plane vias, buck input/output loop

Bridge A is described in board coordinates; B and C are the same shapes shifted by PITCH.

pcbnew's Save() rewrites the .kicad_pro next to the board with whatever settings it has loaded. The
script therefore works in a temporary folder on copies of the board and of the project's .kicad_pro
/ .kicad_dru (taken from the folder of <out>, so the zone fill uses the real netclasses and rules)
and copies only the finished .kicad_pcb to <out>.
"""
import os
import shutil
import sys
import tempfile

import pcbnew

MM = pcbnew.FromMM
PITCH = 28.5                      # bridge A -> B -> C
# C26 (charge-pump flying cap) has pad 1 (CPH) on the far side of pad 2 (CPL): the two nets cross and
# cannot both be routed on F.Cu. --rotate-c26 turns the part 180 deg in place and routes them;
# without it CPH/CPL are left unrouted.
ROTATE_C26 = '--rotate-c26' in sys.argv

LAYER = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu, 'In1': pcbnew.In1_Cu, 'In2': pcbnew.In2_Cu}

# GND copper may not enter the isolated CAN side (U10 pins 5-8, U9 pins 3-4, C60 pad 2 and east)
# In2 planes (VDC, +3.3V, +5V) keep >= 6.7 mm (U10 pad-row gap) from isolated-side copper (11c4e)
# 11d4: GND pours keep >= 2.5 mm from isolated copper: east edge x ISO_X (U9.3 west pad edge 180.28 - 2.5),
# band top y ISO_Y east of it (C60.2 south pad edge 133.4 + 2.6); TP2 (GND, 180.0/137.5) stays inside the band
ISO_X, ISO_Y = 177.7, 136.0
GND_AREA = [(100, 92), (178.6, 92), (178.6, 104.0), (176.8, 104.0), (176.8, 120.5), (ISO_X, 120.5),
            (ISO_X, ISO_Y), (198.5, ISO_Y), (198.5, 176.3), (100, 176.3)]
BAND_Y = 133.0                    # power band (solid pad connections) starts here
GND_CTRL = [(100, 92), (178.6, 92), (178.6, 104.0), (176.8, 104.0), (176.8, 120.5), (ISO_X, 120.5),
            (ISO_X, BAND_Y + 0.2), (100, BAND_Y + 0.2)]
GND_BAND = [(100, BAND_Y), (ISO_X, BAND_Y), (ISO_X, ISO_Y), (198.5, ISO_Y), (198.5, 176.3), (100, 176.3)]


class Board:
    def __init__(self, path):
        self.b = pcbnew.LoadBoard(path)
        self.nets = {}
        for name, net in self.b.GetNetsByName().items():
            name = str(name)
            self.nets[name] = net
            self.nets.setdefault(name.split('/')[-1], net)
        self.count = {'track': 0, 'via': 0, 'zone': 0}

    def clear(self):
        for t in list(self.b.GetTracks()):
            self.b.Delete(t)
        for z in [self.b.GetArea(i) for i in range(self.b.GetAreaCount())]:
            self.b.Delete(z)

    def track(self, net, pts, w, layer='F'):
        """Polyline of segments; pts may contain a number to change the width from there on."""
        prev = None
        for p in pts:
            if not isinstance(p, tuple):
                w = p
                continue
            if prev is not None and prev != p:
                t = pcbnew.PCB_TRACK(self.b)
                t.SetStart(pcbnew.VECTOR2I(MM(prev[0]), MM(prev[1])))
                t.SetEnd(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
                t.SetWidth(MM(w))
                t.SetLayer(LAYER[layer])
                t.SetNet(self.nets[net])
                self.b.Add(t)
                self.count['track'] += 1
            prev = p

    def via(self, net, x, y, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        try:
            v.SetWidth(pcbnew.F_Cu, MM(d))
        except TypeError:
            v.SetWidth(MM(d))
        v.SetDrill(MM(drill))
        v.SetNet(self.nets[net])
        self.b.Add(v)
        self.count['via'] += 1

    def vias(self, net, xs, ys, d=0.8, drill=0.4):
        for x in xs:
            for y in ys:
                self.via(net, x, y, d, drill)

    def zone(self, net, layer, pts, prio=0, solid=True, clearance=0.3, name=''):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(LAYER[layer])
        z.SetNet(self.nets[net])
        o = z.Outline()
        o.NewOutline()
        for x, y in pts:
            o.Append(MM(x), MM(y))
        z.SetAssignedPriority(prio)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(0.25))
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        if name:
            z.SetZoneName(name)
        self.b.Add(z)
        self.count['zone'] += 1

    def fill_and_save(self, path):
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        self.b.BuildConnectivity()
        self.b.Save(path)


def sh(pts, dx):
    return [(p[0] + dx, p[1]) if isinstance(p, tuple) else p for p in pts]


# ------------------------------------------------------------------------------------ planes
def planes(B):
    B.zone('GND', 'In1', GND_CTRL, solid=False, clearance=0.25, name='GND_In1_control')
    B.zone('GND', 'In1', GND_BAND, prio=1, solid=True, clearance=0.25, name='GND_In1_band')
    B.zone('GND', 'B', GND_CTRL, solid=False, clearance=0.25, name='GND_B_control')
    B.zone('GND', 'B', GND_BAND, prio=1, solid=True, clearance=0.3, name='GND_B_band')
    # thermal vias of the buck's exposed pad: solid, a relief has no room for its spokes there
    B.zone('GND', 'B', [(162.4, 119.1), (166.6, 119.1), (166.6, 124.9), (162.4, 124.9)], prio=1, solid=True,
           clearance=0.25, name='GND_B_U4')
    # In2: VDC under the band + tongue up to the buck input (C20, C21, U4 pins 2-3)
    # ... and a notch up to y 128.9 on the left for the via array of R41 pad 2
    B.zone('VDC', 'In2', [(100, 128.9), (117.0, 128.9), (117.0, 133.2), (154.2, 133.2), (154.2, 120.8), (163.0, 120.8), (163.0, 133.2),
                          (173.4, 133.2), (175.54, 138.56), (180.7, 140.7), (198.5, 140.7), (198.5, 176.3), (100, 176.3)],
           solid=True, clearance=0.3, name='VDC_In2')
    B.zone('+3.3V', 'In2', [(100, 92), (176.2, 92), (176.2, 103.8), (152.5, 103.8), (152.5, 132.7),
                            (117.4, 132.7), (117.4, 128.4), (100, 128.4)], solid=False, clearance=0.25, name='3V3_In2')
    B.zone('+5V', 'In2', [(153.0, 104.3), (176.2, 104.3), (176.2, 119.5), (173.4, 119.5), (173.4, 132.7),
                          (163.5, 132.7), (163.5, 120.3), (153.0, 120.3)],
           solid=False, clearance=0.25, name='5V_In2')


# ------------------------------------------------------------------------------------ DC input
def dc_input(B):
    # J14 -> F1 pad 1, on both outer layers (both pads are through-hole)
    vdc_in = [(101.6, 156.0), (107.5, 156.0), (107.5, 165.7), (101.6, 165.7)]
    B.zone('VDC_IN', 'F', vdc_in, prio=2, name='VDC_IN_F')
    B.zone('VDC_IN', 'B', vdc_in, prio=2, name='VDC_IN_B')
    # F1 pad 2 -> D5 pad 1 -> R41 pad 1 (entered from its outer, south side)
    B.zone('VDC_F', 'F', [(101.6, 140.3), (112.7, 140.3), (112.7, 146.0), (107.5, 146.0), (107.5, 150.8),
                          (101.6, 150.8)], prio=2, name='VDC_F')
    # R41 pad 2 -> In2 VDC plane: F.Cu patch north and east of the pad + 17 vias (20 A, ~1.2 A each)
    B.zone('VDC', 'F', [(109.0, 129.3), (117.2, 129.3), (117.2, 134.9), (109.0, 134.9)], prio=2,
           name='VDC_R41')
    B.vias('VDC', [109.8, 111.4, 113.0, 114.6, 116.2], [130.0, 131.6, 133.2])
    B.vias('VDC', [114.2, 116.0], [134.4 - 0.0])
    # TVS D5 pad 2 -> GND planes
    for x, y in ((102.75, 133.5), (102.75, 134.7), (104.4, 136.2), (106.0, 136.2)):
        B.via('GND', x, y, 0.8, 0.4)
    B.track('GND', [(102.75, 133.5), (103.8, 133.5)], 0.6)
    B.track('GND', [(102.75, 134.7), (103.8, 134.7)], 0.6)
    B.track('GND', [(104.4, 136.2), (104.4, 135.2)], 0.6)
    B.track('GND', [(106.0, 136.2), (106.0, 135.2)], 0.6)
    # Kelvin pair R41 -> U11: taps at the inner pad edges, pair runs west of R41 then around U11
    B.track('VDC_F', [(110.4, 140.0), (110.4, 138.3), (108.2, 138.3), (107.65, 137.75), (107.65, 132.4),
                      (107.15, 131.9), (103.6, 131.9), (103.1, 131.4), (103.1, 125.0), (103.575, 124.525),
                      (104.095, 124.525)], 0.25)
    B.track('VDC', [(110.4, 135.0), (110.4, 136.7), (108.75, 136.7), (108.3, 136.25), (108.3, 131.75),
                    (107.8, 131.25), (104.095, 131.25), (104.095, 130.0)], 0.25)
    # J4 (GND welding pad): vias in the pad tie F.Cu/B.Cu pad copper to the In1 plane
    for dx, dy in ((-3.6, -3.6), (3.6, -3.6), (-3.6, 3.6), (3.6, 3.6), (-3.6, -1.2), (-3.6, 1.2),
                   (3.6, -1.2), (3.6, 1.2), (-1.2, -3.6), (1.2, -3.6), (-1.2, 3.6), (1.2, 3.6)):
        B.via('GND', 118.8 + dx, 170.2 + dy, 0.8, 0.4)


# ------------------------------------------------------------------------------------ bridges
BR = {  # phase: k, high-side gate net, low-side gate net, phase-out net
    'A': (0, 'Net-(Q1-PadG)', 'Net-(Q2-PadG)', 'Net-(U6-IN-)'),
    'B': (1, 'Net-(Q3-PadG)', 'Net-(Q4-PadG)', 'Net-(U7-IN-)'),
    'C': (2, 'Net-(Q5-PadG)', 'Net-(Q6-PadG)', 'Net-(U8-IN-)'),
}
ISLAND_TOP = {'A': 138.9, 'B': 143.6, 'C': 140.7}      # below the gate tracks that pass over the bridge


def bridge(B, ph):
    k, g_hs, g_ls, out = BR[ph]
    dx = k * PITCH
    top = ISLAND_TOP[ph]
    SH = 'SH' + ph

    def Z(net, pts, **kw):
        B.zone(net, 'F', sh(pts, dx), prio=2, **kw)

    def T(net, pts, w, layer='F'):
        B.track(net, sh(pts, dx), w, layer)

    # switch node: low-side drain, high-side source, shunt pad 1 (kept clear of the Kelvin pin of U6)
    Z(SH, [(113.6, 151.8), (118.4, 151.8), (118.4, 155.1), (123.4, 155.1), (123.4, 156.55),
           (121.1, 156.55), (121.1, 158.2), (113.6, 158.2)], name='SH' + ph)
    # GND: low-side source + ceramic GND pads, tail between the FETs for two more vias
    Z('GND', [(115.3, top), (119.05, top), (119.05, 149.5), (119.65, 149.5), (119.65, 152.2),
              (118.65, 152.2), (118.65, 151.0), (115.0, 151.0), (115.0, 149.65), (115.3, 149.65)],
      name='GND_' + ph)
    # VDC: high-side drain + ceramic VDC pads (+ bulk cap pad 1 for A)
    if ph == 'A':
        vdc = [(119.35, top), (133.3, top), (133.3, 152.7), (124.95, 152.7), (124.95, 154.35),
               (119.95, 154.35), (119.95, 149.5), (119.35, 149.5)]
    elif ph == 'B':
        vdc = [(119.35, top), (126.8, top), (126.8, 149.0), (124.95, 149.0), (124.95, 154.35),
               (119.95, 154.35), (119.95, 149.5), (119.35, 149.5)]
    else:
        vdc = [(119.35, top), (126.85, top), (126.85, 152.7), (124.95, 152.7), (124.95, 154.35),
               (119.95, 154.35), (119.95, 149.5), (119.35, 149.5)]
    Z('VDC', vdc, name='VDC_' + ph)

    # vias: GND to In1 + B.Cu, VDC to In2. Pitch >= 1.6 keeps copper webs in the planes they cross.
    gnd_col = {'A': [144.0, 145.6, 147.2, 148.8], 'B': [144.4, 146.0, 147.6, 149.2],
               'C': [144.0, 145.6, 147.2, 148.8]}[ph]
    B.vias('GND', [116.1 + dx], gnd_col)
    B.vias('GND', [119.2 + dx], [150.3, 151.7])
    if ph == 'A':
        B.vias('GND', [115.8 + dx, 117.225 + dx, 118.65 + dx], [139.7, 141.2, 142.7])
        B.vias('VDC', [122.3 + dx, 123.9 + dx, 125.5 + dx, 127.1 + dx], [141.5, 143.1, 144.7, 146.3, 147.9])
    elif ph == 'B':
        B.vias('VDC', [122.1 + dx, 123.7 + dx, 125.3 + dx], [144.5, 146.1, 147.7])
    else:
        B.vias('GND', [115.8 + dx, 117.225 + dx, 118.65 + dx], [141.5, 142.9])
        B.vias('VDC', [122.1 + dx, 123.7 + dx, 125.3 + dx], [141.5, 143.1, 144.7, 146.3, 147.9])

    # phase output: shunt pad 2 (outer side) -> welding pad
    if ph == 'A':
        # J5 (x 132.1..142.1) is 17 mm to the right, behind U6 and H3: cross on B.Cu, 10 vias left
        # of the shunt pad; a narrow F.Cu strip below U6 helps
        B.zone(out, 'F', [(112.3, 163.05), (120.95, 163.05), (120.95, 164.4), (133.0, 164.4), (133.0, 167.2),
                          (124.2, 167.2), (124.2, 164.9), (112.3, 164.9)], prio=2, name='PHASE_A_F')
        B.vias(out, [112.75, 113.8, 114.85, 115.9, 116.95], [163.5, 164.45])
        B.zone(out, 'B', [(112.3, 157.5), (129.5, 157.5), (129.5, 159.9), (142.4, 159.9), (142.4, 167.0),
                          (124.2, 167.0), (124.2, 164.9), (112.3, 164.9)], prio=2, name='PHASE_A_B')
    elif ph == 'B':
        # J6 (x 144.4..154.4) lies under the shunt
        B.zone(out, 'F', [(143.4, 163.05), (149.45, 163.05), (149.45, 164.45), (154.4, 164.45),
                          (154.4, 165.6), (143.4, 165.6)], prio=2, name='PHASE_B')
    else:
        # J7 (x 156.7..166.7) is 15 mm to the left: F.Cu block below the shunt, into the pad's east side
        B.zone(out, 'F', [(165.0, 163.6), (171.9, 163.6), (171.9, 163.05), (177.95, 163.05), (177.95, 175.2),
                          (165.0, 175.2)], prio=2, name='PHASE_C')

    # gate resistor -> gate
    T(g_ls, [(114.2, 148.41), (114.2, 149.7), (114.095, 150.2)], 0.4)
    T(g_hs, [(126.1, 155.41), (125.3, 155.6), (124.305, 155.75)], 0.3)
    # Kelvin pair: inner edges of the shunt pads -> AD8418A pin 8 (IN+) and pin 1 (IN-)
    T(SH, [(119.6, 157.9), (119.6, 160.2), (121.0, 160.2), (122.095, 159.1), (122.095, 158.6)], 0.25)
    T(out, [(119.6, 163.3), (119.6, 161.0), (121.0, 161.0), (122.095, 162.1), (122.095, 162.6)], 0.25)
    # GND of the sense amplifier (pins 2-3) and of its input divider / bypass caps -> In1
    T('GND', [(123.365, 163.075), (123.365, 162.3), (124.0, 161.6), (124.635, 162.3), (124.635, 163.075)], 0.3)
    T('GND', [(124.0, 161.6), (124.0, 160.9)], 0.3)
    B.via('GND', 124.0 + dx, 160.9)
    T('GND', [(115.9, 159.425), (115.9, 161.32), (113.9, 161.32)], 0.25)
    T('GND', [(114.9, 161.32), (114.9, 160.5)], 0.25)
    B.via('GND', 114.9 + dx, 160.5)


# ------------------------------------------------------------------------------------ gate drive
def gate_drive(B):
    t = B.track
    # --- phase A: U5 south pins 5 (GHA), 6 (SHA), 7 (GLA)
    # pair GHA/SHA: under the DRV caps, down between C31/C32 column and bridge B, then west between
    # the two bulk caps into R15 (keeps Q1 drain <-> C31 joined on F.Cu)
    t('GHA', [(148.45, 138.4), (148.45, 141.3), (147.35, 142.40), (140.75, 142.40), 0.4,
              (140.75, 153.59), (126.1, 153.59)], 0.24)
    t('SHA', [(148.95, 138.4), (148.95, 141.6), (147.68, 142.87), (145.0, 142.87), (144.88, 142.99), 0.4,
              (141.42, 142.99), (141.42, 154.26), (127.6, 154.26), (127.36, 154.5), 0.25,
              (125.3, 154.5), (125.0, 154.79), (123.0, 154.79), (123.0, 155.7)], 0.2)
    # GLA would cross the pair: hop on B.Cu, then F.Cu along the top of the band to R16
    t('GLA', [(149.45, 138.4), (149.45, 139.2), (150.0, 139.75), (150.0, 140.0)], 0.24)
    B.via('GLA', 150.0, 140.0)
    t('GLA', [(150.0, 140.0), (148.2, 138.2), (139.8, 138.2)], 0.4, 'B')
    B.via('GLA', 139.8, 138.2)
    t('GLA', [(139.8, 138.2), (114.55, 138.2), (114.2, 138.55), (114.2, 146.59)], 0.4)

    # --- phase B: U5 east pins 12 (GHB), 11 (SHB), 10 (GLB)
    t('GHB', [(150.6, 136.25), (156.27, 136.25), (156.62, 136.6), 0.4, (156.62, 153.24),
              (156.27, 153.59), (154.6, 153.59)], 0.24)
    t('SHB', [(150.6, 136.75), (155.6, 136.75), (155.95, 137.1), 0.4, (155.95, 152.1),
              (155.6, 152.45), (153.85, 152.45), 0.25, (153.5, 152.8), (153.5, 154.5), (153.2, 154.79),
              (151.5, 154.79), (151.5, 155.7)], 0.24)
    t('GLB', [(150.6, 137.25), (151.3, 137.25), (151.6, 137.55), 0.4, (151.6, 142.6), 0.2, (151.6, 142.99),
              (151.25, 143.34), (145.45, 143.34), (145.24, 143.55), (143.05, 143.55), (142.7, 143.9),
              (142.7, 144.3), 0.4, (142.7, 146.59)], 0.24)

    # --- phase C: U5 east pins 13 (GHC), 14 (SHC), 15 (GLC)
    t('GHC', [(150.6, 135.75), (156.5, 135.75), (156.63, 135.62), 0.4, (165.83, 135.62), (170.16, 139.95),
              (184.4, 139.95), (184.4, 153.59), (183.1, 153.59)], 0.24)
    t('SHC', [(150.6, 135.25), (156.0, 135.25), (156.3, 134.95), 0.4, (166.4, 134.95), (170.75, 139.3),
              (185.07, 139.3), (185.07, 154.5), (184.4, 154.5), 0.25, (182.3, 154.5), (182.0, 154.79),
              (180.0, 154.79), (180.0, 155.7)], 0.24)
    t('GLC', [(150.6, 134.75), (155.35, 134.75), (155.82, 134.28), 0.4, (169.6, 134.28)], 0.24)
    B.via('GLC', 169.6, 134.28)
    t('GLC', [(169.6, 134.28), (171.2, 135.88), (171.2, 141.3)], 0.4, 'B')
    B.via('GLC', 171.2, 141.3)
    t('GLC', [(171.2, 141.3), (171.2, 146.59)], 0.4)


# ------------------------------------------------------------------------------------ DRV8350S
def drv(B):
    t = B.track
    # GND pins into the exposed pad (it has its own thermal vias to In1/B.Cu)
    t('GND', [(149.95, 138.4), (149.95, 137.75), (150.6, 137.75)], 0.2)
    t('GND', [(149.95, 137.75), (149.6, 137.4)], 0.2)
    t('GND', [(150.6, 134.25), (150.1, 134.25), (149.7, 134.55)], 0.2)
    t('GND', [(145.8, 136.75), (146.7, 136.75)], 0.2)
    # DVDD -> C23, VGLS -> C24 (between the pads of C23)
    t('Net-(U5-DVDD)', [(145.8, 136.25), (144.0, 136.25)], 0.24)
    t('Net-(U5-VGLS)', [(145.8, 137.25), (145.2, 137.3), (143.3, 137.3), (142.9, 136.9), (142.5, 136.7)], 0.2)
    t('GND', [(142.3, 138.075), (144.0, 138.075)], 0.3)
    t('GND', [(141.1, 137.3), (141.5, 137.7), (141.9, 138.0)], 0.3)
    B.via('GND', 141.1, 137.3)
    # VM pins 2-3 -> C22, C25, C19; C19 pad 1 -> In2
    t('VDC', [(146.95, 138.4), (146.95, 139.15), (147.45, 139.15), (147.45, 138.4)], 0.24)
    t('VDC', [(146.95, 139.15), (146.67, 139.43), (146.67, 141.1), (146.09, 141.68), (141.6, 141.68),
              (140.5, 141.6)], 0.3)
    B.via('VDC', 140.5, 141.6)
    t('GND', [(141.6, 140.025), (140.5, 140.025)], 0.3)
    B.via('GND', 140.5, 140.025)
    # top of the SENS_VDC divider (R13 pad 2) -> In2
    t('VDC', [(137.325, 134.6), (138.4, 134.6)], 0.3)
    B.via('VDC', 138.4, 134.6)
    t('GND', [(145.1, 140.72), (145.78, 140.72)], 0.25)
    B.via('GND', 145.78, 140.72)
    # VCP -> C25 pad 2: cannot pass C26/C22 on F.Cu, short hop on B.Cu
    t('Net-(U5-VCP)', [(147.95, 138.4), (147.95, 139.6), (147.45, 140.1), (147.45, 140.7)], 0.24)
    B.via('Net-(U5-VCP)', 147.45, 140.7)
    t('Net-(U5-VCP)', [(147.45, 140.7), (146.25, 139.5), (143.6, 139.5), (143.15, 139.05)], 0.3, 'B')
    B.via('Net-(U5-VCP)', 143.15, 139.05)
    t('Net-(U5-VCP)', [(143.15, 139.05), (143.3, 139.8)], 0.25)
    if ROTATE_C26:
        f = B.b.FindFootprintByReference('C26')
        f.SetOrientationDegrees(180)
        t('Net-(U5-CPH)', [(146.45, 138.4), (146.45, 138.8), (145.85, 139.4), (145.58, 139.6)], 0.2)
        t('Net-(U5-CPL)', [(145.8, 137.75), (145.1, 137.75), (144.8, 138.05), (144.8, 139.0),
                           (144.62, 139.4)], 0.2)


# ------------------------------------------------------------------------------------ MCU bypass
def mcu(B):
    t, v = B.track, B.via
    # pin 6 (+3.3V) - C3
    t('+3.3V', [(119.75, 116.5), (118.6, 116.5), (118.0, 115.88), (117.05, 115.9)], 0.25)
    v('+3.3V', 117.05, 115.9)
    t('GND', [(118.0, 114.92), (117.05, 114.92)], 0.25)
    v('GND', 117.05, 114.92)
    # pins 100 (+3.3V), 99 (GND) - C6
    t('+3.3V', [(121.5, 112.25), (120.95, 112.3), (119.97, 113.28), (117.9, 113.28), (116.95, 113.3)], 0.25)
    v('+3.3V', 116.95, 113.3)
    t('GND', [(122.0, 112.25), (122.0, 111.2), (118.3, 111.2), (117.9, 111.6), (117.9, 112.32),
              (116.95, 112.32)], 0.25)
    v('GND', 116.95, 112.32)
    # pins 23 (GND), 24 (+3.3V) - C5, C15
    t('GND', [(119.75, 125.0), (118.0, 125.02), (116.6, 125.225), (116.0, 124.1)], 0.25)
    v('GND', 116.0, 124.1)
    t('+3.3V', [(119.75, 125.5), (118.73, 125.5), (118.25, 125.98), (118.0, 125.98)], 0.25)
    t('+3.3V', [(118.73, 125.5), (118.73, 127.8), (118.45, 128.08), (118.0, 128.08), (118.0, 128.9), (118.45, 129.3)], 0.25)
    v('+3.3V', 118.45, 129.3)
    t('GND', [(118.0, 127.12), (117.3, 127.7), (116.2, 127.7), (116.2, 127.95)], 0.2)      # C15 pad 2
    v('GND', 116.2, 127.95)
    # south side: pin 35 (GND), 36-37 (+3.3VA) - C16, C14, C13, C17, L1
    t('+3.3VA', [(126.5, 127.75), (126.5, 129.0), (126.32, 129.5), (126.32, 129.8)], 0.2)
    t('+3.3VA', [(127.0, 127.75), (127.0, 128.8), (126.5, 129.3)], 0.2)
    t('+3.3VA', [(121.125, 130.0), (121.125, 130.85), (128.825, 130.85), (128.825, 130.0)], 0.25)
    t('+3.3VA', [(124.22, 129.8), (124.22, 130.85)], 0.25)
    t('+3.3VA', [(126.32, 129.8), (126.32, 130.85)], 0.25)
    t('+3.3VA', [(123.45, 130.85), (123.45, 131.7), (122.688, 131.7)], 0.25)
    t('GND', [(126.0, 127.75), (126.0, 128.6), (125.65, 128.95), (122.675, 128.95), (122.675, 130.0)], 0.25)
    t('GND', [(125.25, 128.95), (125.18, 129.8)], 0.25)
    v('GND', 125.25, 128.95)
    t('GND', [(127.28, 129.8), (127.4, 129.1), (127.75, 128.95), (129.75, 128.95), (130.375, 130.0)], 0.25)
    v('GND', 128.3, 128.95)
    v('GND', 129.75, 128.95)
    t('+3.3V', [(121.112, 131.7), (120.1, 131.7)], 0.3)
    v('+3.3V', 120.1, 131.7)
    # pins 48 (GND), 49 (+3.3V) - C7, C12
    t('GND', [(132.5, 127.75), (132.5, 126.2)], 0.2)
    v('GND', 132.5, 126.2)
    t('+3.3V', [(133.0, 127.75), (133.0, 128.75), (132.7, 129.05), (132.52, 129.8)], 0.2)
    t('+3.3V', [(132.52, 129.8), (132.52, 130.85), (134.72, 130.85), (134.72, 129.8)], 0.25)
    t('+3.3V', [(133.6, 130.85), (133.6, 131.7)], 0.25)
    v('+3.3V', 133.6, 131.7)
    t('GND', [(133.48, 129.8), (133.75, 128.95)], 0.25)
    v('GND', 133.75, 128.95)
    t('GND', [(135.68, 129.8), (136.65, 129.8)], 0.25)
    v('GND', 136.65, 129.8)
    # pins 63 (GND), 64 (+3.3V) - C9
    t('GND', [(135.25, 120.0), (133.9, 120.0)], 0.2)
    v('GND', 133.9, 120.0)
    t('+3.3V', [(135.25, 119.5), (136.3, 119.5), (136.7, 119.9), (137.2, 119.98), (138.05, 120.0)], 0.2)
    v('+3.3V', 138.05, 120.0)
    t('GND', [(137.2, 119.02), (138.05, 119.02)], 0.25)
    v('GND', 138.05, 119.02)
    # pins 74 (GND), 75 (+3.3V) - C11, C18
    t('GND', [(135.25, 114.5), (133.9, 114.5)], 0.2)
    v('GND', 133.9, 114.5)
    t('+3.3V', [(135.25, 114.0), (136.2, 114.0), (136.6, 114.4), (137.2, 114.48), (138.05, 114.5)], 0.2)
    v('+3.3V', 138.05, 114.5)
    t('GND', [(137.2, 113.52), (138.05, 113.52)], 0.25)
    v('GND', 138.05, 113.52)
    t('+3.3V', [(137.5, 112.175), (138.55, 112.175)], 0.3)
    v('+3.3V', 138.55, 112.175)
    t('GND', [(137.5, 110.625), (138.55, 110.625)], 0.3)
    v('GND', 138.55, 110.625)


# ------------------------------------------------------------------------------------ buck LMR38020
def buck(B):
    t, v = B.track, B.via
    # input loop: C20/C21 -> VIN pins 2-3, GND pads -> pin 1 and exposed pad
    t('VDC', [(156.1, 122.2), (159.1, 122.0), (161.8, 122.0)], 0.8)
    t('VDC', [(161.8, 121.365), (161.8, 122.635)], 0.5)
    t('GND', [(156.1, 119.7), (159.1, 119.85), (161.8, 120.095), (163.6, 120.2)], 0.6)
    for x, y in ((156.3, 123.8), (157.2, 123.8)):
        v('VDC', x, y)
        t('VDC', [(x, y), (x, 122.8)], 0.5)
    v('VDC', 157.91, 122.1)
    for x, y in ((155.5, 118.2), (156.7, 118.2)):
        v('GND', x, y)
        t('GND', [(x, y), (x, 119.3)], 0.5)
    v('GND', 159.1, 118.6)
    t('GND', [(159.1, 118.6), (159.1, 119.6)], 0.5)
    # switch node and bootstrap
    t('Net-(U4-SW)', [(167.2, 120.095), (166.9, 119.4), (166.2, 117.6)], 0.6)
    t('Net-(U4-SW)', [(169.4, 120.32), (168.6, 120.1), (167.2, 120.095)], 0.3)
    t('Net-(U4-BOOT)', [(169.4, 121.28), (167.2, 121.365)], 0.3)
    # output: L2 pad 1 -> C29 pad 1, vias to the In2 +5V area; C29 pad 2 -> GND planes
    t('+5V', [(162.0, 107.2), (157.2, 107.2), (157.2, 113.475), (155.2, 113.475)], 1.0)
    for y in (109.0, 110.6):
        v('+5V', 157.2, y)
    for x in (154.3, 155.5):
        v('GND', x, 109.0)
        t('GND', [(x, 109.0), (x, 110.2)], 0.5)


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
        B.clear()
        planes(B)
        dc_input(B)
        for ph in 'ABC':
            bridge(B, ph)
        gate_drive(B)
        drv(B)
        mcu(B)
        buck(B)
        B.fill_and_save(work)
        shutil.copyfile(work, dst)
    print('added', B.count)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
