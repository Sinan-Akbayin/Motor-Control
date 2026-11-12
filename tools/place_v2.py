"""Placement v2 for BLDC_V_0.1 (run with KiCad's bundled Python, KiCad closed or on a copy).

usage:
  python place_v2.py place <in.kicad_pcb> <out.kicad_pcb>   # clear copper, place parts, new outline
  python place_v2.py check <board.kicad_pcb> [ref.kicad_pcb] # courtyard overlaps, off-board, ratsnest

Floorplan (see docs/WORK.md, step 11b2): power pads on the bottom edge, three half-bridges each
followed by a column of two bulk caps, DC input chain in a left column, DRV8350S above bridge B,
MCU rotated 270 deg north-west of the DRV, connectors on the top edge, buck/LDO/SWD between MCU
and the CAN isolation block in the top-right corner.

Groups are moved rigidly from their v1 coordinates (V1 below), so their internal arrangement stays.
"""
import math
import sys

import pcbnew

MM = pcbnew.FromMM

# ---------------------------------------------------------------- board frame
X_L, X_R = 100.0, 198.5
Y_T, Y_B = 92.0, 176.3
CORNER_R = 1.0
J1_NOTCH_HALF = 3.75          # J1 (USB, Molex 47590 r180) has its own notch Edge.Cuts
CONN_Y = Y_T + 7.6            # JST EH horizontal: anchor = pin 1, body 7.25 mm toward the edge
PAD_Y = 170.2                 # 10x10 welding pads on the bottom edge

# ---------------------------------------------------------------- v1 coordinates of moved groups
V1 = {
    # MCU cluster (rotated with U1 around its centre)
    'U1': (143.5, 122.0, 0),
    'C1': (131.6, 118.9, 0), 'C2': (128.8, 122.3, 90), 'Y1': (132.0, 121.8, 180), 'R1': (132.6, 124.6, 0),
    'C3': (134.0, 117.4, 90), 'C5': (134.0, 127.5, 90), 'C6': (133.9, 114.8, 90), 'C15': (134.0, 129.6, 90),
    'C9': (153.2, 121.5, 90), 'C11': (153.2, 116.0, 90), 'C18': (153.5, 113.4, 90),
    'C7': (149.0, 131.8, 0), 'C12': (151.2, 131.8, 0), 'C13': (145.6, 132.0, 0), 'C14': (142.8, 131.8, 0),
    'C16': (140.7, 131.8, 0), 'C17': (137.9, 132.0, 0), 'L1': (137.9, 133.7, 0),
    'C10': (128.8, 125.6, 90), 'C30': (132.6, 128.0, 90), 'R12': (131.0, 128.0, 90),
    # half-bridge A template (x0 = 130); B and C are the same at x0 = 144.5 / 159
    'Q1': (139.7, 153.1, 0), 'Q2': (133.3, 153.1, 180), 'R15': (143.4, 154.5, -90), 'R16': (131.5, 147.5, -90),
    'C39': (136.5, 148.7, 180), 'C40': (136.5, 146.8, 180), 'C42': (136.5, 144.6, 180),
    'R17': (131.2, 158.6, 90), 'R18': (133.2, 158.6, 90), 'R19': (136.5, 160.6, -90), 'U6': (141.3, 160.6, 90),
    'C38': (131.2, 161.8, 90), 'C41': (133.2, 161.8, 90),
    'Q3': (154.2, 153.1, 0), 'Q4': (147.8, 153.1, 180), 'R20': (157.9, 154.5, -90), 'R21': (146.0, 147.5, -90),
    'C44': (151.0, 148.7, 180), 'C45': (151.0, 146.8, 180), 'C47': (151.0, 144.6, 180),
    'R22': (145.7, 158.6, 90), 'R23': (147.7, 158.6, 90), 'R24': (151.0, 160.6, -90), 'U7': (155.8, 160.6, 90),
    'C43': (145.7, 161.8, 90), 'C46': (147.7, 161.8, 90), 'R11': (157.9, 150.6, 90),
    'Q5': (168.7, 153.1, 0), 'Q6': (162.3, 153.1, 180), 'R25': (172.4, 154.5, -90), 'R26': (160.5, 147.5, -90),
    'C49': (165.5, 148.7, 180), 'C50': (165.5, 146.8, 180), 'C52': (165.5, 144.6, 180),
    'R27': (160.2, 158.6, 90), 'R28': (162.2, 158.6, 90), 'R29': (165.5, 160.6, -90), 'U8': (170.3, 160.6, 90),
    'C48': (160.2, 161.8, 90), 'C51': (162.2, 161.8, 90),
    # DRV8350S cluster
    'U5': (158.5, 136.0, 90),
    'C19': (151.9, 140.8, 90), 'C22': (155.4, 141.2, 90), 'C23': (154.3, 137.3, 90), 'C24': (152.6, 137.3, 90),
    'C25': (153.6, 140.8, 90), 'C26': (155.4, 139.6, 0),
    # buck LMR38020 cluster
    'U4': (167.0, 128.0, 0), 'L2': (166.5, 117.5, -90), 'C20': (158.6, 127.0, 90), 'C21': (161.6, 126.8, 90),
    'C27': (171.9, 126.8, 90), 'C28': (172.1, 132.3, 0), 'C29': (157.4, 118.0, 90),
    'R7': (165.2, 132.3, 0), 'R8': (169.0, 132.3, 0), 'R9': (172.2, 130.2, 90), 'R10': (173.4, 130.2, 90),
    # isolated CAN cluster
    'U10': (179.6, 140.0, 0), 'U9': (176.0, 158.0, 0), 'J13': (194.3, 136.0, -90), 'J12': (195.8, 148.0, -90),
    'CR1': (187.6, 135.2, 0), 'L5': (187.6, 139.6, 90), 'R39': (187.6, 143.0, 90), 'C63': (187.3, 147.1, 0),
    'C64': (187.3, 145.4, 0), 'R40': (187.3, 149.3, 0), 'C62': (183.5, 146.5, 90), 'R38': (188.0, 156.0, 90),
    'C60': (179.0, 163.6, 0), 'C61': (184.5, 161.5, 90), 'L4': (179.0, 161.0, 0), 'C54': (175.5, 161.0, 0),
    'C53': (172.6, 136.6, 90), 'C56': (177.0, 133.8, 0), 'L3': (172.5, 134.0, 0),
    'TP1': (175.5, 168.5, 0), 'TP2': (180.0, 168.5, 0), 'TP3': (175.5, 164.5, 0),
    'TP4': (191.5, 153.0, 0), 'TP5': (195.5, 153.0, 0),
}

