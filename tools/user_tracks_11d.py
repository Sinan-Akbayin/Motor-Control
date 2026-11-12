"""user_tracks_11d.py src dst : apply the user's GUI track edits (2026-11-12) to the routed board.

Data: tools/user_tracks_11d.txt, one segment per line: sign|layer|net|ax ay|bx by|width (mm).
'-' lines are removed (must match exactly one track: net, layer, width, end points in either order, 1 nm),
'+' lines are added. The edits came from the user's GUI copy pcb_user_edit_2026-11-12 (11d4 + 45-degree
corner mitres on 50 net/layer pairs, approved 2026-11-12). Runs after silk_11d and before fp_meta_11d,
whose final zone refill covers these tracks. Run with KiCad python; stops with an error on any mismatch.
"""
import os
import sys
import pcbnew

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_tracks_11d.txt')
def NM(v):
    return int(round(v * 1e6))   # exact nm (pcbnew.FromMM truncates, e.g. 130.795 -> 130.794999)


def load():
    rem, add = [], []
    for line in open(DATA, encoding='utf-8'):
        if line[:1] not in '+-':
            continue
        sign, lay, net, a, b, w = line.rstrip('\n').split('|')
        ax, ay = map(float, a.split()); bx, by = map(float, b.split())
        (rem if sign == '-' else add).append((lay, net, NM(ax), NM(ay), NM(bx), NM(by), NM(float(w))))
    return rem, add


def same(t, s):
    lay, net, ax, ay, bx, by, w = s
    p, q = t.GetStart(), t.GetEnd()
    def near(u, x, y):
        return abs(u.x - x) <= 1 and abs(u.y - y) <= 1
    return (t.GetLayerName() == lay and t.GetNetname() == net and abs(t.GetWidth() - w) <= 1 and
            ((near(p, ax, ay) and near(q, bx, by)) or (near(p, bx, by) and near(q, ax, ay))))


def main(src, dst):
    rem, add = load()
    b = pcbnew.LoadBoard(src)
    segs = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    gone = []
    for s in rem:
        hits = [t for t in segs if same(t, s)]
        if len(hits) != 1:
            sys.exit('ERROR: remove %s matched %d tracks' % (s[:2] + tuple(pcbnew.ToMM(v) for v in s[2:]), len(hits)))
        gone.append(hits[0]); segs.remove(hits[0])
    for t in gone:
        b.Remove(t)
    nets = b.GetNetsByName()
    for lay, net, ax, ay, bx, by, w in add:
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(ax, ay)); t.SetEnd(pcbnew.VECTOR2I(bx, by)); t.SetWidth(w)
        t.SetLayer(b.GetLayerID(lay)); t.SetNet(nets[net])
        b.Add(t)
    b.BuildConnectivity()
    b.Save(dst)
    print('user tracks: removed %d, added %d' % (len(gone), len(add)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
