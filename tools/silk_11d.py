"""Step 11d: silkscreen clean-up of reference texts (next link after route_11c4.py).

Usage (KiCad python): silk_11d.py <in.kicad_pcb> <out.kicad_pcb>

Touches only the Reference fields of footprints: position, angle (0/90), size
(1.0/0.15 mm or 0.8/0.12 mm, JLCPCB minimum) and visibility. No footprint moves,
no copper, no footprint graphics. Value fields stay as they are (all hidden).

A reference keeps its current spot if that spot is legal. Otherwise candidate
spots around (and inside) the footprint are scored and the best legal one wins:
legal = text box clear of pad mask openings (0.15 mm), of any F.SilkS graphic or
already placed text (0.1 mm) and of the board edge (0.5 mm), and inside the board.
Hidden only when no legal spot exists within MAXD of the footprint.
Run on a copy in a scratch folder; only the .kicad_pcb goes back to the project.
"""
import sys, math
import pcbnew

MM = 1e6
CLR_PAD, CLR_SILK, CLR_EDGE, CLR_TXT = 0.15, 0.1, 0.5, 0.1
MAXD = 3.0                         # mm: max distance from the footprint box
SIZES = [(1.0, 0.15), (0.8, 0.12)]  # (height, line) in mm


def poly_list(item, layer, clr):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, int(clr * MM), int(0.005 * MM), pcbnew.ERROR_OUTSIDE)
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        pts = [(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]
        if len(pts) >= 3:
            out.append(pts)
    return out


def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def rect_hits_poly(r, pts, pb):
    x0, y0, x1, y1 = r
    if pb[2] < x0 or pb[0] > x1 or pb[3] < y0 or pb[1] > y1:
        return False
    for (x, y) in pts:                      # polygon vertex inside rect
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2   # rect centre inside polygon
    ins = False
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]; bx, by = pts[i - 1]
        if (ay > cy) != (by > cy) and cx < ax + (cy - ay) * (bx - ax) / (by - ay):
            ins = not ins
    if ins:
        return True
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for i in range(n):                      # edge crossings
        p, q = pts[i - 1], pts[i]
        for a, b in edges:
            if seg_x(p, q, a, b):
                return True
    return False