MCU_CL = ['C1', 'C2', 'Y1', 'R1', 'C3', 'C5', 'C6', 'C15', 'C9', 'C11', 'C18', 'C7', 'C12', 'C13', 'C14',
          'C16', 'C17', 'L1', 'C10', 'C30', 'R12']
BRIDGE = {  # v1 x0, parts
    'A': (130.0, ['Q1', 'Q2', 'R15', 'R16', 'C39', 'C40', 'C42', 'R17', 'R18', 'R19', 'U6', 'C38', 'C41']),
    'B': (144.5, ['Q3', 'Q4', 'R20', 'R21', 'C44', 'C45', 'C47', 'R22', 'R23', 'R24', 'U7', 'C43', 'C46', 'R11']),
    'C': (159.0, ['Q5', 'Q6', 'R25', 'R26', 'C49', 'C50', 'C52', 'R27', 'R28', 'R29', 'U8', 'C48', 'C51']),
}
DRV_CL = ['C19', 'C22', 'C23', 'C24', 'C25', 'C26']
BUCK_CL = ['U4', 'L2', 'C20', 'C21', 'C27', 'C28', 'C29', 'R7', 'R8', 'R9', 'R10']
CAN_CL = ['U10', 'U9', 'J13', 'J12', 'CR1', 'L5', 'R39', 'C63', 'C64', 'R40', 'C62', 'R38', 'C60', 'C61',
          'L4', 'C54', 'C53', 'C56', 'L3', 'TP1', 'TP2', 'TP3', 'TP4', 'TP5']

# ---------------------------------------------------------------- v2 anchors
BRIDGE_PITCH = 28.5                                 # 14.5 bridge + 13.1 cap column + gaps
X0 = {'A': 112.7, 'B': 112.7 + BRIDGE_PITCH, 'C': 112.7 + 2 * BRIDGE_PITCH}
CAP_DX = 18.94                                      # CP radial anchor (+ pad) from bridge x0
CAP_Y = (144.76, 157.96)
PAD_DX = 7.2                                        # phase pad centre (under the phase shunt)
MCU_C = (129.5, 119.0)
MCU_ROT = int(__import__('os').environ.get('MCU_ROT', 270))
DRV_C = (148.2, 136.0)
BUCK_D = (-2.5, -6.0)
CAN_D = (0.0, -31.0)


