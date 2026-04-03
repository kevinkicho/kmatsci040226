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
import wikipedia as wiki_api

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
local_db.init_db()

# ── Force sidebar open on every page load ─────────────────────────────────────
st.components.v1.html("""<script>
(function(){
    var p = window.parent;
    // 1. Clear any stored "sidebar collapsed" state from localStorage
    try {
        var ls = p.localStorage;
        for (var i = ls.length - 1; i >= 0; i--) {
            var k = ls.key(i);
            if (k && (k.includes('sidebar') || k.includes('Sidebar') || k.includes('collapsed')))
                ls.removeItem(k);
        }
    } catch(e){}
    // 2. Click the expand button if it exists (retrying until Streamlit renders it)
    var tries = 0;
    var iv = setInterval(function(){
        var btn = p.document.querySelector('[data-testid="collapsedControl"]');
        if (btn) { btn.click(); clearInterval(iv); }
        if (++tries > 30) clearInterval(iv);
    }, 150);
})();
</script>""", height=0)

st.set_page_config(page_title="MatSci Explorer", page_icon="⚛",
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
header[data-testid="stHeader"] { display:none; }
#MainMenu, footer { visibility:hidden; }
.block-container { padding:0.4rem 1rem 0 1rem !important; max-width:100% !important; }
/* Allow vertical scroll when content overflows — no more hidden overflow */
section[data-testid="stMain"] { overflow-y:auto !important; overflow-x:hidden !important; }

/* Hide the << collapse button — sidebar is always-on for this dashboard.
   The JS below handles restoring it if it ever gets stuck collapsed. */
[data-testid="stSidebarCollapseButton"] { display:none !important; }

.stApp { background:#0d1117; color:#e6edf3; }
[data-testid="stSidebar"] { background:#111318; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:0.1rem; }

/* ── Kill sidebar top padding ─────────────────────────────── */
[data-testid="stSidebarContent"] { padding-top:0 !important; padding-bottom:1rem !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top:0 !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:first-child { margin-top:0 !important; padding-top:0 !important; }

/* Stat card */
.sc { background:#161b22; border:1px solid #21262d; border-radius:5px;
  padding:5px 10px; margin-bottom:4px; }
.sc-l { font-size:0.62rem; color:#8b949e; text-transform:uppercase;
  letter-spacing:.06em; display:block; }
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

/* Sidebar category headers */
.cat-hdr { font-size:0.58rem; color:#8b949e; text-transform:uppercase;
  letter-spacing:.12em; font-weight:700; margin:8px 0 3px;
  padding:2px 0 2px 2px; border-left:2px solid #21262d; }

.na { color:#8b949e; font-style:italic; font-size:0.8rem; padding:6px 0; }

/* Sidebar compound chip buttons */
[data-testid="stSidebar"] .stButton > button {
  padding:3px 6px; font-size:0.68rem; border-radius:6px; min-height:0;
  height:auto; line-height:1.3; border:1px solid #21262d;
  background:#161b22; color:#c9d1d9; width:100%;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  transition: border-color 0.15s, color 0.15s, background 0.15s; }
[data-testid="stSidebar"] .stButton > button:hover {
  border-color:#58a6ff; color:#e6edf3; background:#0d1f3c; }

/* Primary (selected) chip */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  border-color:#58a6ff !important; color:#58a6ff !important;
  background:#0d1f3c !important; font-weight:600; }

/* ── Sidebar category grid: compact aligned selectboxes ──── */
[data-testid="stSidebar"] .stSelectbox > label {
  font-size:0.50rem !important; color:#484f58 !important;
  text-transform:uppercase; letter-spacing:.1em;
  margin-bottom:1px !important; line-height:1.2 !important; }
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {
  min-height:24px !important; font-size:0.70rem !important;
  padding:2px 6px !important;
  background:#0d1117 !important; border-color:#21262d !important; }
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child:hover {
  border-color:#30363d !important; }
[data-testid="stSidebar"] .stColumns { gap:6px !important; }
[data-testid="stSidebar"] .stColumn  { padding:0 2px !important; }

/* ── Hover tooltip on stat-card labels ───────────────────── */
.sc-l { position:relative; cursor:help; }
.tip-box {
  visibility:hidden; opacity:0;
  position:absolute; z-index:9999; pointer-events:none;
  bottom:calc(100% + 6px); left:-6px;
  width:260px;
  background:#1c2128; border:1px solid #30363d; border-radius:7px;
  padding:9px 13px;
  font-size:0.70rem; color:#c9d1d9; line-height:1.55;
  white-space:normal; text-transform:none;
  letter-spacing:normal; font-weight:400;
  box-shadow:0 8px 24px rgba(0,0,0,0.65);
  transition: opacity 0.15s ease, visibility 0.15s ease; }
.sc-l:hover .tip-box { visibility:visible; opacity:1; }
.tip-title { font-size:0.68rem; font-weight:700; color:#e6edf3; margin-bottom:5px; }
.tip-scale { display:flex; gap:3px; flex-wrap:wrap; margin:4px 0 6px; }
.tip-scale span { padding:1px 6px; border-radius:3px; font-size:0.62rem; font-weight:600; }

/* ── "Why" hover popup ───────────────────────────────────── */
.why-hover-wrap { position:relative; margin-top:6px; }
.why-trigger {
  font-size:0.61rem; color:#484f58; cursor:help;
  display:block; padding:1px 0; letter-spacing:0.02em;
  user-select:none; transition:color 0.15s; }
.why-trigger:hover { color:#8b949e; }
.why-popup {
  visibility:hidden; opacity:0;
  position:absolute; z-index:9999; pointer-events:none;
  top:-6px; left:calc(100% + 14px);
  width:360px;
  background:#161b22; border:1px solid #21262d;
  border-radius:0 7px 7px 0; padding:13px 16px;
  font-size:0.81rem; line-height:1.65; color:#c9d1d9;
  box-shadow:0 8px 28px rgba(0,0,0,0.65);
  transition: opacity 0.2s ease, visibility 0.2s ease; }
.why-hover-wrap:hover .why-popup { visibility:visible; opacity:1; }

.why { background:#161b22; border-left:3px solid; border-radius:0 5px 5px 0;
  padding:8px 12px; font-size:0.8rem; line-height:1.65; color:#c9d1d9; margin-top:3px; }

/* ── Section header (replaces tabs) ─────────────────────── */
.section-hdr { font-size:0.62rem; color:#58a6ff; text-transform:uppercase;
  letter-spacing:.1em; font-weight:700; margin:10px 0 5px; padding-bottom:4px;
  border-bottom:1px solid #21262d; }
.section-hdr:first-child { margin-top:0; }

/* ── 2-column stat card grid ─────────────────────────────── */
.sc-grid { display:grid; grid-template-columns:1fr 1fr; gap:4px; margin-top:4px; }
.sc-grid .sh { grid-column:1/-1; }


/* ── Note button ─────────────────────────────────────────── */
.note-btn-wrap .stButton > button {
  background:transparent !important; border:none !important;
  padding:1px 0 !important; font-size:0.60rem !important;
  color:#484f58 !important; min-height:0 !important; height:auto !important;
  letter-spacing:0.02em !important; transition:color 0.15s !important; }
.note-btn-wrap .stButton > button:hover { color:#8b949e !important; border:none !important; }

/* ── Lat info line ───────────────────────────────────────── */
.lat-info { font-size:0.62rem; color:#8b949e; margin-top:2px; line-height:1.4; }

</style>
""", unsafe_allow_html=True)


# ── Rich HTML tooltip content (hover on stat-card labels) ────────────────────
def _s(color, bg, text):  # colored scale chip
    return f'<span style="background:{bg};color:{color};padding:1px 6px;border-radius:3px;">{text}</span>'

TIP_HTML: dict[str, str] = {
"Band Gap": (
    '<div class="tip-title">Band Gap (eV)</div>'
    '<div class="tip-scale">'
    + _s("#fff","#c0392b","Metal 0") + _s("#000","#e67e22","Narrow &lt;1")
    + _s("#000","#27ae60","Semi 1–3") + _s("#fff","#2980b9","Wide 3–5")
    + _s("#fff","#5d6d7e","Insul. &gt;5")
    + '</div>'
    'Energy gap between the filled valence band and empty conduction band. '
    'Determines whether a material conducts, semi-conducts, or insulates. '
    'DFT values underestimate by ~20–40% vs experiment.'
),
"CBM": (
    '<div class="tip-title">Conduction Band Minimum</div>'
    'Lowest energy an electron in the conduction band can have. '
    'Its position relative to vacuum sets the material\'s <b>electron affinity</b> — '
    'critical for designing heterojunction solar cells and LEDs.'
),
"VBM": (
    '<div class="tip-title">Valence Band Maximum</div>'
    'Highest energy of occupied electrons at 0 K. '
    'Band Gap = CBM − VBM. Position vs vacuum sets the <b>ionization potential</b>.'
),
"Ordering": (
    '<div class="tip-title">Magnetic Ordering</div>'
    '<div class="tip-scale">'
    + _s("#fff","#c0392b","FM") + _s("#fff","#2980b9","AFM")
    + _s("#fff","#8e44ad","FiM") + _s("#aaa","#21262d","NM")
    + '</div>'
    '<b>FM</b> ferromagnetic — spins aligned → permanent magnet. '
    '<b>AFM</b> antiferromagnetic — alternating ± → no net moment. '
    '<b>FiM</b> ferrimagnetic — unequal opposing → weak net moment. '
    '<b>NM</b> non-magnetic.'
),
"Magnetization": (
    '<div class="tip-title">Total Magnetization (μB / f.u.)</div>'
    'Net magnetic moment per formula unit in Bohr magnetons. '
    'Pure Fe ≈ 2.2 μB/atom · Nd₂Fe₁₄B ≈ 37.5 μB/f.u. '
    'High magnetization + high coercivity = strong permanent magnet candidate.'
),
"Magnetic Sites": (
    '<div class="tip-title">Magnetic Sites</div>'
    'Atoms per unit cell carrying unpaired d/f electrons. '
    'Transition metals (Fe, Co, Ni) and rare earths (Nd, Sm, Gd) are typical sites.'
),
"Bulk K": (
    '<div class="tip-title">Bulk Modulus K (GPa)</div>'
    '<div class="tip-scale">'
    + _s("#aaa","#21262d","Rubber 0.002") + _s("#000","#f0b27a","Al 76")
    + _s("#fff","#2980b9","Steel 160") + _s("#fff","#c0392b","Diamond 440")
    + '</div>'
    'Resistance to uniform compression from all sides. '
    'Higher K = harder to squeeze. Voigt average from full elastic tensor.'
),
"Shear G": (
    '<div class="tip-title">Shear Modulus G (GPa)</div>'
    '<div class="tip-scale">'
    + _s("#aaa","#21262d","Ice 4") + _s("#000","#f0b27a","Al 26")
    + _s("#fff","#2980b9","Steel 80") + _s("#fff","#c0392b","Diamond 535")
    + '</div>'
    'Resistance to shape change at constant volume. High G = scratch-resistant, hard.'
),
"Young\'s E": (
    '<div class="tip-title">Young\'s Modulus E (GPa)</div>'
    '<div class="tip-scale">'
    + _s("#000","#f0b27a","Al 70") + _s("#fff","#2980b9","Steel 200")
    + _s("#fff","#8e44ad","C-fiber 300") + _s("#fff","#c0392b","Diamond 1050")
    + '</div>'
    'Axial stiffness: stress ÷ strain along one axis. '
    'E = 9BG/(3B+G). The go-to number for structural design.'
),
"Poisson ν": (
    '<div class="tip-title">Poisson Ratio ν</div>'
    '<div style="position:relative;background:#21262d;border-radius:4px;height:7px;margin:5px 0 8px;">'
    '<div style="position:absolute;left:0;width:100%;height:100%;'
    'background:linear-gradient(to right,#2980b9,#27ae60,#c0392b);border-radius:4px;"></div>'
    '<div style="position:absolute;left:0%;top:-12px;font-size:0.58rem;color:#58a6ff;">0<br>cork</div>'
    '<div style="position:absolute;left:50%;top:-12px;font-size:0.58rem;color:#3fb950;transform:translateX(-50%);">0.3<br>metals</div>'
    '<div style="position:absolute;right:0;top:-12px;font-size:0.58rem;color:#f85149;text-align:right;">0.5<br>rubber</div>'
    '</div>'
    'Lateral expansion when compressed axially. Near 0.5 = nearly incompressible (rubber-like).'
),
"Anisotropy": (
    '<div class="tip-title">Universal Anisotropy AU</div>'
    '<div class="tip-scale">'
    + _s("#000","#27ae60","Isotropic AU=0") + _s("#000","#f0b27a","Mild AU&lt;1")
    + _s("#fff","#c0392b","High AU&gt;1")
    + '</div>'
    '0 = stiffness identical in all crystal directions. '
    'High AU predicts preferred cleavage planes and directional mechanical failure.'
),
"Specific E/ρ": (
    '<div class="tip-title">Specific Modulus E/ρ (GPa·cm³/g)</div>'
    '<div class="tip-scale">'
    + _s("#000","#f0b27a","Steel 26") + _s("#000","#f0b27a","Al 26")
    + _s("#fff","#2980b9","C-fiber 150") + _s("#fff","#c0392b","Diamond 350")
    + '</div>'
    'Stiffness per unit weight. The key metric for lightweight structural materials. '
    'Space elevator cable concept requires E/ρ &gt; 100.'
),
"Pugh B/G": (
    '<div class="tip-title">Pugh Ratio B/G</div>'
    '<div style="position:relative;background:#21262d;border-radius:4px;height:7px;margin:5px 0 8px;">'
    '<div style="position:absolute;left:0;width:54%;height:100%;background:#c0392b;border-radius:4px 0 0 4px;"></div>'
    '<div style="position:absolute;left:54%;width:46%;height:100%;background:#27ae60;border-radius:0 4px 4px 0;"></div>'
    '<div style="position:absolute;left:54%;top:-14px;font-size:0.60rem;color:#e6edf3;transform:translateX(-50%);">1.75</div>'
    '</div>'
    '<span style="color:#f85149;">Brittle</span> (ceramics, B/G &lt;1.75) · '
    '<span style="color:#3fb950;">Ductile</span> (metals, B/G &gt;1.75). '
    'Voigt averages from elastic tensor.'
),
"Therm. Cond.": (
    '<div class="tip-title">Thermal Conductivity κ (W/m·K)</div>'
    '<div class="tip-scale">'
    + _s("#aaa","#21262d","ZrO₂ 2") + _s("#000","#f0b27a","Steel 50")
    + _s("#fff","#2980b9","Cu 400") + _s("#fff","#c0392b","Diamond 2000")
    + '</div>'
    'Rate of heat flow. High κ = good heat spreader (electronics cooling). '
    'Low κ = good thermal barrier (turbine coatings). Clarke/Cahill model estimate.'
),
"Debye Temp": (
    '<div class="tip-title">Debye Temperature Θ_D (K)</div>'
    '<div class="tip-scale">'
    + _s("#aaa","#21262d","Pb 105 K") + _s("#000","#f0b27a","Al 428 K")
    + _s("#fff","#2980b9","Si 645 K") + _s("#fff","#c0392b","Diamond 2230 K")
    + '</div>'
    'Energy scale of lattice vibrations. High Θ_D = stiff bonds, high sound speed, '
    'high melting point. Scales with κ and hardness.'
),
"Total ε": (
    '<div class="tip-title">Dielectric Constant ε (static)</div>'
    '<div class="tip-scale">'
    + _s("#aaa","#21262d","Vacuum 1") + _s("#fff","#2980b9","Si 11.7")
    + _s("#fff","#8e44ad","GaAs 12.9") + _s("#fff","#c0392b","BaTiO₃ ~1700")
    + '</div>'
    'How much a material weakens an electric field at low frequency. '
    'High ε = good capacitor dielectric or plasma wave reflector.'
),
"Electronic ε∞": (
    '<div class="tip-title">Electronic Dielectric ε∞ (optical)</div>'
    'Electron-cloud distortion response at optical frequencies. '
    'Related to refractive index: <b>n = √ε∞</b>. '
    'Unaffected by slower ionic motion — stays nonzero at all frequencies.'
),
"Ionic εᵢₒₙ": (
    '<div class="tip-title">Ionic Dielectric ε_ion</div>'
    'Polarization from polar bond vibrations (phonons). '
    'Active only below IR frequencies. Large in ferroelectrics (BaTiO₃, PZT). '
    'Drops to zero above phonon frequencies — ε_total → ε∞ at optical frequencies.'
),
"Refr. Index n": (
    '<div class="tip-title">Refractive Index n</div>'
    '<div class="tip-scale">'
    + _s("#aaa","#21262d","Air 1.00") + _s("#000","#f0b27a","Glass 1.5")
    + _s("#fff","#c0392b","Diamond 2.42") + _s("#fff","#8e44ad","GaAs 3.6")
    + '</div>'
    'n = √ε∞. How much light slows and bends at the interface. '
    'High n = more reflective, stronger light bending (useful for waveguides, LEDs).'
),
"Reflectivity": (
    '<div class="tip-title">Normal-Incidence Reflectivity R</div>'
    'R = ((n−1)/(n+1))². Fraction of light reflected at a flat surface. '
    '<b>Glass ≈ 4%</b> · <b>Diamond ≈ 17%</b> · <b>GaAs ≈ 32%</b>. '
    'High R = mirror-like, metallic appearance.'
),
"Hull Energy": (
    '<div class="tip-title">Energy Above Convex Hull (eV/atom)</div>'
    '<div class="tip-scale">'
    + _s("#000","#27ae60","Stable 0") + _s("#000","#f0b27a","Metastable &lt;0.025")
    + _s("#fff","#c0392b","Unstable &gt;0.1")
    + '</div>'
    'Distance from thermodynamic ground state. '
    '0 = fully stable phase. &lt;0.025 eV/at = typically synthesizable. '
    '&gt;0.1 eV/at = prone to decomposition under equilibrium conditions.'
),
"Formation Energy": (
    '<div class="tip-title">Formation Energy (eV/atom)</div>'
    '<div class="tip-scale">'
    + _s("#000","#27ae60","Negative → stable") + _s("#fff","#c0392b","Positive → unstable")
    + '</div>'
    'Energy to form compound from its elements. '
    'More negative = atoms strongly prefer to be bonded together. '
    'SiO₂ ≈ −3.0 eV/at (very stable) · NaCl ≈ −1.8 eV/at.'
),
"Density": (
    '<div class="tip-title">Density (g/cm³)</div>'
    '<div class="tip-scale">'
    + _s("#aaa","#21262d","Li 0.53") + _s("#000","#f0b27a","Al 2.7")
    + _s("#fff","#2980b9","Fe 7.87") + _s("#fff","#c0392b","Os 22.6")
    + '</div>'
    'From unit cell mass ÷ unit cell volume. '
    'Affects specific strength, shielding effectiveness, and thermal mass.'
),
}

# ── Fallback plain-text tips (used if not in TIP_HTML) ───────────────────────
HELP: dict[str, str] = {
    "CBM":           "Conduction Band Minimum.",
    "VBM":           "Valence Band Maximum.",
    "Magnetic Sites":"Atoms per unit cell with unpaired electrons.",
    "Ionic fraction": "Fraction of total ε from ionic phonon contribution.",
    "Cell Volume":   "Unit cell volume in Å³.",
    "Sites":         "Atoms per unit cell.",
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
if "compare_mode" not in st.session_state:
    st.session_state.compare_mode = False
if "compare_mp_id" not in st.session_state:
    st.session_state.compare_mp_id = None
if "compare_name" not in st.session_state:
    st.session_state.compare_name = None
if "compare_curated" not in st.session_state:
    st.session_state.compare_curated = None

# ── URL query-param sync (enables browser back/forward) ───────────────────────
_url_mp = st.query_params.get("mp")
if _url_mp and _url_mp != st.session_state.mp_id:
    _url_row = local_db.get_material_row(_url_mp)
    if _url_row:
        st.session_state.mp_id        = _url_mp
        st.session_state.compound_name = _url_row.get("formula", _url_mp)
        st.session_state.curated_data  = None
        for _cat, _cmpds in COMPOUNDS.items():
            for _n, _d in _cmpds.items():
                if _d["mp_id"] == _url_mp:
                    st.session_state.curated_data = _d
                    break
        st.rerun()
elif st.session_state.mp_id and not _url_mp:
    st.query_params["mp"] = st.session_state.mp_id


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
                tip       → ignored (tooltips come from TIP_HTML keyed by label).
    """
    tip_content = TIP_HTML.get(label) or (HELP.get(label) or "")
    tip_span    = f'<span class="tip-box">{tip_content}</span>' if tip_content else ""
    lbl_html    = f'<span class="sc-l">{label}{tip_span}</span>'
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
                col="bandgap", raw=bg if bg>0 else None)
        pct   = min(bg/10*100, 100)
        color = "#f85149" if bg==0 else "#3fb950" if bg<3 else "#d29922"
        h += (f'<div style="background:#21262d;border-radius:3px;height:5px;margin:-1px 0 5px;">'
              f'<div style="background:{color};width:{pct}%;height:100%;border-radius:3px;"></div></div>')
    else:
        h += na("No bandgap")
    cbm = row.get("cbm"); vbm = row.get("vbm")
    if cbm is not None: h += sc("CBM", f"{cbm:.3f} eV", "Conduction band min")
    if vbm is not None: h += sc("VBM", f"{vbm:.3f} eV", "Valence band max")
    h += sh("Magnetic")
    ordering = row.get("ordering"); mag = row.get("total_magnetization")
    ORDR = {"FM":("Ferromagnetic","All spins aligned"),"AFM":("Antiferromagnetic","Alternating ±"),
            "FiM":("Ferrimagnetic","Unequal opposing"),"NM":("Non-magnetic","No unpaired e⁻")}
    if ordering and ordering in ORDR:
        lbl, note = ORDR[ordering]; h += sc("Ordering", lbl, note)
    elif ordering:
        h += sc("Ordering", ordering)
    if mag is not None:
        h += sc("Magnetization", f"{mag:.3f} μB/f.u.",
                col="total_magnetization", raw=mag if mag>0 else None)
    nm = row.get("num_magnetic_sites")
    if nm: h += sc("Magnetic Sites", str(nm), "Atoms w/ unpaired e⁻")
    return h


def build_mechanical(row):
    if not row: return na()
    h = sh("Elastic Moduli")
    if row.get("k_voigt") is None:
        return h + na("No mechanical data available" if row.get("elastic_fetched")==1 else "Mechanical data not yet loaded — run python fetch.py once")
    B  = row.get("k_voigt"); G = row.get("g_voigt"); E = row.get("young_modulus")
    nu = row.get("poisson_ratio"); au = row.get("universal_anisotropy")
    ρ  = row.get("density"); tc = row.get("thermal_conductivity"); θD = row.get("debye_temperature")
    if B:  h += sc("Bulk K",    f"{B:.1f} GPa", "Compression resistance", col="k_voigt", raw=B)
    if G:  h += sc("Shear G",   f"{G:.1f} GPa", "Shape change resistance", col="g_voigt", raw=G)
    if E:  h += sc("Young's E", f"{E:.1f} GPa", "Axial stiffness", col="young_modulus", raw=E)
    if nu is not None:
        h += sc("Poisson ν", f"{nu:.4f}", "Lateral contraction", col="poisson_ratio", raw=nu)
    if au is not None:
        alab = "Isotropic" if au<0.1 else ("Mild" if au<1 else "High aniso.")
        h += sc("Anisotropy", f"{au:.3f}", alab)
    if E and ρ:
        sm = E/ρ; flag = " ★" if sm>100 else ""
        h += sc("Specific E/ρ", f"{sm:.1f}{flag}", "GPa·cm³/g")
    if B and G:
        pugh = B/G
        h += sc("Pugh B/G", f"{pugh:.2f}", "Ductile" if pugh>1.75 else "Brittle")
    h += sh("Thermal")
    if tc is not None:
        h += sc("Therm. Cond.", f"{tc:.2f} W/m·K", "Clarke/Cahill estimate",
                col="thermal_conductivity", raw=tc)
    if θD is not None:
        h += sc("Debye Temp", f"{θD:.0f} K", "Phonon energy scale",
                col="debye_temperature", raw=θD)
    return h


def build_dielectric(row):
    if not row: return na()
    h = sh("Dielectric & Optical")
    if row.get("e_total") is None:
        return h + na("No dielectric data available" if row.get("dielectric_fetched")==1 else "Dielectric data not yet loaded — run python fetch.py once")
    e_tot = row.get("e_total"); e_ion = row.get("e_ionic")
    e_elec = row.get("e_electronic"); n = row.get("refractive_index")
    if e_tot:
        cat = "Very high" if e_tot>20 else "High" if e_tot>10 else "Moderate" if e_tot>4 else "Low"
        h += sc("Total ε", f"{e_tot:.2f}", cat, col="e_total", raw=e_tot)
    if e_elec:
        h += sc("Electronic ε∞", f"{e_elec:.2f}", "Optical frequencies",
                col="e_electronic", raw=e_elec)
    if e_ion:  h += sc("Ionic εᵢₒₙ", f"{e_ion:.2f}", "Phonon-driven")
    if n:
        h += sc("Refr. Index n", f"{n:.4f}", "n = √ε_elec",
                col="refractive_index", raw=n)
        R = ((n-1)/(n+1))**2 * 100
        h += sc("Reflectivity", f"{R:.1f}%", "Normal incidence")
    if e_elec and e_tot:
        ionic_frac = (e_tot-e_elec)/e_tot*100 if e_tot>0 else 0
        h += sc("Ionic fraction", f"{ionic_frac:.1f}%", "Drops at high freq if large")
    if e_tot and e_tot>15:
        h += f'<div style="background:#0d2818;border:1px solid #238636;border-radius:4px;padding:3px 8px;font-size:0.7rem;color:#3fb950;margin-top:4px;">ε={e_tot:.1f} — plasma shielding candidate</div>'
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
        h += sc("Hull Energy", lbl, note, col="energy_above_hull", raw=hull)
    fe = row.get("formation_energy_per_atom")
    if fe is not None:
        h += sc("Formation Energy", f"{fe:.4f} eV/atom",
                "Neg = exothermic (stable vs elements)",
                col="formation_energy_per_atom", raw=fe)
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
    if dens: h += sc("Density", f"{dens:.3f} g/cm³", col="density", raw=dens)
    if row.get("volume"):  h += sc("Cell Volume", f"{row['volume']:.2f} Å³")
    if row.get("nsites"):  h += sc("Sites", str(row["nsites"]), "Atoms per unit cell")
    return h


# ── Modal dialogs ────────────────────────────────────────────────────────────
@st.dialog("Electronic & Magnetic Properties")
def dlg_electronic():
    st.markdown("""
**Band Gap** — Energy gap between valence and conduction bands (eV).
- `0 eV` = metal (electrons flow freely)
- `0.5–3 eV` = semiconductor (transistors, solar cells)
- `>5 eV` = insulator (ceramics, glass)
- DFT values are typically 20–40% lower than experiment.

**CBM / VBM** — Conduction Band Minimum / Valence Band Maximum. The difference between them = band gap. Their absolute positions set how electrons transfer at interfaces (important for solar cells and LEDs).

**Magnetic Ordering** — How electron spins are arranged:
- **FM** (Ferromagnetic): all spins aligned → acts as a permanent magnet (Fe, Nd₂Fe₁₄B)
- **AFM** (Antiferromagnetic): alternating ± → no net moment, but still magnetically ordered
- **FiM** (Ferrimagnetic): unequal opposing spins → weak net moment
- **NM** (Non-magnetic): no unpaired electrons

**Total Magnetization** — Net magnetic moment in Bohr magnetons (μB) per formula unit. Pure Fe ≈ 2.2 μB/atom. High magnetization + high coercivity = strong permanent magnet.

**Magnetic Sites** — How many atoms per unit cell carry unpaired electrons. Transition metals (Fe, Co, Ni) and rare earths (Nd, Sm) are common magnetic sites.
""")

@st.dialog("Mechanical & Thermal Properties")
def dlg_mechanical():
    st.markdown("""
**Bulk Modulus K** — Resistance to compression from all sides (GPa). Diamond ≈ 440. Steel ≈ 160. Rubber ≈ 0.002. Higher = harder to squeeze.

**Shear Modulus G** — Resistance to shape change without volume change (GPa). High G = scratch-resistant, hard to deform. Steel ≈ 80. Ice ≈ 4.

**Young's Modulus E** — Axial stiffness: how much the material stretches under tension (GPa). Computed as E = 9BG/(3B+G). Diamond ≈ 1050. Carbon fiber ≈ 300. Aluminum ≈ 70.

**Poisson Ratio ν** — How much a material expands sideways when compressed. Cork ≈ 0 (great bottle stopper). Most metals 0.25–0.35. Near 0.5 = rubber-like.

**Anisotropy Index AU** — 0 = stiffness is the same in all directions. > 1 = significant directional variation — the crystal has preferred cleavage planes.

**Specific Modulus E/ρ** — Stiffness per unit weight (GPa·cm³/g). The figure of merit for lightweight stiff structures. Space elevator cables need > 100. Steel ≈ 26. Diamond ≈ 350.

**Pugh Ratio B/G** — B/G > 1.75 → material deforms before breaking (ductile, like metals). B/G < 1.75 → material shatters (brittle, like ceramics).

**Thermal Conductivity κ** — How fast heat flows through (W/m·K). Diamond ≈ 2000. Copper ≈ 400. ZrO₂ ≈ 2 (great thermal barrier). Estimated from Debye temperature.

**Debye Temperature Θ_D** — Energy scale of lattice vibrations (K). High Θ_D = stiff bonds, high sound speed, high melting point. Diamond ≈ 2230 K. Lead ≈ 105 K.
""")

@st.dialog("Dielectric & Optical Properties")
def dlg_dielectric():
    st.markdown("""
**Total Dielectric Constant ε** — How much the material weakens an electric field at low frequency. Vacuum = 1. Silicon = 11.7. BaTiO₃ ≈ 1700. High ε = good capacitor, good plasma reflector.

**Electronic ε∞** — High-frequency response: how much electron clouds distort under a fast oscillating field. This is active at optical frequencies. Related to refractive index: **n = √ε∞**.

**Ionic εᵢₒₙ** — Contribution from polar bond vibrations (phonons). Only active at low / infrared frequencies. Large values in ferroelectrics and ionic crystals. Drops off at high frequency.

**Refractive Index n** — How much the material slows and bends light. Vacuum = 1. Glass ≈ 1.5. Diamond = 2.42. GaAs ≈ 3.6. Higher n = more reflective surface, more light bending at interfaces.

**Reflectivity R** — Fraction of light reflected at normal incidence: R = ((n−1)/(n+1))². Glass ≈ 4%. Diamond ≈ 17%. GaAs ≈ 32%. A high-n material looks shiny or mirror-like.

**Ionic Fraction** — What percentage of the total ε comes from ionic (phonon) vs electronic contributions. High ionic fraction means ε drops dramatically at microwave and higher frequencies.
""")

@st.dialog("Why this structure → this property", width="large")
def dlg_why():
    text   = st.session_state.get("_why_text",   "")
    accent = st.session_state.get("_why_accent", "#58a6ff")
    st.markdown(
        f'<div style="background:#161b22;border-left:3px solid {accent};'
        f'border-radius:0 6px 6px 0;padding:14px 18px;font-size:0.88rem;'
        f'line-height:1.7;color:#c9d1d9;">{text}</div>',
        unsafe_allow_html=True,
    )


@st.dialog("Note", width="large")
def note_dialog():
    mp_id   = st.session_state.get("_note_mp_id", "")
    formula = st.session_state.get("_note_formula", mp_id)
    st.markdown(f'<div style="font-size:0.72rem;color:#8b949e;margin-bottom:8px;">{formula} · {mp_id}</div>',
                unsafe_allow_html=True)
    existing = local_db.get_note(mp_id)
    new_text = st.text_area("", value=existing, height=220,
                             placeholder="Write your observations, questions, or insights about this compound…",
                             label_visibility="collapsed")
    ca, cb = st.columns([1, 1], gap="small")
    with ca:
        if st.button("Save", type="primary", use_container_width=True):
            local_db.save_note(mp_id, new_text)
            st.rerun()
    with cb:
        if existing and st.button("Clear", use_container_width=True):
            local_db.save_note(mp_id, "")
            st.rerun()


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
        marker=dict(size=4, color="#30363d", opacity=0.7),
        customdata=[p["mp_id"] for p in bg_pts],
        hovertemplate="%{text}  ·  click to navigate<extra></extra>",
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
            customdata=[cur_mp],
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
        clickmode="event",
    )
    event = st.plotly_chart(fig, on_select="rerun", key="pos_chart", width="stretch")
    st.markdown(
        f'<div style="font-size:0.58rem;color:#8b949e;margin-top:-6px;">'
        f'★ = {db_row.get("formula","")} · {len(rows):,} compounds · click any point to navigate</div>',
        unsafe_allow_html=True)

    # ── Handle chart click → navigate ─────────────────────────────────────────
    if event and event.selection and event.selection.points:
        clicked_mp = event.selection.points[0].get("customdata")
        if clicked_mp and clicked_mp != cur_mp:
            clicked_row = local_db.get_material_row(clicked_mp)
            clicked_formula = clicked_row.get("formula", clicked_mp) if clicked_row else clicked_mp
            clicked_curated = None
            for _cat, _cmpds in COMPOUNDS.items():
                for _n, _d in _cmpds.items():
                    if _d["mp_id"] == clicked_mp:
                        clicked_curated = _d
                        break
            st.session_state.mp_id         = clicked_mp
            st.session_state.compound_name  = clicked_formula
            st.session_state.curated_data   = clicked_curated
            st.session_state.ashby_mode     = False
            st.session_state.compare_mode   = False
            st.query_params["mp"]           = clicked_mp
            st.rerun()


# ── Comparison view ───────────────────────────────────────────────────────────
COMPARE_PROPS = [
    ("Band Gap",         "bandgap",                  "eV",      "higher"),
    ("Density",          "density",                  "g/cm³",   "lower"),
    ("Young's E",        "young_modulus",             "GPa",     "higher"),
    ("Bulk K",           "k_voigt",                  "GPa",     "higher"),
    ("Shear G",          "g_voigt",                  "GPa",     "higher"),
    ("Poisson ν",        "poisson_ratio",             "",        "lower"),
    ("Magnetization",    "total_magnetization",       "μB",      "higher"),
    ("Dielectric ε",     "e_total",                  "",        "higher"),
    ("Refr. Index n",    "refractive_index",          "",        "higher"),
    ("Thermal κ",        "thermal_conductivity",      "W/m·K",   "higher"),
    ("Debye Temp",       "debye_temperature",         "K",       "higher"),
    ("Formation E",      "formation_energy_per_atom", "eV/at",   "lower"),
    ("Hull Energy",      "energy_above_hull",         "eV/at",   "lower"),
]

def _delta_arrow(a, b, direction):
    """Return colored arrow + pct change string for value a vs b."""
    if a is None or b is None or b == 0:
        return ""
    pct = (a - b) / abs(b) * 100
    if abs(pct) < 0.5:
        return '<span style="color:#8b949e;">≈ same</span>'
    better = (pct > 0 and direction == "higher") or (pct < 0 and direction == "lower")
    color  = "#3fb950" if better else "#f85149"
    arrow  = "▲" if pct > 0 else "▼"
    return f'<span style="color:{color};">{arrow} {abs(pct):.1f}%</span>'

def render_compare_row(label, col, unit, direction, row_a, row_b, accent_a, accent_b):
    va = row_a.get(col) if row_a else None
    vb = row_b.get(col) if row_b else None
    if va is None and vb is None:
        return ""
    fmt = lambda v: f"{v:.3g} {unit}".strip() if v is not None else "—"
    delta_ab = _delta_arrow(va, vb, direction)   # A relative to B
    delta_ba = _delta_arrow(vb, va, direction)   # B relative to A
    return (
        f'<tr style="border-bottom:1px solid #21262d;">'
        f'<td style="padding:4px 6px;font-size:0.72rem;color:#8b949e;white-space:nowrap;">{label}</td>'
        f'<td style="padding:4px 8px;font-size:0.78rem;color:{accent_a};text-align:right;">'
        f'{fmt(va)}<br><span style="font-size:0.65rem;">{delta_ab}</span></td>'
        f'<td style="padding:4px 8px;font-size:0.78rem;color:{accent_b};text-align:right;">'
        f'{fmt(vb)}<br><span style="font-size:0.65rem;">{delta_ba}</span></td>'
        f'</tr>'
    )

def render_compare_page(mp_a, name_a, curated_a, mp_b, name_b, curated_b, api_key):
    accent_a = curated_a["accent"] if curated_a else "#58a6ff"
    accent_b = curated_b["accent"] if curated_b else "#f9ca24"
    fa = (curated_a["formula"] if curated_a else name_a) or mp_a
    fb = (curated_b["formula"] if curated_b else name_b) or mp_b

    row_a = local_db.get_material_row(mp_a)
    row_b = local_db.get_material_row(mp_b)

    try:
        struct_a = load_structure(mp_a, api_key)
    except Exception:
        struct_a = None
    try:
        struct_b = load_structure(mp_b, api_key)
    except Exception:
        struct_b = None

    # ── Title bar ──────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:18px;margin-bottom:8px;flex-wrap:wrap;">'
        f'<span style="font-size:1.4rem;font-weight:700;color:{accent_a};">{fa}</span>'
        f'<span style="font-size:1.1rem;color:#8b949e;">vs</span>'
        f'<span style="font-size:1.4rem;font-weight:700;color:{accent_b};">{fb}</span>'
        f'<span style="font-size:0.75rem;color:#8b949e;margin-left:auto;">Structure-to-property comparison</span>'
        f'</div>', unsafe_allow_html=True)

    # ── Crystal system summary tags ────────────────────────────────────────────
    def _sym_badge(row, curated, accent):
        parts = []
        if curated:
            parts.append(f'<span style="color:{accent};font-weight:600;">{curated.get("crystal_system","")}</span>')
            parts.append(f'<span style="color:#8b949e;">{curated.get("space_group","")}</span>')
        elif row:
            parts.append(f'<span style="color:{accent};font-weight:600;">{row.get("crystal_system","")}</span>')
            parts.append(f'<span style="color:#8b949e;">{row.get("space_group","")}</span>')
        return " · ".join(parts)

    st.markdown(
        f'<div style="display:flex;gap:40px;margin-bottom:6px;">'
        f'<div style="font-size:0.72rem;">{_sym_badge(row_a, curated_a, accent_a)}</div>'
        f'<div style="font-size:0.72rem;">{_sym_badge(row_b, curated_b, accent_b)}</div>'
        f'</div>', unsafe_allow_html=True)

    # ── 3D viewers side by side ────────────────────────────────────────────────
    v1, v2 = st.columns(2, gap="small")
    with v1:
        st.markdown(f'<div style="font-size:0.65rem;color:{accent_a};font-weight:600;margin-bottom:3px;">{fa}</div>',
                    unsafe_allow_html=True)
        if struct_a:
            st.components.v1.html(render_crystal(struct_a, accent_a, w=430, h=280), height=295, scrolling=False)
            lat = struct_a.lattice
            st.markdown(f'<div style="font-size:0.62rem;color:#8b949e;">a={lat.a:.3f} b={lat.b:.3f} c={lat.c:.3f} Å · {struct_a.num_sites} sites</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div style="height:280px;display:flex;align-items:center;justify-content:center;'
                        'background:#161b22;border-radius:6px;color:#8b949e;">Structure unavailable</div>',
                        unsafe_allow_html=True)
        if curated_a:
            if st.button(f"Why {fa} works", key="why_a", use_container_width=True):
                st.session_state["_why_text"]   = curated_a["why_it_works"]
                st.session_state["_why_accent"] = accent_a
                dlg_why()

    with v2:
        st.markdown(f'<div style="font-size:0.65rem;color:{accent_b};font-weight:600;margin-bottom:3px;">{fb}</div>',
                    unsafe_allow_html=True)
        if struct_b:
            st.components.v1.html(render_crystal(struct_b, accent_b, w=430, h=280), height=295, scrolling=False)
            lat = struct_b.lattice
            st.markdown(f'<div style="font-size:0.62rem;color:#8b949e;">a={lat.a:.3f} b={lat.b:.3f} c={lat.c:.3f} Å · {struct_b.num_sites} sites</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div style="height:280px;display:flex;align-items:center;justify-content:center;'
                        'background:#161b22;border-radius:6px;color:#8b949e;">Structure unavailable</div>',
                        unsafe_allow_html=True)
        if curated_b:
            if st.button(f"Why {fb} works", key="why_b", use_container_width=True):
                st.session_state["_why_text"]   = curated_b["why_it_works"]
                st.session_state["_why_accent"] = accent_b
                dlg_why()

    # ── Property comparison table ──────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:0.62rem;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;'
        f'font-weight:700;margin:10px 0 4px;">Property Comparison  '
        f'<span style="color:#8b949e;text-transform:none;font-weight:400;">'
        f'(arrows show improvement vs the other)</span></div>', unsafe_allow_html=True)

    rows_html = ""
    for (label, col, unit, direction) in COMPARE_PROPS:
        rows_html += render_compare_row(label, col, unit, direction, row_a, row_b, accent_a, accent_b)

    if rows_html:
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;background:#161b22;'
            f'border:1px solid #21262d;border-radius:6px;overflow:hidden;">'
            f'<thead><tr style="background:#0d1117;">'
            f'<th style="padding:5px 6px;font-size:0.65rem;color:#8b949e;text-align:left;">Property</th>'
            f'<th style="padding:5px 8px;font-size:0.65rem;color:{accent_a};text-align:right;">{fa}</th>'
            f'<th style="padding:5px 8px;font-size:0.65rem;color:{accent_b};text-align:right;">{fb}</th>'
            f'</tr></thead>'
            f'<tbody>{rows_html}</tbody></table>',
            unsafe_allow_html=True)

    # ── XRD overlay ───────────────────────────────────────────────────────────
    if struct_a or struct_b:
        st.markdown(
            '<div style="font-size:0.62rem;color:#8b949e;text-transform:uppercase;'
            'letter-spacing:.08em;font-weight:700;margin:10px 0 4px;">'
            'XRD Pattern Overlay (Cu Kα)</div>', unsafe_allow_html=True)
        try:
            fig_xrd = go.Figure()
            if struct_a:
                xa = get_xrd(json.dumps(struct_a.as_dict()))
                for x, y, hkl in zip(xa["two_theta"], xa["intensity"], xa["hkls"]):
                    fig_xrd.add_trace(go.Scatter(
                        x=[x, x, x], y=[0, y, 0], mode="lines",
                        line=dict(color=accent_a, width=1.5),
                        hovertemplate=f"{fa}  2θ={x:.2f}° I={y:.1f} {hkl}<extra></extra>",
                        name=fa, showlegend=(x == xa["two_theta"][0]),
                        legendgroup="A",
                    ))
            if struct_b:
                xb = get_xrd(json.dumps(struct_b.as_dict()))
                for x, y, hkl in zip(xb["two_theta"], xb["intensity"], xb["hkls"]):
                    fig_xrd.add_trace(go.Scatter(
                        x=[x, x, x], y=[0, -y, 0], mode="lines",
                        line=dict(color=accent_b, width=1.5),
                        hovertemplate=f"{fb}  2θ={x:.2f}° I={y:.1f} {hkl}<extra></extra>",
                        name=fb, showlegend=(x == xb["two_theta"][0]),
                        legendgroup="B",
                    ))
            fig_xrd.add_hline(y=0, line=dict(color="#30363d", width=1))
            if struct_a and struct_b:
                fig_xrd.add_annotation(
                    x=0.01, y=0.97, xref="paper", yref="paper",
                    text=f"{fa} (above 0)  ·  {fb} (below 0, mirrored)",
                    showarrow=False, font=dict(size=9, color="#8b949e"), align="left")
            fig_xrd.update_layout(
                xaxis_title="2θ (degrees)", yaxis_title="Intensity (↑A  ↓B)",
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                margin=dict(l=52, r=10, t=10, b=40), height=200,
                xaxis=dict(range=[0, 90], gridcolor="#21262d", tickfont=dict(size=9)),
                yaxis=dict(gridcolor="#21262d", tickfont=dict(size=9), zeroline=True,
                           zerolinecolor="#444"),
                legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
                            font=dict(size=9)),
                font=dict(size=10),
            )
            st.plotly_chart(fig_xrd, width="stretch")
        except Exception as exc:
            st.markdown(f'<div class="na">XRD error: {exc}</div>', unsafe_allow_html=True)

    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:0.82rem;font-weight:700;color:#e6edf3;'
        'letter-spacing:.06em;text-transform:uppercase;padding:6px 0 8px;'
        'border-bottom:1px solid #21262d;margin-bottom:6px;">'
        'MatSci <span style="color:#58a6ff;">Explorer</span></div>',
        unsafe_allow_html=True)
    api_key = os.environ.get("MP_API_KEY", "")
    if not api_key:
        api_key = st.text_input("MP API Key", type="password",
                                placeholder="materialsproject.org",
                                label_visibility="collapsed")
    search_q = st.text_input("Search", placeholder="Search formula / mp-id…",
                             label_visibility="collapsed")

    # ── Property filter search ─────────────────────────────────────────────
    with st.expander("Search by property", expanded=False):
        pf_prop = st.selectbox("Property", [
            "Bandgap (eV)", "Density (g/cm³)", "Young's E (GPa)",
            "Magnetization (μB)", "Dielectric ε", "Thermal κ (W/m·K)",
            "Formation E (eV/at)", "Hull Energy (eV/at)",
        ], key="pf_prop", label_visibility="collapsed")
        _pf_map = {
            "Bandgap (eV)": "bandgap", "Density (g/cm³)": "density",
            "Young's E (GPa)": "young_modulus", "Magnetization (μB)": "total_magnetization",
            "Dielectric ε": "e_total", "Thermal κ (W/m·K)": "thermal_conductivity",
            "Formation E (eV/at)": "formation_energy_per_atom",
            "Hull Energy (eV/at)": "energy_above_hull",
        }
        pf_col = _pf_map[pf_prop]
        pf_cond = st.radio("Condition", ["< (below)", "> (above)", "range"], key="pf_cond",
                           label_visibility="collapsed", horizontal=True)
        if pf_cond == "range":
            pf_lo = st.number_input("Min", value=0.0, key="pf_lo", format="%.3f")
            pf_hi = st.number_input("Max", value=3.0, key="pf_hi", format="%.3f")
            pf_sql = f"{pf_col} BETWEEN {pf_lo} AND {pf_hi}"
        else:
            pf_val = st.number_input("Value", value=2.0 if "eV" in pf_prop else 5.0,
                                     key="pf_val", format="%.3f")
            op = "<" if "<" in pf_cond else ">"
            pf_sql = f"{pf_col} {op} {pf_val}"
        # optional: direct bandgap only
        if pf_prop == "Bandgap (eV)":
            pf_direct = st.checkbox("Direct bandgap only", key="pf_direct")
            if pf_direct:
                pf_sql += " AND is_direct_gap = 1"
        if st.button("Search", key="pf_run"):
            with local_db.get_conn() as _conn:
                _conn.row_factory = __import__("sqlite3").Row
                _pf_rows = _conn.execute(
                    f"SELECT mp_id, formula, {pf_col} FROM materials "
                    f"WHERE {pf_col} IS NOT NULL AND {pf_sql} "
                    f"ORDER BY {pf_col} LIMIT 30"
                ).fetchall()
            st.session_state["_pf_results"] = [dict(r) for r in _pf_rows]
            st.session_state["_pf_label"]   = pf_prop

    st.divider()

    # Show property filter results if any
    if st.session_state.get("_pf_results"):
        lbl = st.session_state.get("_pf_label", "Matches")
        st.markdown(f'<div class="cat-hdr">{lbl} matches ({len(st.session_state["_pf_results"])})</div>',
                    unsafe_allow_html=True)
        pf_col_key = _pf_map.get(lbl, "")
        for r in st.session_state["_pf_results"]:
            val_str = f"  [{r.get(pf_col_key, ''):.3g}]" if r.get(pf_col_key) is not None else ""
            flabel  = f"{'▶ ' if r['mp_id']==st.session_state.mp_id else ''}{r['formula']}{val_str}"
            if st.button(flabel, key=f"pf_{r['mp_id']}"):
                st.session_state.mp_id        = r["mp_id"]
                st.session_state.compound_name = r["formula"]
                st.session_state.curated_data  = None
                st.session_state.ashby_mode    = False
                st.session_state.compare_mode  = False
                st.query_params["mp"] = r["mp_id"]
                st.rerun()
        if st.button("✕ Clear results", key="pf_clear"):
            st.session_state["_pf_results"] = None
            st.rerun()
        st.divider()

    CAT_SHORT = {
        "Strong Magnets":                      "Magnets",
        "Perovskites (Solar & Ferroelectric)": "Perovskites",
        "Semiconductors":                      "Semiconductors",
        "Space Elevator Candidates":           "Space Elevator",
        "Re-entry & Thermal Shield Materials": "Re-entry / Thermal",
        "Superconductors":                     "Superconductors",
        "Battery Cathodes & Anodes":           "Battery Materials",
        "Catalysts":                           "Catalysts",
        "Thermoelectrics":                     "Thermoelectrics",
        "Topological Insulators":              "Topological",
    }

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
                is_active = row["mp_id"] == st.session_state.mp_id
                if st.button(row["formula"], key=f"sr_{row['mp_id']}",
                             type="primary" if is_active else "secondary",
                             use_container_width=True):
                    st.session_state.mp_id        = row["mp_id"]
                    st.session_state.compound_name = row["formula"]
                    st.session_state.curated_data  = None
                    st.session_state.ashby_mode    = False
                    for _c in COMPOUNDS:
                        st.session_state.pop(f"dd_{_c}", None)
                    st.query_params["mp"] = row["mp_id"]
                    st.rerun()
        else:
            st.caption("No matches.")
    else:
        # ── 2-column category grid ─────────────────────────────────────────
        _chosen_cat = None
        _chosen_formula = None
        cats_list = list(COMPOUNDS.items())
        for _i in range(0, len(cats_list), 2):
            _pair = cats_list[_i:_i+2]
            _gcols = st.columns(2, gap="small")
            for _j, (cat, compounds) in enumerate(_pair):
                with _gcols[_j]:
                    hdr = CAT_SHORT.get(cat, cat)
                    items    = list(compounds.items())
                    formulas = [d["formula"] for _, d in items]
                    OPTIONS  = ["—"] + formulas
                    current_formula = next(
                        (d["formula"] for _, d in items
                         if d["mp_id"] == st.session_state.mp_id),
                        None,
                    )
                    default_idx = (formulas.index(current_formula) + 1) if current_formula else 0
                    chosen = st.selectbox(hdr, OPTIONS, index=default_idx, key=f"dd_{cat}")
                    if chosen != "—":
                        data_map = {d["formula"]: d for _, d in items}
                        name_map = {d["formula"]: n for n, d in items}
                        if data_map[chosen]["mp_id"] != st.session_state.mp_id:
                            _chosen_cat     = cat
                            _chosen_formula = chosen
                            _chosen_data    = data_map[chosen]
                            _chosen_name    = name_map[chosen]

        if _chosen_cat is not None:
            for other in COMPOUNDS:
                if other != _chosen_cat:
                    st.session_state.pop(f"dd_{other}", None)
            st.session_state.mp_id        = _chosen_data["mp_id"]
            st.session_state.compound_name = _chosen_name
            st.session_state.curated_data  = _chosen_data
            st.session_state.ashby_mode    = False
            st.session_state.compare_mode  = False
            st.query_params["mp"] = _chosen_data["mp_id"]
            st.rerun()

    st.divider()
    # ── Pin / Compare controls ─────────────────────────────────────────────
    cur_formula = (
        st.session_state.curated_data["formula"]
        if st.session_state.curated_data else st.session_state.mp_id
    )
    cur_is_pinned = st.session_state.mp_id == st.session_state.compare_mp_id

    if st.session_state.compare_mp_id:
        cname = st.session_state.compare_name or st.session_state.compare_mp_id
        st.markdown(
            f'<div style="font-size:0.63rem;color:#d29922;margin-bottom:3px;">'
            f'<b>{cname}</b> pinned</div>', unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns([2, 2, 1], gap="small")
        with cc1:
            cmp_lbl = "Active" if st.session_state.compare_mode else "Compare"
            if st.button(cmp_lbl, width="stretch"):
                st.session_state.compare_mode = not st.session_state.compare_mode
                st.session_state.ashby_mode   = False
                st.rerun()
        with cc2:
            if not cur_is_pinned:
                if st.button(f"Pin {cur_formula}", width="stretch",
                             help="Replace pin with current compound"):
                    st.session_state.compare_mp_id   = st.session_state.mp_id
                    st.session_state.compare_name    = cur_formula
                    st.session_state.compare_curated = st.session_state.curated_data
                    st.session_state.compare_mode    = False
                    st.rerun()
        with cc3:
            if st.button("✕", width="stretch", help="Unpin"):
                st.session_state.compare_mp_id   = None
                st.session_state.compare_name    = None
                st.session_state.compare_curated = None
                st.session_state.compare_mode    = False
                st.rerun()
    else:
        if st.button(f"Pin  {cur_formula}", width="stretch",
                     help="Pin this compound for side-by-side comparison"):
            st.session_state.compare_mp_id   = st.session_state.mp_id
            st.session_state.compare_name    = cur_formula
            st.session_state.compare_curated = st.session_state.curated_data
            st.rerun()

    ashby_lbl = "Ashby Charts  (active)" if st.session_state.ashby_mode else "Ashby Charts"
    if st.button(ashby_lbl, width="stretch"):
        st.session_state.ashby_mode  = not st.session_state.ashby_mode
        st.session_state.compare_mode = False
        st.rerun()
    st.divider()
    db_info = local_db.stats()
    st.caption(
        f"**{db_info['total']:,}** compounds  \n"
        f"Elastic: {db_info['with_elasticity']}  ·  ε: {db_info['with_dielectric']}"
    )


# ── Ashby Charts ──────────────────────────────────────────────────────────────
# ── Compare mode ─────────────────────────────────────────────────────────────
if st.session_state.compare_mode and st.session_state.compare_mp_id:
    mp_a   = st.session_state.mp_id
    name_a = st.session_state.compound_name
    cur_a  = st.session_state.curated_data
    mp_b   = st.session_state.compare_mp_id
    name_b = st.session_state.compare_name
    cur_b  = st.session_state.compare_curated
    if mp_a and mp_b and mp_a != mp_b:
        render_compare_page(mp_a, name_a, cur_a, mp_b, name_b, cur_b, api_key)
    else:
        st.warning("Select a different compound to compare against the pinned one.")
        st.session_state.compare_mode = False

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
    st.markdown("## Ashby Material Selection Charts")
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


# ── Main 2-column layout ──────────────────────────────────────────────────────
TAB_H   = 500   # scrollable height inside each tab panel
VIEWER_H = 320  # 3D viewer height

left_col, right_col = st.columns([40, 60], gap="medium")

# ── LEFT: crystal viewer + why + position chart ────────────────────────────────
with left_col:
    if structure:
        st.components.v1.html(
            render_crystal(structure, accent, w=430, h=VIEWER_H),
            height=VIEWER_H + 16, scrolling=False)
        lat = structure.lattice
        st.markdown(
            f'<div class="lat-info">'
            f'a={lat.a:.3f} &nbsp;b={lat.b:.3f} &nbsp;c={lat.c:.3f} Å'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'α={lat.alpha:.1f}° &nbsp;β={lat.beta:.1f}° &nbsp;γ={lat.gamma:.1f}°'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;{structure.num_sites} sites</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="background:#161b22;border:1px dashed #30363d;border-radius:8px;'
            f'height:{VIEWER_H}px;display:flex;align-items:center;justify-content:center;'
            f'color:#8b949e;font-size:0.8rem;">Structure unavailable</div>',
            unsafe_allow_html=True)

    if curated_data:
        why_text = curated_data["why_it_works"]
        st.markdown(
            f'<div class="why-hover-wrap">'
            f'<span class="why-trigger">Why this structure → this property</span>'
            f'<div class="why-popup" style="border-left:3px solid {accent};">'
            f'{why_text}</div></div>',
            unsafe_allow_html=True)

    # Note button
    existing_note = local_db.get_note(selected_mp_id)
    note_label = f"Note ({len(existing_note)} chars)" if existing_note else "Add note"
    st.markdown('<div class="note-btn-wrap">', unsafe_allow_html=True)
    if st.button(note_label, key="note_btn"):
        st.session_state["_note_mp_id"]   = selected_mp_id
        st.session_state["_note_formula"] = formula_display
        note_dialog()
    st.markdown('</div>', unsafe_allow_html=True)

    # Position in property space (compact)
    if db_row:
        st.markdown(
            '<div style="font-size:0.6rem;color:#8b949e;text-transform:uppercase;'
            'letter-spacing:.09em;font-weight:700;margin:6px 0 2px;">Position in property space</div>',
            unsafe_allow_html=True)
        try:
            render_position_chart(db_row, accent, chart_h=170)
        except Exception:
            pass

# ── RIGHT: property panels (grid layout) ──────────────────────────────────────
with right_col:
    # Row 1: Electronic & Magnetic | Mechanical & Thermal
    r1c1, r1c2 = st.columns(2, gap="medium")
    with r1c1:
        st.markdown('<div class="section-hdr">Electronic & Magnetic</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_electronic(db_row)}</div>',
                    unsafe_allow_html=True)
    with r1c2:
        st.markdown('<div class="section-hdr">Mechanical & Thermal</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_mechanical(db_row)}</div>',
                    unsafe_allow_html=True)

    # Row 2: Dielectric & Optical | Stability & Physical
    r2c1, r2c2 = st.columns(2, gap="medium")
    with r2c1:
        st.markdown('<div class="section-hdr">Dielectric & Optical</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_dielectric(db_row)}</div>',
                    unsafe_allow_html=True)
    with r2c2:
        st.markdown('<div class="section-hdr">Stability & Physical</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_stability(db_row, pc_data)}</div>',
                    unsafe_allow_html=True)

    # XRD Pattern (full width)
    st.markdown('<div class="section-hdr" style="margin-top:12px;">XRD Pattern (Cu Kα)</div>',
                unsafe_allow_html=True)
    if structure:
        try:
            xrd = get_xrd(json.dumps(structure.as_dict()))
            fig = go.Figure()
            for x, y, hkl in zip(xrd["two_theta"], xrd["intensity"], xrd["hkls"]):
                fig.add_trace(go.Scatter(
                    x=[x, x, x], y=[0, y, 0], mode="lines",
                    line=dict(color=accent, width=1.5),
                    hovertemplate=f"2θ={x:.2f}° &nbsp;I={y:.1f} &nbsp;{hkl}<extra></extra>",
                    showlegend=False,
                ))
            fig.update_layout(
                xaxis_title="2θ (degrees)", yaxis_title="Intensity",
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                margin=dict(l=48, r=10, t=8, b=44), height=220,
                xaxis=dict(range=[0, 90], gridcolor="#21262d", tickfont=dict(size=10)),
                yaxis=dict(range=[0, 110], gridcolor="#21262d", tickfont=dict(size=10)),
            )
            st.plotly_chart(fig, width="stretch")
            st.caption("Cu Kα  λ = 1.5406 Å  ·  Simulated from crystal structure")
        except Exception as exc:
            st.markdown(f'<div class="na">XRD error: {exc}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="na">Structure not loaded — XRD unavailable.</div>',
                    unsafe_allow_html=True)

    # About / Wikipedia (full width)
    wiki_title = curated_data.get("wiki_search") if curated_data else None
    if wiki_title:
        @st.cache_data(show_spinner=False)
        def _get_wiki(title): return wiki_api.fetch_wiki_summary(title)
        wiki = _get_wiki(wiki_title)
        if wiki:
            st.markdown('<div class="section-hdr" style="margin-top:12px;">About</div>',
                        unsafe_allow_html=True)
            has_thumb = bool(wiki.get("thumbnail", {}).get("source"))
            if has_thumb:
                wa, wb = st.columns([3, 1], gap="medium")
            else:
                wa = st.container()
            with wa:
                st.markdown(
                    f'<div style="font-size:0.84rem;line-height:1.65;color:#c9d1d9;'
                    f'background:#161b22;border-radius:8px;padding:14px 16px;">'
                    f'{wiki.get("extract", "No description available.")}</div>',
                    unsafe_allow_html=True)
                page_url = wiki.get("content_urls", {}).get("desktop", {}).get("page", "")
                if page_url:
                    st.markdown(
                        f'<div style="margin-top:10px;font-size:0.75rem;">'
                        f'<a href="{page_url}" target="_blank" style="color:#58a6ff;">'
                        f'Read full article on Wikipedia</a></div>',
                        unsafe_allow_html=True)
            if has_thumb:
                with wb:
                    st.image(wiki["thumbnail"]["source"], use_container_width=True)
