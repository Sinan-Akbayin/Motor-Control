"""Step 11d2: restore footprint metadata from the library footprints (next link after silk_11d.py).

Usage (KiCad python, run from the repo root): fp_meta_11d.py <in.kicad_pcb> <out.kicad_pcb>

Since step 11.0 the board footprint copies carried no attributes, 3D models,
description or keywords, so DRC reported 155 lib_footprint_mismatch warnings.
This step loads every footprint's library copy through the project fp-lib-table
(project libraries under BLDC_V_0.1/) and KiCad's standard table, and copies ONLY:
  - attributes (SMD / through-hole / unspecified, exclude from position files,
    exclude from BOM, board-only, ...); the board's own DNP flag is kept, never set
    from the library (the schematic has no DNP / BOM / position exclusions)
  - 3D model list (file, offset, rotation, scale, opacity, show)
  - library description and keywords
No pads, graphics, courtyards, positions, rotations, reference/value texts, nets or copper.
Left as lib_footprint_mismatch on purpose (geometry, 2026-11-12): R15 R16 R20 R21 R25 R26 L3
(R_0805), U2, U4, J1 differ by 1 nm rounding in pads or fab/silk graphics; L2's library copy
also has an F.Cu keepout (no tracks/vias/pour under the body) that the board copy lacks.
Library footprint fields such as KiLib_Generator are not copied: DRC does not compare them.
Run on a copy in a scratch folder; only the .kicad_pcb goes back to the project.
"""
import os, re, sys
import pcbnew

SYS = 'C:/Program Files/KiCad/10.0/share/kicad'
PRJ = os.path.abspath('BLDC_V_0.1').replace(os.sep, '/')


def lib_table():
    def read(path, subs):
        t = {}
        txt = open(path, encoding='utf-8').read()
        for n, u in re.findall(r'\(name "([^"]+)"\)\s*\(type "[^"]+"\)\s*\(uri "([^"]+)"\)', txt):
            for k, v in subs.items():
                u = u.replace('${%s}' % k, v)
            t[n] = u
        return t
    t = read(SYS + '/template/fp-lib-table', {'KICAD10_FOOTPRINT_DIR': SYS + '/footprints'})
    t.update(read(os.path.join(PRJ, 'fp-lib-table'), {'KIPRJMOD': PRJ}))  # project wins
    return t


def copy_meta(f, L):
    dnp = f.GetAttributes() & pcbnew.FP_DNP
    f.SetAttributes((L.GetAttributes() & ~pcbnew.FP_DNP) | dnp)
    f.Models().clear()
    for m in L.Models():
        f.Add3DModel(m)
    f.SetLibDescription(L.GetLibDescription())
    f.SetKeywords(L.GetKeywords())


def main(src, dst):
    T = lib_table()
    b = pcbnew.LoadBoard(src)
    cache, missing, still = {}, [], []
    for f in b.GetFootprints():
        fid = f.GetFPID()
        key = (fid.GetLibNickname().wx_str(), fid.GetLibItemName().wx_str())
        if key not in cache:
            try:
                cache[key] = pcbnew.FootprintLoad(T[key[0]], key[1])
            except Exception:
                cache[key] = None
        L = cache[key]
        if L is None:
            missing.append(f.GetReference()); continue
        copy_meta(f, L)
        if f.FootprintNeedsUpdate(L):
            still.append('%s(%s)' % (f.GetReference(), key[1]))
    b.Save(dst)
    print('footprints', len(b.GetFootprints()), 'types', len(cache))
    print('library copy not found:', ' '.join(missing) or '-')
    print('still differ from library:', ' '.join(still[:20]) or '-', '(%d)' % len(still))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