def build_table():
    t = {}
    # input chain, left column
    t.update({'J14': (106.5, PAD_Y, 0), 'F1': (104.5, 158.0, 90), 'D5': (105.2, 137.5, 90),
              'R41': (110.8, 137.5, 90), 'U11': (106.0, 127.0, 90), 'C65': (110.6, 127.0, 90)})
    # bridges, bulk caps, power pads
    caps = {'A': ('C31', 'C32'), 'B': ('C33', 'C34'), 'C': ('C35', 'C37')}
    pads = {'A': 'J5', 'B': 'J6', 'C': 'J7'}
    for ph, (x0_old, parts) in BRIDGE.items():
        dx = X0[ph] - x0_old
        for r in parts:
            x, y, a = V1[r]
            t[r] = (x + dx, y, a)
        for r, cy in zip(caps[ph], CAP_Y):
            t[r] = (X0[ph] + CAP_DX, cy, 0)
        t[pads[ph]] = (X0[ph] + PAD_DX, PAD_Y, 0)
    # bottom edge, left to right: VDC_IN, GND | A, B, C (user: supply and phases in separate groups).
    # A pad sits ~11 mm right of its shunt, under the A cap column; B and C stay under their shunts.
    t['J4'] = (118.8, PAD_Y, 0)
    t['J5'] = (131.0, PAD_Y, 0)
    # mounting holes
    t.update({'H1': (103.8, Y_T + 3.8, 0), 'H2': (194.7, Y_T + 3.8, 0),
              'H3': ((X0['B'] + X0['C']) / 2 + PAD_DX, 171.0, 0), 'H4': (194.5, 172.3, 0)})
    # DRV + cluster (translated)
    ux, uy, ua = V1['U5']
    t['U5'] = (DRV_C[0], DRV_C[1], ua)
    for r in DRV_CL:
        x, y, a = V1[r]
        t[r] = (x - ux + DRV_C[0], y - uy + DRV_C[1], a)
    t.update({'R5': (153.0, 133.5, 90), 'R6': (154.6, 133.5, 90)})
    # MCU + cluster (rotated -90 deg on screen = KiCad orientation 270)
    mx, my, _ = V1['U1']
    t['U1'] = (MCU_C[0], MCU_C[1], MCU_ROT)
    for r in MCU_CL:
        x, y, a = V1[r]
        dx, dy = x - mx, y - my
        th = math.radians(MCU_ROT)          # KiCad: positive = counter-clockwise on screen (y down)
        c, s = round(math.cos(th), 9), round(math.sin(th), 9)
        t[r] = (MCU_C[0] + dx * c + dy * s, MCU_C[1] - dx * s + dy * c, (a + MCU_ROT) % 360)
    # SENS_VDC divider below MCU, near pin 69
    t.update({'R13': (137.2, 133.0, 0), 'R14': (137.2, 135.0, 0), 'C36': (134.5, 134.0, 0)})
    # hall / temp input filters between J10 and MCU: row 1 = series R + filter C pairs, row 2 = pull-ups
    for i, r in enumerate(['R35', 'C57', 'R36', 'C58', 'R37', 'C59']):
        t[r] = (133.8 + 1.45 * i, 103.6, 90)
    for i, r in enumerate(['R32', 'R33', 'R34', 'R31']):
        t[r] = (133.8 + 1.8 * i, 107.2, 90)
    t['C55'] = (140.75, 107.2, 90)
    # top-edge connectors
    t.update({'J9': (110.64, CONN_Y, 0), 'J10': (129.54, CONN_Y, 0), 'J1': (150.6, Y_T + 1.1, 180),
              'J11': (159.14, CONN_Y, 0), 'J8': (107.4, 120.0, 90)})
    # USB ESD, SWD, LDO, boot jumper, LEDs
    t.update({'U3': (153.0, 104.2, 0), 'J2': (146.5, 108.0, 0),
              'U2': (146.0, 116.0, 0), 'C4': (140.8, 116.0, 90), 'C8': (146.0, 122.0, 0), 'D2': (151.5, 122.0, 0),
              'J3': (141.6, 127.0, 0), 'R3': (144.5, 126.0, 90),
              'D1': (148.0, 125.5, 0), 'D3': (148.0, 128.0, 0), 'D4': (148.0, 130.5, 0),
              'R2': (151.5, 125.5, 0), 'R4': (151.5, 128.0, 0), 'R30': (151.5, 130.5, 0)})
    # buck and CAN clusters (translated)
    for cl, (ddx, ddy) in ((BUCK_CL, BUCK_D), (CAN_CL, CAN_D)):
        for r in cl:
            x, y, a = V1[r]
            t[r] = (x + ddx, y + ddy, a)
    return t