def seg_x(p1, p2, p3, p4):
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(p3, p4, p1), o(p3, p4, p2), o(p1, p2, p3), o(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def inside(pt, pts):
    cx, cy = pt; ins = False
    for i in range(len(pts)):
        ax, ay = pts[i]; bx, by = pts[i - 1]
        if (ay > cy) != (by > cy) and cx < ax + (cy - ay) * (bx - ax) / (by - ay):
            ins = not ins
    return ins


class Grid:
    def __init__(self, cell=2.0):
        self.c = cell; self.g = {}

    def add(self, obj, b):
        c = self.c
        for i in range(int(b[0] // c), int(b[2] // c) + 1):
            for j in range(int(b[1] // c), int(b[3] // c) + 1):
                self.g.setdefault((i, j), []).append(obj)

    def query(self, r):
        c = self.c; seen = set()
        for i in range(int(r[0] // c), int(r[2] // c) + 1):
            for j in range(int(r[1] // c), int(r[3] // c) + 1):
                for o in self.g.get((i, j), ()):
                    if id(o) not in seen:
                        seen.add(id(o)); yield o


def main(src, dst):
    b = pcbnew.LoadBoard(src)
    fps = list(b.Footprints())
    static = Grid()
    # pad mask openings on the top side (all pads, incl. NPTH / mounting holes)
    for f in fps:
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.F_Mask) or p.IsOnLayer(pcbnew.F_Cu) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                lay = pcbnew.F_Mask if p.IsOnLayer(pcbnew.F_Mask) else pcbnew.F_Cu
                for pts in poly_list(p, lay, CLR_PAD):
                    static.add((pts, bbox(pts), 'pad'), bbox(pts))
        for g in f.GraphicalItems():
            if g.GetLayer() != pcbnew.F_SilkS:
                continue
            for pts in poly_list(g, pcbnew.F_SilkS, CLR_SILK):
                static.add((pts, bbox(pts), 'silk'), bbox(pts))
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            for pts in poly_list(d, pcbnew.Edge_Cuts, CLR_EDGE):
                static.add((pts, bbox(pts), 'edge'), bbox(pts))
        elif d.GetLayer() == pcbnew.F_SilkS:
            for pts in poly_list(d, pcbnew.F_SilkS, CLR_SILK):
                static.add((pts, bbox(pts), 'silk'), bbox(pts))
    for v in b.GetTracks():   # untented vias would open the mask
        if v.GetClass() == 'PCB_VIA' and not v.IsTented(pcbnew.F_Mask):
            for pts in poly_list(v, pcbnew.F_Mask, CLR_PAD):
                static.add((pts, bbox(pts), 'via'), bbox(pts))
    outl = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outl, True)
    o0 = outl.Outline(0); outline = [(o0.CPoint(k).x / MM, o0.CPoint(k).y / MM) for k in range(o0.PointCount())]

    def fbox(f):
        cy = f.GetCourtyard(pcbnew.F_CrtYd)
        if cy.OutlineCount():
            bb = cy.BBox()
        else:
            bb = f.GetBoundingBox(False)
        return (bb.GetLeft() / MM, bb.GetTop() / MM, bb.GetRight() / MM, bb.GetBottom() / MM)

    boxes = {f.GetReference(): fbox(f) for f in fps}

    placed = Grid()
    near = {}
    for a, ab in boxes.items():
        near[a] = [(o, ob) for o, ob in boxes.items() if o != a and not (
            ob[2] < ab[0] - 8 or ob[0] > ab[2] + 8 or ob[3] < ab[1] - 8 or ob[1] > ab[3] + 8)]

    def legal(r):
        for pts, pb, _ in static.query(r):
            if rect_hits_poly(r, pts, pb):
                return False
        for q in placed.query(r):
            if not (q[2] + CLR_TXT < r[0] or q[0] - CLR_TXT > r[2] or q[3] + CLR_TXT < r[1] or q[1] - CLR_TXT > r[3]):
                return False
        for c in ((r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3])):
            if not inside(c, outline):
                return False
        return True

    def text_rect(fld):
        bb = fld.GetBoundingBox()
        return (bb.GetLeft() / MM, bb.GetTop() / MM, bb.GetRight() / MM, bb.GetBottom() / MM)

    def dist_box(pt, bx):
        dx = max(bx[0] - pt[0], 0, pt[0] - bx[2]); dy = max(bx[1] - pt[1], 0, pt[1] - bx[3])
        return math.hypot(dx, dy)

    def rect_box_gap(r, bx):
        dx = max(bx[0] - r[2], 0, r[0] - bx[2]); dy = max(bx[1] - r[3], 0, r[1] - bx[3])
        return math.hypot(dx, dy)

    def overlap_area(r, bx):
        w = min(r[2], bx[2]) - max(r[0], bx[0]); h = min(r[3], bx[3]) - max(r[1], bx[1])
        return w * h if w > 0 and h > 0 else 0.0

    # text extents per (size, angle) from a probe field
    probe = fps[0].Reference()
    keep = (probe.GetPosition(), probe.GetTextAngle(), probe.GetTextHeight(), probe.GetTextWidth(), probe.GetTextThickness())
    ext = {}
    for h, w in SIZES:
        for ang in (0, 90):
            probe.SetTextSize(pcbnew.VECTOR2I(int(h * MM), int(h * MM))); probe.SetTextThickness(int(w * MM))
            probe.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
            probe.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); probe.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
            r = text_rect(probe); c = probe.GetPosition()
            ext[(h, ang)] = (r, c.x / MM, c.y / MM)
    probe.SetPosition(keep[0]); probe.SetTextAngle(keep[1])
    probe.SetTextSize(pcbnew.VECTOR2I(keep[3], keep[2])); probe.SetTextThickness(keep[4])

    fext = {}

    def rect_for(fld, h, ang, x, y):
        # exact text box of this field for (size, angle), measured once and cached
        key = (fld.GetText(), h, ang)
        if key not in fext:
            st = (fld.GetPosition(), fld.GetTextAngle(), fld.GetTextSize(), fld.GetTextThickness(),
                  fld.GetHorizJustify(), fld.GetVertJustify())
            fld.SetTextSize(pcbnew.VECTOR2I(int(h * MM), int(h * MM))); fld.SetTextThickness(int(dict(SIZES)[h] * MM))
            fld.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
            fld.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); fld.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
            r = text_rect(fld); p = fld.GetPosition()
            fext[key] = (r[0] - p.x / MM, r[1] - p.y / MM, r[2] - p.x / MM, r[3] - p.y / MM)
            fld.SetPosition(st[0]); fld.SetTextAngle(st[1]); fld.SetTextSize(st[2]); fld.SetTextThickness(st[3])
            fld.SetHorizJustify(st[4]); fld.SetVertJustify(st[5])
        e = fext[key]
        return (x + e[0], y + e[1], x + e[2], y + e[3])

    def score(ref, r, h):
        bx = boxes[ref]
        c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        s = rect_box_gap(r, bx)
        own = dist_box(c, bx)
        for o, ob in near[ref]:
            if ob[2] < r[0] - 3 or ob[0] > r[2] + 3 or ob[3] < r[1] - 3 or ob[1] > r[3] + 3:
                continue
            a = overlap_area(r, ob)
            if a > 0:
                s += 3 + a            # text over another part's body
            elif dist_box(c, ob) < own - 0.05:
                s += 1.5              # closer to a neighbour than to its own part
        if h < 1.0:
            s += 0.6
        return s

    def candidates(ref, fld):
        bx = boxes[ref]
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        for h, _w in SIZES:
            for ang in (0, 90):
                r0 = rect_for(fld, h, ang, 0, 0); tw, th = r0[2] - r0[0], r0[3] - r0[1]
                yield (h, ang, cx, cy)  # inside the body
                for gap in (0.05, 0.3, 0.7, 1.2, 2.0):
                    for t in [k * 0.5 for k in range(-6, 7)]:
                        yield (h, ang, cx + t, bx[1] - gap - th / 2)  # north
                        yield (h, ang, cx + t, bx[3] + gap + th / 2)  # south
                        yield (h, ang, bx[0] - gap - tw / 2, cy + t)  # west
                        yield (h, ang, bx[2] + gap + tw / 2, cy + t)  # east

    def apply(fld, h, w, ang, x, y):
        fld.SetTextSize(pcbnew.VECTOR2I(int(h * MM), int(h * MM))); fld.SetTextThickness(int(w * MM))
        fld.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
        fld.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); fld.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        fld.SetPosition(pcbnew.VECTOR2I(int(round(x * 1000)) * 1000, int(round(y * 1000)) * 1000))

    # pass 1: keep references whose current spot is already legal
    todo = []; kept = 0
    for f in sorted(fps, key=lambda f: f.GetReference()):
        fld = f.Reference()
        if not fld.IsVisible() or fld.GetLayer() != pcbnew.F_SilkS:
            continue
        r = text_rect(fld)
        if legal(r) and score(f.GetReference(), r, 1.0) < 1.5:
            placed.add(r, r); kept += 1
        else:
            todo.append(f)

    # pass 2: candidates legal against the static obstacles and the kept texts,
    # computed once; then most constrained first, re-checked against texts placed meanwhile
    def static_cands(f):
        fld = f.Reference(); ref = f.GetReference(); out = []; seen = set()
        for h, ang, x, y in candidates(ref, fld):
            k = (h, ang, round(x, 2), round(y, 2))
            if k in seen:
                continue
            seen.add(k)
            r = rect_for(fld, h, ang, x, y)
            if rect_box_gap(r, boxes[ref]) > MAXD:
                continue
            if legal(r):
                out.append((score(ref, r, h), h, ang, x, y, r))
        out.sort(key=lambda t: t[0])
        return out

    def free_of_placed(r):
        for q in placed.query(r):
            if not (q[2] + CLR_TXT < r[0] or q[0] - CLR_TXT > r[2] or q[3] + CLR_TXT < r[1] or q[1] - CLR_TXT > r[3]):
                return False
        return True

    moved, hidden = [], []
    cands = {f.GetReference(): static_cands(f) for f in todo}
    pending = todo[:]
    while pending:
        live = {f.GetReference(): [c for c in cands[f.GetReference()] if free_of_placed(c[5])] for f in pending}
        pending.sort(key=lambda f: len(live[f.GetReference()]))
        f = pending.pop(0)
        c = live[f.GetReference()]
        cands[f.GetReference()] = c
        if not c:
            f.Reference().SetVisible(False); hidden.append(f.GetReference()); continue
        s, h, ang, x, y, r = c[0]
        w = dict(SIZES)[h]
        apply(f.Reference(), h, w, ang, x, y)
        rr = text_rect(f.Reference())
        placed.add(rr, rr)
        moved.append((f.GetReference(), round(s, 2), h, ang))

    b.Save(dst)
    print('kept', kept, 'moved', len(moved), 'hidden', len(hidden))
    print('small(0.8mm):', ' '.join(m[0] for m in moved if m[2] < 1.0))
    print('far/ambiguous(score>=1.5):', ' '.join('%s(%.1f)' % (m[0], m[1]) for m in moved if m[1] >= 1.5))
    print('hidden:', ' '.join(hidden))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
