# app.py — MatSci Explorer  (zero-scroll · tooltips · rank bars · position chart)
import bisect, os, json
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict
from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from dotenv import load_dotenv

from compounds import COMPOUNDS
import db as local_db
import pubchem as pc

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
local_db.init_db()

st.set_page_config(page_title="MatSci Explorer", page_icon="⚛",
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
header[data-testid="stHeader"] { display:none; }
#MainMenu, footer { visibility:hidden; }
.block-container { padding:0.4rem 1rem 0 1rem !important; max-width:100% !important; }
section[data-testid="stMain"] { overflow:hidden !important; }

.stApp { background:#0d1117; color:#e6edf3; }
[data-testid="stSidebar"] { background:#111318; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:0.1rem; }

/* Stat card */
.sc { background:#161b22; border:1px solid #21262d; border-radius:5px;
  padding:5px 10px; margin-bottom:4px; }
.sc-l { font-size:0.62rem; color:#8b949e; text-transform:uppercase;
  letter-spacing:.06em; display:block; }
.sc-l[title] { cursor:help; border-bottom:1px dotted #444; display:inline-block; }
.sc-v { font-size:0.86rem; color:#e6edf3; font-weight:500; }
.sc-n { font-size:0.67rem; color:#8b949e; }
/* Rank bar */
.sc-rank { height:4px; border-radius:2px; margin:3px 0 1px; background:#21262d; }
.sc-rank-f { height:100%; border-radius:2px; }

/* Scrollable panel */
.panel { overflow-y:auto; scrollbar-width:thin; scrollbar-color:#30363d transparent; padding-right:2px; }

/* KPI */
.krow { display:flex; gap:6px; margin:4px 0 6px; flex-wrap:nowrap; }
.kpi  { background:#161b22; border:1px solid #21262d; border-radius:6px;
  padding:5px 10px; flex:1; min-width:0; }
.kl   { font-size:0.58rem; color:#8b949e; text-transform:uppercase; letter-spacing:.06em;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.kv   { font-size:0.95rem; font-weight:600; color:#e6edf3;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ku   { font-size:0.62rem; color:#8b949e; }

/* Badges */
.badge { display:inline-block; background:#21262d; border:1px solid #30363d;
  border-radius:10px; padding:1px 9px; font-size:0.7rem; color:#8b949e;
  margin-right:4px; margin-bottom:3px; }
.badge-green  { border-color:#238636; color:#3fb950; background:#0d2818; }
.badge-orange { border-color:#9e6a03; color:#d29922; background:#2d1f00; }
.badge-red    { border-color:#8b1a1a; color:#f85149; background:#2d0000; }
.badge-blue   { border-color:#1f6feb; color:#58a6ff; background:#0d1f3c; }

.sh { font-size:0.62rem; color:#58a6ff; text-transform:uppercase;
  letter-spacing:.1em; margin:8px 0 4px; font-weight:700; }
.sh:first-child { margin-top:0; }
.cat-hdr { font-size:0.6rem; color:#58a6ff; text-transform:uppercase;
  letter-spacing:.1em; font-weight:700; margin:6px 0 2px; }
.na { color:#8b949e; font-style:italic; font-size:0.8rem; padding:6px 0; }

[data-testid="stSidebar"] .stButton > button {
  padding:2px 6px; font-size:0.72rem; border-radius:12px; min-height:0;
  height:auto; line-height:1.3; border:1px solid #30363d;
  background:#21262d; color:#c9d1d9; width:100%; }
[data-testid="stSidebar"] .stButton > button:hover {
  border-color:#58a6ff; color:#58a6ff; background:#0d1f3c; }

details summary { cursor:pointer; font-size:0.7rem; color:#58a6ff;
  text-transform:uppercase; letter-spacing:.07em; font-weight:700;
  margin:6px 0 3px; list-style:none; }
details summary::marker, details summary::-webkit-details-marker { display:none; }
details summary::before { content:"▶ "; font-size:0.6rem; }
details[open] summary::before { content:"▼ "; }
.why { background:#161b22; border-left:3px solid; border-radius:0 5px 5px 0;
  padding:8px 12px; font-size:0.8rem; line-height:1.65; color:#c9d1d9; margin-top:3px; }

/* Compact popover trigger buttons */
button[kind="secondary"] { padding:2px 8px !important; font-size:0.7rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Property help text ────────────────────────────────────────────────────────
HELP: dict[str, str] = {
    "Band Gap":        "Energy gap between valence and conduction bands (eV). 0 = metal. 0.5–3 eV = semiconductor. >5 eV = insulator. DFT values are typically 20–40% lower than experiment.",
    "CBM":             "Conduction Band Minimum — lowest energy available to a free electron. Its depth below vacuum sets the electron affinity of the surface.",
    "VBM":             "Valence Band Maximum — highest occupied electron state at 0 K. Gap = CBM − VBM.",
    "Ordering":        "FM = ferromagnetic (all spins aligned, acts as a magnet). AFM = antiferromagnetic (alternating ±, no net moment). FiM = ferrimagnetic (unequal opposing spins). NM = non-magnetic.",
    "Magnetization":   "Total magnetic moment per formula unit (μB). Pure Fe ≈ 2.2 μB/atom. High magnetization + high coercivity = strong permanent magnet candidate.",
    "Magnetic Sites":  "Atoms per unit cell with unpaired electrons contributing to the net magnetic moment. Transition metals and rare earths are common magnetic sites.",
    "Bulk K":          "Bulk modulus — resistance to uniform compression from all sides (GPa). Diamond ≈ 440. Steel ≈ 160. Rubber ≈ 0.002. Voigt average from the full elastic tensor.",
    "Shear G":         "Shear modulus — resistance to shape change without volume change (GPa). High G = hard to scratch. Steel ≈ 80. Ice ≈ 4. Voigt average.",
    "Young's E":       "Young's modulus — axial stiffness: stress / strain along one axis (GPa). Diamond ≈ 1050. Carbon fiber ≈ 300. Aluminum ≈ 70. Computed as E = 9BG / (3B+G).",
    "Poisson ν":       "Poisson ratio — lateral expansion when you compress axially. Cork ≈ 0 (good bottle stopper). Most metals 0.25–0.35. Near 0.5 = rubber-like (nearly incompressible).",
    "Anisotropy":      "Universal anisotropy index AU. 0 = same stiffness in all directions. >1 = significant directional variation. High AU predicts preferred cleavage planes.",
    "Specific E/ρ":    "Specific modulus = E / density (GPa·cm³/g). The figure of merit for lightweight stiff structures. Space elevator cables need E/ρ > 100. Steel ≈ 26. Diamond ≈ 350.",
    "Pugh B/G":        "Pugh ratio. B/G > 1.75 → ductile (deforms before breaking). B/G < 1.75 → brittle (shatters). Useful for ceramic screening.",
    "Therm. Cond.":    "Thermal conductivity (W/m·K). Diamond ≈ 2000. Copper ≈ 400. Steel ≈ 50. ZrO₂ ≈ 2 (great thermal barrier). Estimated from Debye temperature via Clarke/Cahill models.",
    "Debye Temp":      "Debye temperature Θ_D (K) — energy scale of phonons. High Θ_D = stiff bonds, high melting point. Diamond ≈ 2230 K. Lead ≈ 105 K.",
    "Total ε":         "Static dielectric constant — how much the material weakens an electric field at low frequency. Vacuum = 1. Silicon = 11.7. BaTiO₃ ≈ 1700. High ε = good capacitor, good plasma reflector.",
    "Electronic ε∞":   "High-frequency dielectric response from electron cloud distortion only. Active at optical frequencies. Related to refractive index: n = √ε∞.",
    "Ionic εᵢₒₙ":      "Contribution from polar bond vibrations (phonons). Active only at low / infrared frequencies. Large in ferroelectrics and perovskites.",
    "Refr. Index n":   "Refractive index n = √ε∞. Vacuum = 1. Glass ≈ 1.5. Diamond = 2.42. GaAs ≈ 3.6. High n = shiny surface, more reflective, light bends more at the interface.",
    "Reflectivity":    "Fraction of light reflected at normal incidence: R = ((n−1)/(n+1))². Glass ≈ 4%. Diamond ≈ 17%. GaAs ≈ 32%. High R = mirror-like surface.",
    "Energy Above Hull":"Distance above the convex hull (eV/atom). 0 = thermodynamic ground state. <0.025 = usually synthesizable. >0.1 = hard to make, tends to decompose.",
    "Formation Energy": "Energy per atom to form the compound from its elements (eV/atom). Negative = exothermic (atoms prefer to be together). More negative = more thermodynamically stable.",
    "Density":         "Crystallographic density (g/cm³) from unit cell mass and volume. Lithium ≈ 0.53. Aluminum ≈ 2.7. Iron ≈ 7.87. Osmium ≈ 22.6 (densest element).",
}

# ── DB column bounds for percentile rank bars ─────────────────────────────────
COL_BOUNDS: dict[str, str] = {
    "bandgap":                   "bandgap > 0",
    "young_modulus":             "young_modulus > 0 AND young_modulus < 5000",
    "k_voigt":                   "k_voigt > 0 AND k_voigt < 2000",
    "g_voigt":                   "g_voigt > 0 AND g_voigt < 2000",
    "density":                   "density > 0",
    "e_total":                   "e_total > 0 AND e_total < 200",
    "e_electronic":              "e_electronic > 0 AND e_electronic < 100",
    "refractive_index":          "refractive_index > 0 AND refractive_index < 20",
    "formation_energy_per_atom": "formation_energy_per_atom IS NOT NULL",
    "total_magnetization":       "total_magnetization > 0",
    "energy_above_hull":         "energy_above_hull >= 0",
    "thermal_conductivity":      "thermal_conductivity > 0",
    "debye_temperature":         "debye_temperature > 0",
    "poisson_ratio":             "poisson_ratio > 0 AND poisson_ratio < 0.6",
}


@st.cache_data(show_spinner=False)
def col_stats(col: str) -> dict:
    if col not in COL_BOUNDS:
        return {}
    where = COL_BOUNDS[col]
    with local_db.get_conn() as conn:
        rows = conn.execute(
            f"SELECT {col} FROM materials WHERE {col} IS NOT NULL AND {where} ORDER BY {col}"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    vals = [r[0] for r in rows]
    return {"sorted": vals, "n": len(vals), "total": total}


def pct_rank(raw_val, col: str):
    """Return 'top X%' float (0–100) — small number = impressive. None if unavailable."""
    if raw_val is None:
        return None
    stats = col_stats(col)
    if not stats or stats["n"] == 0:
        return None
    vals = stats["sorted"]
    idx = bisect.bisect_left(vals, raw_val)
    pct_from_bottom = idx / stats["n"] * 100
    if col in ("formation_energy_per_atom", "energy_above_hull"):
        # lower = better → top% = percent beaten (from bottom)
        return 100.0 - pct_from_bottom
    # higher = better → top% = percent above this value
    return pct_from_bottom  # pct that this value beats from bottom = fraction it's above


# Pre-warm stats cache at startup for instant rank bars on first load
for _c in COL_BOUNDS:
    col_stats(_c)


# ── Session state ─────────────────────────────────────────────────────────────
def _default():
    cat  = list(COMPOUNDS.keys())[0]
    name = list(COMPOUNDS[cat].keys())[0]
    return COMPOUNDS[cat][name]["mp_id"], name, COMPOUNDS[cat][name]

if "mp_id" not in st.session_state:
    mid, cn, cd = _default()
    st.session_state.mp_id         = mid
    st.session_state.compound_name = cn
    st.session_state.curated_data  = cd
if "ashby_mode" not in st.session_state:
    st.session_state.ashby_mode = False


# ── HTML helpers ──────────────────────────────────────────────────────────────
def badge(text, style=""):
    cls = f"badge badge-{style}" if style else "badge"
    return f'<span class="{cls}">{text}</span>'

def _rank_color(top_pct: float) -> str:
    if top_pct <= 25:  return "#3fb950"
    if top_pct <= 75:  return "#d29922"
    return "#f85149"

def sc(label: str, value: str, note: str = "",
       col: str = None, raw=None, tip: str = None) -> str:
    """
    Stat card.  col + raw → shows percentile rank bar.
                tip       → shows help tooltip on hover.
    """
    tip_attr = f' title="{tip.replace(chr(34), chr(39))}"' if tip else ""
    lbl_html = f'<span class="sc-l"{tip_attr}>{label}{"  ?" if tip else ""}</span>'
    note_html = f'<div class="sc-n">{note}</div>' if note else ""

    rank_html = ""
    if col is not None and raw is not None:
        top_pct = pct_rank(raw, col)
        if top_pct is not None:
            # bar fills proportionally to how much of DB this value beats
            beats_pct = 100.0 - top_pct  # for higher-is-better cols
            if col in ("formation_energy_per_atom", "energy_above_hull"):
                beats_pct = top_pct      # already fraction-beaten for lower-is-better
            color   = _rank_color(top_pct)
            n_total = col_stats(col).get("total", 6816)
            rank_html = (
                f'<div class="sc-rank"><div class="sc-rank-f" '
                f'style="background:{color};width:{beats_pct:.1f}%;"></div></div>'
                f'<div class="sc-n" style="color:{color};">Top {top_pct:.0f}% of {n_total:,}</div>'
            )

    return (f'<div class="sc">{lbl_html}'
            f'<div class="sc-v">{value}</div>'
            f'{note_html}{rank_html}</div>')

def sh(text):  return f'<div class="sh">{text}</div>'
def na(msg="Not available"): return f'<div class="na">{msg}</div>'
def kpi(label, value, unit=""):
    return (f'<div class="kpi"><div class="kl">{label}</div>'
            f'<div class="kv">{value}<span class="ku"> {unit}</span></div></div>')
def panel(html, height=345):
    return f'<div class="panel" style="height:{height}px;">{html}</div>'


# ── Structure / data loaders ──────────────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

@st.cache_data(show_spinner=False)
def load_structure(mp_id, api_key):
    s = local_db.get_structure(mp_id)
    if s: return s
    cp = os.path.join(CACHE_DIR, f"{mp_id}.json")
    if os.path.exists(cp):
        with open(cp) as f: return Structure.from_dict(json.load(f))
    if not api_key: return None
    from mp_api.client import MPRester
    with MPRester(api_key) as mpr:
        docs = mpr.materials.summary.search(
            material_ids=[mp_id],
            fields=["material_id","formula_pretty","formula_anonymous","symmetry",
                    "band_gap","cbm","vbm","is_gap_direct","total_magnetization",
                    "ordering","num_magnetic_sites","formation_energy_per_atom",
                    "energy_above_hull","decomposes_to","nsites","volume","density",
                    "density_atomic","nelements","elements","chemsys","theoretical",
                    "database_IDs","structure"],
        )
    if not docs: return None
    doc = docs[0]; sym = doc.symmetry
    db_ids = getattr(doc,"database_IDs",None) or {}
    icsd   = db_ids.get("icsd",[]) if isinstance(db_ids,dict) else []
    elems  = [str(e) for e in doc.elements] if doc.elements else None
    ordering = None
    if hasattr(doc,"ordering") and doc.ordering:
        ordering = str(doc.ordering.value) if hasattr(doc.ordering,"value") else str(doc.ordering)
    local_db.upsert(
        mp_id=doc.material_id, formula=doc.formula_pretty,
        crystal_system=sym.crystal_system.value if sym else None,
        space_group=sym.symbol if sym else None,
        bandgap=doc.band_gap, cbm=getattr(doc,"cbm",None),
        vbm=getattr(doc,"vbm",None), is_direct=doc.is_gap_direct,
        magnetization=doc.total_magnetization, ordering=ordering,
        num_magnetic_sites=getattr(doc,"num_magnetic_sites",None),
        formation_e=doc.formation_energy_per_atom, hull_e=doc.energy_above_hull,
        decomposes_to=getattr(doc,"decomposes_to",None),
        nsites=doc.nsites, volume=doc.volume, density=doc.density,
        density_atomic=getattr(doc,"density_atomic",None),
        nelements=getattr(doc,"nelements",None), elements=elems,
        chemsys=getattr(doc,"chemsys",None), theoretical=getattr(doc,"theoretical",None),
        icsd_ids=icsd, formula_anonymous=getattr(doc,"formula_anonymous",None),
        structure=doc.structure, tags=[],
    )
    return doc.structure

@st.cache_data(show_spinner=False)
def get_xrd(structure_json):
    s = Structure.from_dict(json.loads(structure_json))
    p = XRDCalculator(wavelength="CuKa").get_pattern(s)
    hkls = []
    for g in p.hkls:
        if g:
            hkl = g[0]["hkl"]
            hkls.append("(" + "".join(str(i) for i in hkl[:3]) + ")")
        else:
            hkls.append("")
    return {"two_theta": p.x.tolist(), "intensity": p.y.tolist(), "hkls": hkls}

@st.cache_data(show_spinner=False)
def get_pubchem(formula, name): return pc.lookup(formula, name)

def render_crystal(structure, accent, w=460, h=330):
    a,b,c = structure.lattice.abc
    sup = structure * (2 if a<10 else 1, 2 if b<10 else 1, 2 if c<10 else 1)
    cif = json.dumps(str(CifWriter(sup, symprec=None)))
    uid = f"v{abs(hash(structure.formula))%999999}"
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.4.2/3Dmol-min.js"></script>
<style>body{{margin:0;background:#0d1117;overflow:hidden}}#{uid}{{width:{w}px;height:{h}px}}</style>
</head><body><div id="{uid}"></div><script>
var v=$3Dmol.createViewer(document.getElementById('{uid}'),{{backgroundColor:'#0d1117'}});
v.addModel({cif},'cif');
v.setStyle({{}},{{sphere:{{radius:0.38,colorscheme:'Jmol'}},stick:{{radius:0.12,colorscheme:'Jmol'}}}});
v.addUnitCell({{box:{{color:'{accent}',linewidth:2}},alabel:'',blabel:'',clabel:''}});
v.zoomTo();v.spin({{axis:'y',speed:0.5}});v.render();
</script></body></html>"""


# ── Panel HTML builders ───────────────────────────────────────────────────────
def build_electronic(row):
    if not row: return na()
    h = sh("Electronic")
    bg = row.get("bandgap")
    if bg is not None:
        gtype = "Direct" if row.get("is_direct_gap")==1 else ("Indirect" if row.get("is_direct_gap")==0 else "")
        if bg == 0:   desc, note = "0.00 eV", "Metal"
        elif bg < 1:  desc, note = f"{bg:.3f} eV", "Narrow semiconductor"
        elif bg < 3:  desc, note = f"{bg:.3f} eV", "Semiconductor"
        elif bg < 5:  desc, note = f"{bg:.3f} eV", "Wide-gap"
        else:         desc, note = f"{bg:.3f} eV", "Insulator"
        h += sc("Band Gap", desc, f"{gtype} · {note}" if gtype else note,
                col="bandgap", raw=bg if bg>0 else None, tip=HELP["Band Gap"])
        pct   = min(bg/10*100, 100)
        color = "#f85149" if bg==0 else "#3fb950" if bg<3 else "#d29922"
        h += (f'<div style="background:#21262d;border-radius:3px;height:5px;margin:-1px 0 5px;">'
              f'<div style="background:{color};width:{pct}%;height:100%;border-radius:3px;"></div></div>')
    else:
        h += na("No bandgap")
    cbm = row.get("cbm"); vbm = row.get("vbm")
    if cbm is not None: h += sc("CBM", f"{cbm:.3f} eV", "Conduction band min", tip=HELP["CBM"])
    if vbm is not None: h += sc("VBM", f"{vbm:.3f} eV", "Valence band max",    tip=HELP["VBM"])
    h += sh("Magnetic")
    ordering = row.get("ordering"); mag = row.get("total_magnetization")
    ORDR = {"FM":("Ferromagnetic","All spins aligned"),"AFM":("Antiferromagnetic","Alternating ±"),
            "FiM":("Ferrimagnetic","Unequal opposing"),"NM":("Non-magnetic","No unpaired e⁻")}
    if ordering and ordering in ORDR:
        lbl, note = ORDR[ordering]; h += sc("Ordering", lbl, note, tip=HELP["Ordering"])
    elif ordering:
        h += sc("Ordering", ordering, tip=HELP["Ordering"])
    if mag is not None:
        h += sc("Magnetization", f"{mag:.3f} μB/f.u.",
                col="total_magnetization", raw=mag if mag>0 else None, tip=HELP["Magnetization"])
    nm = row.get("num_magnetic_sites")
    if nm: h += sc("Magnetic Sites", str(nm), "Atoms w/ unpaired e⁻", tip=HELP["Magnetic Sites"])
    return h


def build_mechanical(row):
    if not row: return na()
    h = sh("Elastic Moduli")
    if row.get("k_voigt") is None:
        return h + na("No elasticity data" if row.get("elastic_fetched")==1 else "Run fetch.py")
    B  = row.get("k_voigt"); G = row.get("g_voigt"); E = row.get("young_modulus")
    nu = row.get("poisson_ratio"); au = row.get("universal_anisotropy")
    ρ  = row.get("density"); tc = row.get("thermal_conductivity"); θD = row.get("debye_temperature")
    if B:  h += sc("Bulk K",    f"{B:.1f} GPa", "Compression resistance",
                   col="k_voigt", raw=B, tip=HELP["Bulk K"])
    if G:  h += sc("Shear G",   f"{G:.1f} GPa", "Shape change resistance",
                   col="g_voigt", raw=G, tip=HELP["Shear G"])
    if E:  h += sc("Young's E", f"{E:.1f} GPa", "Axial stiffness",
                   col="young_modulus", raw=E, tip=HELP["Young's E"])
    if nu is not None:
        h += sc("Poisson ν", f"{nu:.4f}", "Lateral contraction",
                col="poisson_ratio", raw=nu, tip=HELP["Poisson ν"])
    if au is not None:
        alab = "Isotropic" if au<0.1 else ("Mild" if au<1 else "High aniso.")
        h += sc("Anisotropy", f"{au:.3f}", alab, tip=HELP["Anisotropy"])
    if E and ρ:
        sm = E/ρ; flag = " ★" if sm>100 else ""
        h += sc("Specific E/ρ", f"{sm:.1f}{flag}", "GPa·cm³/g", tip=HELP["Specific E/ρ"])
    if B and G:
        pugh = B/G
        h += sc("Pugh B/G", f"{pugh:.2f}", "Ductile" if pugh>1.75 else "Brittle", tip=HELP["Pugh B/G"])
    h += sh("Thermal")
    if tc is not None:
        h += sc("Therm. Cond.", f"{tc:.2f} W/m·K", "Clarke/Cahill estimate",
                col="thermal_conductivity", raw=tc, tip=HELP["Therm. Cond."])
    if θD is not None:
        h += sc("Debye Temp", f"{θD:.0f} K", "Phonon energy scale",
                col="debye_temperature", raw=θD, tip=HELP["Debye Temp"])
    return h


def build_dielectric(row):
    if not row: return na()
    h = sh("Dielectric & Optical")
    if row.get("e_total") is None:
        return h + na("No dielectric data" if row.get("dielectric_fetched")==1 else "Run fetch.py")
    e_tot = row.get("e_total"); e_ion = row.get("e_ionic")
    e_elec = row.get("e_electronic"); n = row.get("refractive_index")
    if e_tot:
        cat = "Very high" if e_tot>20 else "High" if e_tot>10 else "Moderate" if e_tot>4 else "Low"
        h += sc("Total ε", f"{e_tot:.2f}", cat,
                col="e_total", raw=e_tot, tip=HELP["Total ε"])
    if e_elec:
        h += sc("Electronic ε∞", f"{e_elec:.2f}", "Optical frequencies",
                col="e_electronic", raw=e_elec, tip=HELP["Electronic ε∞"])
    if e_ion:  h += sc("Ionic εᵢₒₙ", f"{e_ion:.2f}", "Phonon-driven", tip=HELP["Ionic εᵢₒₙ"])
    if n:
        h += sc("Refr. Index n", f"{n:.4f}", "n = √ε_elec",
                col="refractive_index", raw=n, tip=HELP["Refr. Index n"])
        R = ((n-1)/(n+1))**2 * 100
        h += sc("Reflectivity", f"{R:.1f}%", "Normal incidence", tip=HELP["Reflectivity"])
    if e_elec and e_tot:
        ionic_frac = (e_tot-e_elec)/e_tot*100 if e_tot>0 else 0
        h += sc("Ionic fraction", f"{ionic_frac:.1f}%", "Drops at high freq if large")
    if e_tot and e_tot>15:
        h += f'<div style="background:#0d2818;border:1px solid #238636;border-radius:4px;padding:3px 8px;font-size:0.7rem;color:#3fb950;margin-top:4px;">ε={e_tot:.1f} — plasma shielding candidate 🛡</div>'
    return h


def build_stability(row, pc_data):
    if not row: return na()
    h = sh("Thermodynamic Stability")
    hull = row.get("energy_above_hull")
    if hull is not None:
        if hull<0.001:   lbl,note = "Stable ground state","Thermodynamically stable"
        elif hull<0.025: lbl,note = f"+{hull:.3f} eV/atom","Metastable — often synthesizable"
        elif hull<0.1:   lbl,note = f"+{hull:.3f} eV/atom","Unstable"
        else:            lbl,note = f"+{hull:.3f} eV/atom","Highly unstable"
        h += sc("Hull Energy", lbl, note,
                col="energy_above_hull", raw=hull, tip=HELP["Energy Above Hull"])
    fe = row.get("formation_energy_per_atom")
    if fe is not None:
        h += sc("Formation Energy", f"{fe:.4f} eV/atom",
                "Neg = exothermic (stable vs elements)",
                col="formation_energy_per_atom", raw=fe, tip=HELP["Formation Energy"])
    decomp = row.get("decomposes_to")
    if decomp:
        try:
            dl = json.loads(decomp) if isinstance(decomp,str) else decomp
            if dl:
                txt = " → ".join(f"{d.get('formula','?')} ({d.get('amount',0):.2f})"
                                 if isinstance(d,dict) else str(d) for d in dl)
                h += sc("Decomposes To", txt, "If unstable")
        except Exception: pass
    if pc_data:
        h += sh("Experimental Thermal (PubChem)")
        mp_v = pc.format_prop(pc_data,"MeltingPoint","°C")
        bp_v = pc.format_prop(pc_data,"BoilingPoint","°C")
        fp_v = pc.format_prop(pc_data,"FlashPoint","°C")
        mw_v = pc.format_prop(pc_data,"MolecularWeight","g/mol")
        if mp_v: h += sc("Melting Point", mp_v)
        if bp_v: h += sc("Boiling Point", bp_v)
        if fp_v: h += sc("Flash Point",   fp_v, "Vapor ignition temp")
        if mw_v: h += sc("Mol. Weight",   mw_v)
    h += sh("Physical")
    dens = row.get("density")
    if dens: h += sc("Density", f"{dens:.3f} g/cm³",
                     col="density", raw=dens, tip=HELP["Density"])
    if row.get("volume"):  h += sc("Cell Volume", f"{row['volume']:.2f} Å³")
    if row.get("nsites"):  h += sc("Sites", str(row["nsites"]), "Atoms per unit cell")
    return h


# ── Position / comparison chart ───────────────────────────────────────────────
POS_PROPS = {
    "Bandgap (eV)":             "bandgap",
    "Density (g/cm³)":          "density",
    "Formation E (eV/at)":      "formation_energy_per_atom",
    "Magnetization (μB)":       "total_magnetization",
    "Young's E (GPa)":          "young_modulus",
    "Bulk K (GPa)":             "k_voigt",
    "Dielectric ε":             "e_total",
    "Refr. Index n":            "refractive_index",
    "Thermal κ (W/m·K)":        "thermal_conductivity",
    "Debye Temp (K)":           "debye_temperature",
}
POS_KEYS = list(POS_PROPS.keys())

def _auto_axes(tags):
    ts = set(tags or [])
    if "magnet"        in ts: return "Magnetization (μB)",  "Formation E (eV/at)"
    if "semiconductor" in ts or "perovskite" in ts: return "Bandgap (eV)", "Density (g/cm³)"
    if "space_elevator" in ts or "uhtc" in ts: return "Young's E (GPa)", "Density (g/cm³)"
    if "superconductor" in ts: return "Formation E (eV/at)", "Bandgap (eV)"
    return "Bandgap (eV)", "Density (g/cm³)"

@st.cache_data(show_spinner=False)
def _pos_data(x_col, y_col, fm, cs, tag):
    return local_db.get_position_data(x_col, y_col, fm, cs, tag)

def render_position_chart(db_row, accent, chart_h=168):
    """Render compound-position scatter inside its column."""
    try:
        cur_tags = json.loads(db_row.get("tags") or "[]")
    except Exception:
        cur_tags = []
    cur_cs  = db_row.get("crystal_system") or ""
    cur_tag = cur_tags[0] if cur_tags else None

    def_x, def_y = _auto_axes(cur_tags)
    xi = POS_KEYS.index(def_x); yi = POS_KEYS.index(def_y)

    cc1, cc2, cc3 = st.columns([3, 3, 4], gap="small")
    with cc1:
        x_lbl = st.selectbox("X", POS_KEYS, index=xi, key="pos_x",
                             label_visibility="collapsed")
    with cc2:
        y_lbl = st.selectbox("Y", POS_KEYS, index=yi, key="pos_y",
                             label_visibility="collapsed")
    with cc3:
        opts = ["All"]
        if cur_cs:  opts.append(cur_cs)
        if cur_tag: opts.append(cur_tag.capitalize())
        group = st.radio("Filter", opts, index=0, key="pos_grp", horizontal=True,
                         label_visibility="collapsed")

    if group == "All":           fm, cs_a, tag_a = "All", None, None
    elif group == cur_cs:        fm, cs_a, tag_a = "crystal_system", cur_cs, None
    else:                        fm, cs_a, tag_a = "category", None, cur_tag

    xc = POS_PROPS[x_lbl]; yc = POS_PROPS[y_lbl]
    rows = _pos_data(xc, yc, fm, cs_a, tag_a)

    if not rows:
        st.markdown(f'<div class="na" style="padding:20px 0 0;">No data for these axes.</div>',
                    unsafe_allow_html=True)
        return

    cur_mp = db_row.get("mp_id")
    bg_pts = [r for r in rows if r["mp_id"] != cur_mp]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[p[xc] for p in bg_pts], y=[p[yc] for p in bg_pts],
        mode="markers",
        marker=dict(size=3, color="#30363d", opacity=0.65),
        hovertemplate="%{text}<extra></extra>",
        text=[p["formula"] for p in bg_pts],
        showlegend=False,
    ))
    cur_xv = db_row.get(xc); cur_yv = db_row.get(yc)
    if cur_xv is not None and cur_yv is not None:
        formula_disp = db_row.get("formula", cur_mp)
        fig.add_trace(go.Scatter(
            x=[cur_xv], y=[cur_yv], mode="markers",
            marker=dict(size=13, color=accent, symbol="star",
                        line=dict(color="#fff", width=1)),
            hovertemplate=(f"{formula_disp}<br>"
                           f"{x_lbl}: %{{x:.3g}}<br>{y_lbl}: %{{y:.3g}}<extra></extra>"),
            showlegend=False,
        ))
    fig.update_layout(
        xaxis_title=x_lbl, yaxis_title=y_lbl,
        template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        margin=dict(l=44, r=6, t=4, b=36), height=chart_h,
        xaxis=dict(gridcolor="#21262d", tickfont=dict(size=9)),
        yaxis=dict(gridcolor="#21262d", tickfont=dict(size=9)),
        font=dict(size=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.markdown(
        f'<div style="font-size:0.58rem;color:#8b949e;margin-top:-6px;">'
        f'★ = {db_row.get("formula","")} · {len(rows):,} compounds</div>',
        unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚛ MatSci Explorer")
    api_key = os.environ.get("MP_API_KEY", "")
    if not api_key:
        api_key = st.text_input("MP API Key", type="password",
                                placeholder="materialsproject.org",
                                label_visibility="collapsed")
    search_q = st.text_input("🔍", placeholder="Search formula / mp-id…",
                             label_visibility="collapsed")
    st.divider()

    if search_q:
        st.markdown('<div class="cat-hdr">Search results</div>', unsafe_allow_html=True)
        with local_db.get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            srows = conn.execute(
                "SELECT mp_id, formula FROM materials "
                "WHERE formula LIKE ? OR mp_id LIKE ? LIMIT 20",
                (f"%{search_q}%", f"%{search_q}%")
            ).fetchall()
        if srows:
            for row in srows:
                lbl = f"{'▶ ' if row['mp_id']==st.session_state.mp_id else ''}{row['formula']}"
                if st.button(lbl, key=f"sr_{row['mp_id']}"):
                    st.session_state.mp_id        = row["mp_id"]
                    st.session_state.compound_name = row["formula"]
                    st.session_state.curated_data  = None
                    st.session_state.ashby_mode    = False
                    st.rerun()
        else:
            st.caption("No matches.")
    else:
        for cat, compounds in COMPOUNDS.items():
            st.markdown(f'<div class="cat-hdr">{cat}</div>', unsafe_allow_html=True)
            for name, data in compounds.items():
                is_sel = data["mp_id"] == st.session_state.mp_id
                lbl = f"{'▶ ' if is_sel else ''}{data['formula']}"
                if st.button(lbl, key=f"chip_{data['mp_id']}", width="stretch"):
                    st.session_state.mp_id        = data["mp_id"]
                    st.session_state.compound_name = name
                    st.session_state.curated_data  = data
                    st.session_state.ashby_mode    = False
                    st.rerun()

    st.divider()
    ashby_lbl = "▶ Ashby Charts" if st.session_state.ashby_mode else "📊 Ashby Charts"
    if st.button(ashby_lbl, width="stretch"):
        st.session_state.ashby_mode = not st.session_state.ashby_mode
        st.rerun()
    st.divider()
    db_info = local_db.stats()
    st.caption(
        f"**{db_info['total']:,}** compounds  \n"
        f"Elastic: {db_info['with_elasticity']}  ·  ε: {db_info['with_dielectric']}"
    )


# ── Ashby Charts ──────────────────────────────────────────────────────────────
if st.session_state.ashby_mode:
    APROPS = {
        "Density (g/cm³)": "density", "Young's Modulus (GPa)": "young_modulus",
        "Bulk K (GPa)": "k_voigt", "Shear G (GPa)": "g_voigt",
        "Bandgap (eV)": "bandgap", "Magnetization (μB)": "total_magnetization",
        "Refractive Index": "refractive_index", "Dielectric ε": "e_total",
        "Formation Energy (eV/at)": "formation_energy_per_atom",
        "Hull Energy (eV/at)": "energy_above_hull",
        "Poisson Ratio": "poisson_ratio", "Anisotropy AU": "universal_anisotropy",
        "Thermal κ (W/m·K)": "thermal_conductivity", "Debye Temp (K)": "debye_temperature",
    }
    st.markdown("## 📊 Ashby Material Selection Charts")
    c1,c2,c3,c4,c5 = st.columns([2,2,2,1,1])
    with c1: x_lbl = st.selectbox("X", list(APROPS.keys()), index=0)
    with c2: y_lbl = st.selectbox("Y", list(APROPS.keys()), index=1)
    with c3: color_by = st.selectbox("Color", ["crystal_system","ordering","theoretical"])
    with c4: log_x = st.checkbox("Log X")
    with c5: log_y = st.checkbox("Log Y", value=True)
    @st.cache_data(show_spinner=False)
    def _ashby(x,y,c,lim=3000): return local_db.get_ashby_data(x,y,c,lim)
    rows = _ashby(APROPS[x_lbl], APROPS[y_lbl], color_by)
    if not rows:
        st.warning(f"No compounds have both **{x_lbl}** and **{y_lbl}**.")
    else:
        clrs = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24
        grps = defaultdict(list)
        for r in rows: grps[str(r.get(color_by) or "Unknown")].append(r)
        xc,yc = APROPS[x_lbl], APROPS[y_lbl]
        fig = go.Figure()
        for i,(gn,pts) in enumerate(sorted(grps.items())):
            fig.add_trace(go.Scatter(
                x=[p[xc] for p in pts], y=[p[yc] for p in pts], mode="markers",
                marker=dict(size=6,color=clrs[i%len(clrs)],opacity=0.75),
                name=gn, hovertemplate="%{customdata}<extra></extra>",
                customdata=[f"{p['formula']}<br>{p['mp_id']}<br>{x_lbl}: {p[xc]:.3g}<br>{y_lbl}: {p[yc]:.3g}" for p in pts],
            ))
        fig.update_layout(
            xaxis_title=x_lbl, yaxis_title=y_lbl,
            xaxis_type="log" if log_x else "linear",
            yaxis_type="log" if log_y else "linear",
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            height=560, margin=dict(l=60,r=20,t=20,b=60),
            legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
            xaxis=dict(gridcolor="#21262d"), yaxis=dict(gridcolor="#21262d"),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(f"{len(rows):,} compounds · ★ top-left in E vs ρ = best specific stiffness")
    st.stop()


# ── Load compound ─────────────────────────────────────────────────────────────
selected_mp_id = st.session_state.mp_id
curated_data   = st.session_state.curated_data
accent         = curated_data["accent"] if curated_data else "#58a6ff"

db_row = local_db.get_material_row(selected_mp_id)

try:
    with st.spinner(""):
        structure = load_structure(selected_mp_id, api_key)
except Exception as exc:
    structure = None
    st.warning(f"Structure load error: {exc}")

if db_row is None:
    db_row = local_db.get_material_row(selected_mp_id)

if db_row is None and structure is None:
    st.error("Could not load compound. Select a curated compound or check API key.")
    st.stop()

# PubChem (try cache first)
pc_data = None
if db_row and db_row.get("pubchem_json"):
    try: pc_data = json.loads(db_row["pubchem_json"])
    except Exception: pass
if pc_data is None and db_row:
    try:
        formula_clean = db_row.get("formula", "")
        display_name  = curated_data["formula"] if curated_data else formula_clean
        pc_data = get_pubchem(formula_clean, display_name)
        if pc_data: local_db.save_pubchem(selected_mp_id, pc_data)
    except Exception:
        pass


# ── ROW A — Header + KPI strip ────────────────────────────────────────────────
formula_display = (curated_data["formula"] if curated_data
                   else (db_row or {}).get("formula", selected_mp_id))

badges = ""
if db_row:
    if db_row.get("crystal_system"): badges += badge(db_row["crystal_system"])
    if db_row.get("space_group"):    badges += badge(db_row["space_group"])
    theoretical = db_row.get("theoretical")
    if theoretical == 0:   badges += badge("Experimentally observed", "green")
    elif theoretical == 1: badges += badge("Computational only", "orange")
    hull = db_row.get("energy_above_hull")
    if hull is not None:
        if hull < 0.001:   badges += badge("Stable", "green")
        elif hull < 0.025: badges += badge(f"Metastable +{hull:.3f}", "orange")
        else:              badges += badge(f"Unstable +{hull:.3f}", "red")
badges += badge(selected_mp_id, "blue")

def _f(v, fmt=".2f"): return format(v, fmt) if v is not None else "—"
kpis = ""
if db_row:
    bg   = db_row.get("bandgap")
    bg_s = ("Metal" if bg==0 else f"{bg:.2f} eV") if bg is not None else "—"
    mag  = db_row.get("total_magnetization")
    kpis += kpi("Density",      _f(db_row.get("density"),".3f"), "g/cm³")
    kpis += kpi("Band Gap",     bg_s)
    kpis += kpi("Young's E",    _f(db_row.get("young_modulus"),".0f"), "GPa")
    kpis += kpi("Bulk K",       _f(db_row.get("k_voigt"),".0f"), "GPa")
    kpis += kpi("Dielectric ε", _f(db_row.get("e_total"),".1f"))
    kpis += kpi("Refr. Index",  _f(db_row.get("refractive_index"),".3f"))
    kpis += kpi("Magnetization",_f(mag,".2f") if mag is not None else "—", "μB")
    tc = db_row.get("thermal_conductivity")
    if tc is not None: kpis += kpi("Thermal κ", f"{tc:.2f}", "W/m·K")

st.markdown(
    f'<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:2px;">'
    f'<span style="font-size:1.5rem;font-weight:700;color:#e6edf3;">{formula_display}</span>'
    f'<span>{badges}</span></div>'
    f'<div class="krow">{kpis}</div>',
    unsafe_allow_html=True)


# ── ROW B — popovers + panels ─────────────────────────────────────────────────
PANEL_H = 345

# Popover guide buttons (mirror column ratios [36,21,22,21])
ph_v, ph_e, ph_m, ph_d = st.columns([36, 21, 22, 21], gap="small")
with ph_e:
    with st.popover("ℹ Electronic", width="stretch"):
        st.markdown("""
**Band Gap** — Energy gap between valence and conduction bands. 0 = metal, <1 eV = narrow semiconductor, >5 eV = insulator. Hover over any **?** label below for details.

**CBM / VBM** — Conduction Band Minimum / Valence Band Maximum. The difference = band gap. Position sets electron affinity.

**Magnetic Ordering** — FM = ferromagnet (spins aligned). AFM = antiferromagnet (alternating ±). FiM = ferrimagnet. NM = non-magnetic.

**Magnetization** — Total magnetic moment (μB/f.u.). Higher = stronger magnetic field per unit cell. Permanent magnets need high magnetization *and* high coercivity.

**Magnetic Sites** — Atoms with unpaired electrons. Transition metals (Fe, Co, Ni) and rare earths (Nd, Sm) are common magnetic sites.
        """)
with ph_m:
    with st.popover("ℹ Mechanical", width="stretch"):
        st.markdown("""
**Bulk K** — Resistance to uniform compression (GPa). Diamond ≈ 440, steel ≈ 160.

**Shear G** — Resistance to shape change (GPa). High G = scratch-resistant.

**Young's E** — Axial stiffness = 9BG/(3B+G). Diamond ≈ 1050, carbon fiber ≈ 300.

**Poisson ν** — Lateral contraction ratio. 0.25–0.35 = typical solids. Near 0.5 = rubber-like.

**Anisotropy AU** — 0 = same stiffness all directions. >1 = significant variation.

**Specific E/ρ** — Stiffness per unit weight. Space elevator cables need > 100 GPa·cm³/g. Steel ≈ 26, diamond ≈ 350.

**Pugh B/G** — >1.75 = ductile, <1.75 = brittle fracture expected.

**Thermal κ** — Heat flow rate (W/m·K). Estimated from Debye temperature via Clarke/Cahill model.

**Debye Temp** — Θ_D: temperature above which all phonons are excited. High = stiff bonds, high melting point.
        """)
with ph_d:
    with st.popover("ℹ Dielectric", width="stretch"):
        st.markdown("""
**Total ε** — Static dielectric constant. How much the material weakens an electric field at low frequency. High ε = good capacitor + good plasma reflector.

**Electronic ε∞** — High-frequency response from electron clouds only. Active at optical frequencies. n = √ε∞.

**Ionic εᵢₒₙ** — Response from polar bond vibrations (phonons). Only active below infrared frequencies; drops off for fast EM fields.

**Refractive Index n** — Measures light slowing/bending. Glass ≈ 1.5, diamond = 2.42.

**Reflectivity** — Normal-incidence reflection: R = ((n−1)/(n+1))². High n → shiny surface.

**Ionic fraction** — What percent of ε comes from ions vs electrons. High ionic fraction = ε drops dramatically at high frequency.
        """)

# Main panels
v_col, e_col, m_col, d_col = st.columns([36, 21, 22, 21], gap="small")

with v_col:
    if structure:
        st.components.v1.html(render_crystal(structure, accent, w=460, h=330), height=348, scrolling=False)
        lat = structure.lattice
        st.markdown(
            f'<div style="font-size:0.65rem;color:#8b949e;margin-top:1px;">'
            f'a={lat.a:.3f} b={lat.b:.3f} c={lat.c:.3f} Å &nbsp;|&nbsp; '
            f'α={lat.alpha:.1f}° β={lat.beta:.1f}° γ={lat.gamma:.1f}° &nbsp;|&nbsp; '
            f'{structure.num_sites} sites</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="background:#161b22;border:1px dashed #30363d;border-radius:6px;'
            f'height:{PANEL_H}px;display:flex;align-items:center;justify-content:center;'
            f'color:#8b949e;font-size:0.8rem;">Structure unavailable</div>',
            unsafe_allow_html=True)
    if curated_data:
        st.markdown(
            f'<details><summary>💡 Why this structure → this property</summary>'
            f'<div class="why" style="border-color:{accent};">'
            f'{curated_data["why_it_works"]}</div></details>',
            unsafe_allow_html=True)

with e_col:
    st.markdown(panel(build_electronic(db_row), PANEL_H), unsafe_allow_html=True)

with m_col:
    st.markdown(panel(build_mechanical(db_row), PANEL_H), unsafe_allow_html=True)

with d_col:
    st.markdown(panel(build_dielectric(db_row), PANEL_H), unsafe_allow_html=True)


# ── ROW C — XRD · Stability · Position chart ─────────────────────────────────
BOTTOM_H = 220
xrd_col, stab_col, pos_col = st.columns([40, 28, 32], gap="small")

with xrd_col:
    st.markdown(
        '<div style="font-size:0.62rem;color:#8b949e;text-transform:uppercase;'
        'letter-spacing:.08em;font-weight:700;margin-bottom:3px;">'
        '📊 XRD Pattern (Cu Kα λ=1.5406 Å)</div>', unsafe_allow_html=True)
    if structure:
        try:
            xrd = get_xrd(json.dumps(structure.as_dict()))
            fig = go.Figure()
            for x,y,hkl in zip(xrd["two_theta"], xrd["intensity"], xrd["hkls"]):
                fig.add_trace(go.Scatter(
                    x=[x,x,x], y=[0,y,0], mode="lines",
                    line=dict(color=accent, width=1.5),
                    hovertemplate=f"2θ={x:.2f}° I={y:.1f} {hkl}<extra></extra>",
                    showlegend=False,
                ))
            fig.update_layout(
                xaxis_title="2θ (degrees)", yaxis_title="Intensity",
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                margin=dict(l=44,r=8,t=4,b=36), height=BOTTOM_H,
                xaxis=dict(range=[0,90],gridcolor="#21262d",tickfont=dict(size=10)),
                yaxis=dict(range=[0,110],gridcolor="#21262d",tickfont=dict(size=10)),
            )
            st.plotly_chart(fig, width="stretch")
        except Exception as exc:
            st.markdown(f'<div class="na">XRD failed: {exc}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="panel" style="height:{BOTTOM_H}px;">{na("Structure not loaded")}</div>',
                    unsafe_allow_html=True)

with stab_col:
    st.markdown(panel(build_stability(db_row, pc_data), BOTTOM_H), unsafe_allow_html=True)

with pos_col:
    st.markdown(
        '<div style="font-size:0.62rem;color:#8b949e;text-transform:uppercase;'
        'letter-spacing:.08em;font-weight:700;margin-bottom:2px;">'
        '⭐ Where does this compound sit?</div>', unsafe_allow_html=True)
    if db_row:
        try:
            render_position_chart(db_row, accent, chart_h=BOTTOM_H - 52)
        except Exception as exc:
            st.markdown(f'<div class="na">Chart error: {exc}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="na">No data available.</div>', unsafe_allow_html=True)