# ---------------------------------------------------------------- actions
def outline(board, j1_x):
    lay = pcbnew.Edge_Cuts
    w = MM(0.1)

    def line(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(lay); s.SetWidth(w)
        s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
        board.Add(s)

    def arc(cx, cy, sx, sy, deg):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetLayer(lay); s.SetWidth(w)
        s.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy))); s.SetStart(pcbnew.VECTOR2I(MM(sx), MM(sy)))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(deg, pcbnew.DEGREES_T), True)
        board.Add(s)

    r = CORNER_R
    line(X_L + r, Y_T, j1_x - J1_NOTCH_HALF, Y_T)
    line(j1_x + J1_NOTCH_HALF, Y_T, X_R - r, Y_T)
    line(X_R, Y_T + r, X_R, Y_B - r)
    line(X_R - r, Y_B, X_L + r, Y_B)
    line(X_L, Y_B - r, X_L, Y_T + r)
    arc(X_L + r, Y_T + r, X_L, Y_T + r, 90)
    arc(X_R - r, Y_T + r, X_R - r, Y_T, 90)
    arc(X_R - r, Y_B - r, X_R, Y_B - r, 90)
    arc(X_L + r, Y_B - r, X_L + r, Y_B, 90)


def place(src, dst):
    b = pcbnew.LoadBoard(src)
    for t in list(b.GetTracks()):
        b.Delete(t)
    for z in [b.GetArea(i) for i in range(b.GetAreaCount())]:
        b.Delete(z)
    for d in list(b.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            b.Delete(d)
    table = build_table()
    missing = []
    for f in b.GetFootprints():
        r = f.GetReference()
        if r not in table:
            missing.append(r)
            continue
        x, y, a = table[r]
        f.SetOrientationDegrees(a)
        f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    outline(b, table['J1'][0])
    b.Save(dst)
    print('placed', len(table), 'parts; not in table:', missing or 'none')


def courtyard(f):
    s = f.GetCourtyard(pcbnew.F_CrtYd)
    if s.OutlineCount():
        return s
    s = pcbnew.SHAPE_POLY_SET()
    bb = f.GetBoundingBox(False)
    s.NewOutline()
    for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
                 (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
        s.Append(x, y)
    return s


def mst_length(b, skip=('GND', 'GND_ISO')):
    """Sum over nets of the minimum spanning tree of pad centres (a ratsnest length), in mm."""
    nets = {}
    for p in b.GetPads():
        n = p.GetNetname()
        if not n or n.startswith('unconnected') or n in skip:
            continue
        q = p.GetPosition()
        nets.setdefault(n, []).append((pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)))
    per = {}
    for n, pts in nets.items():
        if len(pts) < 2:
            continue
        inside, rest, tot = [pts[0]], pts[1:], 0.0
        while rest:
            d, k = min((min(math.dist(p, q) for q in inside), i) for i, p in enumerate(rest))
            tot += d
            inside.append(rest.pop(k))
        per[n] = tot
    return per


def check(path, ref=None):
    b = pcbnew.LoadBoard(path)
    fps = list(b.GetFootprints())
    cy = {f.GetReference(): courtyard(f) for f in fps}
    refs = sorted(cy)
    overlaps = []
    for i, a in enumerate(refs):
        ba = cy[a].BBox()
        for c in refs[i + 1:]:
            if not ba.Intersects(cy[c].BBox()):
                continue
            inter = pcbnew.SHAPE_POLY_SET(cy[a])
            inter.BooleanIntersection(cy[c])
            area = inter.Area() / 1e12 if inter.OutlineCount() else 0
            if area > 0.01:
                overlaps.append((area, a, c))
    print(f'courtyard overlaps: {len(overlaps)}')
    for area, a, c in sorted(overlaps, reverse=True):
        print(f'  {a:5s} {c:5s} {area:6.2f} mm2')
    board_bb = b.GetBoardEdgesBoundingBox()
    off = [f.GetReference() for f in fps
           if not board_bb.Contains(cy[f.GetReference()].BBox()) and f.GetReference() != 'J1']
    print('outside board edge bbox:', off or 'none')
    print(f'board: {pcbnew.ToMM(board_bb.GetWidth()):.1f} x {pcbnew.ToMM(board_bb.GetHeight()):.1f} mm')
    per = mst_length(b)
    print(f'ratsnest MST (no GND): {sum(per.values()):.0f} mm')
    if ref:
        old = mst_length(pcbnew.LoadBoard(ref))
        print(f'  reference board:     {sum(old.values()):.0f} mm')
        worst = sorted(per.items(), key=lambda kv: -kv[1])[:15]
        for n, l in worst:
            print(f'  {n.split("/")[-1]:22s} {l:6.1f}  (ref {old.get(n, 0):6.1f})')


if __name__ == '__main__':
    if sys.argv[1] == 'place':
        place(sys.argv[2], sys.argv[3])
    else:
        check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
