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
(R_0805), U2, U4, J1 differ by 1 nm rounding in pads or fab/silk graphics (L2's keepout: see 11d5).
Library footprint fields such as KiLib_Generator are not copied: DRC does not compare them.
Run on a copy in a scratch folder; only the .kicad_pcb goes back to the project.

Step 11d3 (2026-11-12): MODELS below gives a 3D body to footprints whose library has no model or
names a file that does not exist on this machine. It replaces the library model list for that
footprint type. Paths use KiCad path variables only; every file is checked at build time.
Source rule: a = file shipped with the part's own library, b = standard KiCad model of the same
package, c = close generic body (differences noted). Offsets in mm (KiCad 3D axes: +y = up on the
board picture, i.e. -y in board coordinates), rotation in degrees about x/y/z.
No body on purpose: MountingHole_3.2mm_M3 (H1-H4), Power_Welding_Pad_10x10mm (J4-J7, J14).

Step 11d5 (2026-11-12): rule areas (keepouts) that a footprint's library copy has and the board copy
lacks are copied in, placed with the footprint's position and rotation, only for refs in RULE_AREA_REFS
(they change copper); any other footprint with a rule-area difference is printed, not changed.
Zones are refilled after that (board rules from the .kicad_pro/.kicad_dru next to <in>), so this
step also holds the board's final zone fill. L2 (CDRH127): F.Cu, no tracks / vias / copper pour.
"""
import os, re, sys
import pcbnew

SYS = 'C:/Program Files/KiCad/10.0/share/kicad'
PRJ = os.path.abspath('BLDC_V_0.1').replace(os.sep, '/')
STD = '${KICAD10_3DMODEL_DIR}/'
LIBS = '${KIPRJMOD}/Libraries/'

# footprint item name -> (model path, offset xyz, rotation xyz, scale xyz, rule / note)
MODELS = {
    'LQFP100-14x14mm':  (STD + 'Package_QFP.3dshapes/LQFP-100_14x14mm_P0.5mm.step', (0, 0, 0), (0, 0, 0), (1, 1, 1), 'b'),
    'SOT23_TO-236AB_NEX': (STD + 'Package_TO_SOT_SMD.3dshapes/SOT-23.step', (0, 0, 0), (0, 0, -90), (1, 1, 1),
                           'b; board fp has pins 1/2 at the bottom, std at the left: z -90'),
    'TI_RTV0032E_DRV8350S': (STD + 'Package_DFN_QFN.3dshapes/QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm.step', (0, 0, 0), (0, 0, 0), (1, 1, 1),
                             'b; same pads and pin-1 corner, QFN 0.9 mm high vs WQFN 0.8 mm'),
    'Infineon_PG-WSON-8_BSC070N10NS5SC': (STD + 'Package_TO_SOT_SMD.3dshapes/TDSON-8-1.step', (0, 0, 0), (0, 0, -90), (1, 1, 1),
                                         'b; 5x6 mm power SON body; board fp has G/S at the bottom, std at the left: z -90'),
    'TI_SO-PowerPAD-8_ThermalVias': (STD + 'Package_SO.3dshapes/HTSOP-8-1EP_3.9x4.9mm_P1.27mm.step', (0, 0, 0), (0, 0, 0), (1, 1, 1),
                                     'b; library names ..._Pitch1.27mm.step, file is ..._P1.27mm.step'),
    'SOP-8_6.62x9.15mm_P2.54mm': (STD + 'Package_SO.3dshapes/SOP-8_6.605x9.655mm_P2.54mm.step', (0, 0, 0), (0, 0, 0), (1, 1, 1),
                                  'c; library model file missing; pad row 8.7 vs 9.06 mm apart'),
    # J1: the real Molex STEP (TraceParts, Y-up, not committed) when present, else the 47346 stand-in (see J1_REAL below)
    'USB_Micro-AB_Molex_47590-0001': (STD + 'Connector_USB.3dshapes/USB_Micro-B_Molex_47346-0001.step', (0, 1.56, 0), (0, 0, 0), (1, 1, 1),
                                      'c; Micro-B body of the same size, pin row moved 1.56 mm to this origin'),
    'Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin': (STD + 'Fuse.3dshapes/Fuseholder_Blade_Mini_Keystone_3568.step', (-0.36, 0, 0), (0, 0, 0), (1, 1, 1),
                                                     'c; no ATO model installed: Mini-blade holder, smaller body, 4 legs'),
    'CONN_15EDGVC-3.5-03P-1X_DEG': (STD + 'Connector_Phoenix_MC.3dshapes/PhoenixContact_MCV_1,5_3-G-3.5_1x03_P3.50mm_Vertical.step', (0, 0, 0), (0, 0, 0), (1, 1, 1),
                                    'c; same 3.5 mm 3-pin vertical header, Phoenix MCV body'),
    'ACM2012_TDK': (LIBS + 'ul_ACM2012-900-2P-T002/ACM2012_TDK.step', (0, 0, 0), (0, 0, 0), (1, 1, 1), 'a; STEP in the part library folder'),
    'B0505S-1WR2_MNS': (LIBS + 'ul_B0505S-1WR2/B0505S-1WR2_MNS.step', (0, 0, 0), (0, 0, 0), (1, 1, 1), 'a; STEP in the part library folder'),
    'IND_CDRH127&slash_LDNP-470MC_SUM': (LIBS + 'ul_CDRH127-LDNP-470MC/IND_CDRH127LDNP-470MC_SUM.step', (0, 0, 0), (0, 0, 0), (1, 1, 1),
                                         'a; STEP in the part library folder'),
}

# Real J1 model: x -90 makes the STEP's Y-up body stand on the board; y 1.39 puts the front flange on the fab front
# line (1.35 mm past the edge), legs in the slots, pegs in the round holes, pin tails on pads 1-5; z 1.245 = pin tails
# on the copper (checked with top / bottom / rear renders, 2026-11-12)
J1_REAL = ('${KIPRJMOD}/BLDC_Project.3dshapes/Molex_47590-0001.stp', (0, 1.39, 1.245), (-90, 0, 0), (1, 1, 1),
           'a; Molex STEP from TraceParts, local only (gitignored)')


def model_file(path):
    p = path.replace('${KICAD10_3DMODEL_DIR}', SYS + '/3dmodels').replace('${KIPRJMOD}', PRJ)
    return p if os.path.isfile(p) else None


def set_model(f, spec):
    path, off, rot, sc, _ = spec
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(*off)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    m.m_Scale = pcbnew.VECTOR3D(*sc)
    m.m_Show = True
    m.m_Opacity = 1.0
    f.Models().clear()
    f.Add3DModel(m)


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


RULE_AREA_REFS = {'L2'}


def copy_rule_areas(f, L):
    """Add the library's rule areas to the board footprint if it has none. Returns a note or None."""
    lz = [z for z in L.Zones() if z.GetIsRuleArea()]
    if not lz or any(z.GetIsRuleArea() for z in f.Zones()):
        return None
    if f.GetReference() not in RULE_AREA_REFS:
        return 'not applied'
    if f.IsFlipped():
        return 'not applied (bottom side)'
    for z in lz:
        n = pcbnew.ZONE(z)
        n.SetParent(f)
        n.Rotate(pcbnew.VECTOR2I(0, 0), f.GetOrientation())
        n.Move(f.GetPosition())
        f.Add(n)
    return 'added %d' % len(lz)


def copy_meta(f, L):
    dnp = f.GetAttributes() & pcbnew.FP_DNP
    f.SetAttributes((L.GetAttributes() & ~pcbnew.FP_DNP) | dnp)
    f.Models().clear()
    for m in L.Models():
        f.Add3DModel(m)
    f.SetLibDescription(L.GetLibDescription())
    f.SetKeywords(L.GetKeywords())


def main(src, dst):
    if model_file(J1_REAL[0]):
        MODELS['USB_Micro-AB_Molex_47590-0001'] = J1_REAL
        print('J1: real Molex 47590-0001 model')
    else:
        print('J1: real model absent, stand-in 47346 used')
    T = lib_table()
    b = pcbnew.LoadBoard(src)
    cache, missing, still, used = {}, [], [], {}
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
        note = copy_rule_areas(f, L)
        if note:
            print('rule areas %s: %s' % (f.GetReference(), note))
        if key[1] in MODELS:
            set_model(f, MODELS[key[1]])
            used.setdefault(key[1], []).append(f.GetReference())
        elif f.FootprintNeedsUpdate(L):
            still.append('%s(%s)' % (f.GetReference(), key[1]))
    for name, spec in MODELS.items():
        if not model_file(spec[0]):
            print('WARNING model file missing:', name, spec[0])
        if name not in used:
            print('WARNING model table entry not used:', name)
    nomodel = [f.GetReference() for f in b.GetFootprints()
               if not any(model_file(m.m_Filename) for m in f.Models())]
    print('3D model table: %d types, %d footprints' % (len(used), sum(len(v) for v in used.values())))
    print('footprints without a resolving model:', ' '.join(sorted(nomodel)) or '-')
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    b.Save(dst)
    print('footprints', len(b.GetFootprints()), 'types', len(cache))
    print('library copy not found:', ' '.join(missing) or '-')
    print('still differ from library:', ' '.join(still[:20]) or '-', '(%d)' % len(still))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
