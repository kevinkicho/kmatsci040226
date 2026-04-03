# app.py — MatSci Explorer
import base64, bisect, io, csv, os, json
import streamlit as st
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
import predict as ml_mod

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
local_db.init_db()

st.set_page_config(page_title="MatSci Explorer", page_icon="⚛",
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
header[data-testid="stHeader"] { display:none; }
#MainMenu, footer { visibility:hidden; }
.block-container { padding:0.2rem 0.8rem 0 0.8rem !important; max-width:100% !important; }
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
  padding:4px 8px; margin-bottom:3px; }
.sc-l { font-size:0.60rem; color:#8b949e; text-transform:uppercase;
  letter-spacing:.06em; display:block; }
.sc-v { font-size:0.82rem; color:#e6edf3; font-weight:500; }
.sc-n { font-size:0.64rem; color:#8b949e; }
/* Rank bar */
.sc-rank { height:4px; border-radius:2px; margin:3px 0 2px; background:#21262d; }
.sc-rank-f { height:100%; border-radius:2px; transition:width 0.3s ease; }

/* Scrollable panel */
.panel { overflow-y:auto; scrollbar-width:thin; scrollbar-color:#30363d transparent; padding-right:2px; }

/* KPI */
.krow { display:flex; gap:4px; margin:2px 0 4px; flex-wrap:nowrap; }
.kpi  { background:#161b22; border:1px solid #21262d; border-radius:5px;
  padding:3px 8px; flex:1; min-width:0; position:relative; }
.kpi-tip { cursor:help; }
.kpi-tip:hover .ttip-box { visibility:visible; opacity:1; }
.kl   { font-size:0.55rem; color:#8b949e; text-transform:uppercase; letter-spacing:.06em;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.kv   { font-size:0.88rem; font-weight:600; color:#e6edf3;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ku   { font-size:0.60rem; color:#8b949e; }

/* Badges */
.badge { display:inline-block; background:#21262d; border:1px solid #30363d;
  border-radius:10px; padding:1px 9px; font-size:0.7rem; color:#8b949e;
  margin-right:4px; margin-bottom:3px; }
.badge-green  { border-color:#238636; color:#3fb950; background:#0d2818; }
.badge-orange { border-color:#9e6a03; color:#d29922; background:#2d1f00; }
.badge-red    { border-color:#8b1a1a; color:#f85149; background:#2d0000; }
.badge-blue   { border-color:#1f6feb; color:#58a6ff; background:#0d1f3c; }

.sh { font-size:0.60rem; color:#58a6ff; text-transform:uppercase;
  letter-spacing:.1em; margin:6px 0 3px; font-weight:700; }
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
  margin-bottom:1px !important; line-height:1.2 !important;
  white-space:nowrap !important; overflow:hidden !important;
  text-overflow:ellipsis !important; cursor:help !important; }
/* Hide the ? help icon — label itself is the hover target */
[data-testid="stSidebar"] .stSelectbox [data-testid="stTooltipIcon"] {
  display:none !important; }
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {
  min-height:24px !important; font-size:0.70rem !important;
  padding:2px 6px !important;
  background:#0d1117 !important; border-color:#21262d !important; }
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child:hover {
  border-color:#30363d !important; }
/* Prevent selected value text from wrapping inside the dropdown box */
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {
  white-space:nowrap !important; overflow:hidden !important;
  text-overflow:ellipsis !important; }
[data-testid="stSidebar"] .stColumns { gap:6px !important; }
[data-testid="stSidebar"] .stColumn  { padding:0 2px !important; }

/* ── Multiselect: show all selected pills (no "+N more" truncation) ── */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {
  height: auto !important;
  max-height: none !important;
  flex-wrap: wrap !important;
  overflow: visible !important;
}

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

/* ── Universal hover tooltip (.ttip) ────────────────────── */
.ttip { position:relative; cursor:help; display:inline-block; }
.ttip-block { position:relative; cursor:help; display:block; }
.ttip-box {
  visibility:hidden; opacity:0;
  position:absolute; z-index:10000; pointer-events:none;
  top:calc(100% + 5px); left:0;
  min-width:210px; max-width:290px;
  background:#1c2128; border:1px solid #30363d; border-radius:7px;
  padding:9px 13px;
  font-size:0.70rem; color:#c9d1d9; line-height:1.55;
  white-space:normal; text-transform:none;
  letter-spacing:normal; font-weight:400;
  box-shadow:0 8px 24px rgba(0,0,0,0.65);
  transition:opacity 0.15s ease, visibility 0.15s ease; }
.ttip:hover .ttip-box,
.ttip-block:hover .ttip-box { visibility:visible; opacity:1; }
.ttip-title { font-size:0.68rem; font-weight:700; color:#e6edf3;
  margin-bottom:4px; display:block; }

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
.section-hdr { font-size:0.60rem; color:#58a6ff; text-transform:uppercase;
  letter-spacing:.1em; font-weight:700; margin:7px 0 4px; padding-bottom:3px;
  border-bottom:1px solid #21262d; }
.section-hdr:first-child { margin-top:0; }

/* ── 2-column stat card grid ─────────────────────────────── */
.sc-grid { display:grid; grid-template-columns:1fr 1fr; gap:3px; margin-top:3px; }
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

/* ── Action button row (CSV / CIF / etc.) ────────────────── */
.action-row { display:flex; gap:6px; margin:4px 0 6px; flex-wrap:wrap; }
.action-row .stDownloadButton > button, .action-row .stButton > button {
  background:#161b22 !important; border:1px solid #30363d !important;
  color:#8b949e !important; font-size:0.64rem !important;
  padding:3px 10px !important; border-radius:5px !important;
  min-height:0 !important; height:auto !important;
  transition: border-color 0.15s, color 0.15s !important; }
.action-row .stDownloadButton > button:hover, .action-row .stButton > button:hover {
  border-color:#58a6ff !important; color:#e6edf3 !important; }

/* ── Find Similar list ───────────────────────────────────── */
.sim-item { display:flex; justify-content:space-between; align-items:center;
  padding:4px 8px; border-radius:4px; margin-bottom:2px;
  background:#161b22; border:1px solid #21262d;
  font-size:0.72rem; color:#c9d1d9; cursor:pointer; }
.sim-dist { font-size:0.62rem; color:#484f58; }

/* ── Application badge strip ─────────────────────────────── */
.app-badge { display:inline-flex; align-items:center; gap:5px;
  background:#161b22; border:1px solid #21262d; border-radius:6px;
  padding:4px 10px; margin:3px 3px 3px 0; font-size:0.70rem; color:#c9d1d9; }
.app-badge .ab-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }

/* ── ML prediction card ──────────────────────────────────── */
.pred-card { background:#161b22; border:1px solid #21262d; border-radius:6px;
  padding:10px 14px; margin:6px 0; }
.pred-val { font-size:1.2rem; font-weight:700; color:#e3b341; }
.pred-sub { font-size:0.62rem; color:#484f58; margin-top:2px; }

/* ── Collection item ─────────────────────────────────────── */
.col-item { font-size:0.70rem; padding:3px 6px; border-radius:4px;
  background:#161b22; border:1px solid #21262d; margin-bottom:2px;
  color:#c9d1d9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

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
    "universal_anisotropy":      "universal_anisotropy >= 0 AND universal_anisotropy < 20",
    "e_ionic":                   "e_ionic > 0 AND e_ionic < 200",
    "volume":                    "volume > 0 AND volume < 5000",
    "nsites":                    "nsites > 0 AND nsites < 200",
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


# Columns where a LOWER value is better (all others treat higher = better)
_LOWER_IS_BETTER = {"formation_energy_per_atom", "energy_above_hull"}

def pct_rank(raw_val, col: str):
    """
    Return 'top X%' float (0.5–100) where SMALL = impressive.
    'Top 5%' means this compound ranks in the top 5% of the database for this property.
    """
    if raw_val is None:
        return None
    stats = col_stats(col)
    if not stats or stats["n"] == 0:
        return None
    vals = stats["sorted"]
    idx = bisect.bisect_left(vals, raw_val)
    pct_from_bottom = idx / stats["n"] * 100          # 0 = lowest value, 100 = highest
    if col in _LOWER_IS_BETTER:
        # Smaller value → lower idx → smaller pct_from_bottom → better rank
        top_pct = pct_from_bottom
    else:
        # Larger value → higher pct_from_bottom → better rank → top% = 100 - pct_from_bottom
        top_pct = 100.0 - pct_from_bottom
    return max(top_pct, 0.5)                           # clamp to avoid 0% edge case


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
if "browse_mode" not in st.session_state:
    st.session_state.browse_mode = False
if "browse_page" not in st.session_state:
    st.session_state.browse_page = 0
if "compare_mp_id" not in st.session_state:
    st.session_state.compare_mp_id = None
if "compare_name" not in st.session_state:
    st.session_state.compare_name = None
if "compare_curated" not in st.session_state:
    st.session_state.compare_curated = None

# ── URL query-param sync (enables browser back/forward) ───────────────────────
# On a fresh server start the browser may still have ?mp=... from the prior
# session.  We clear it once per Python session so the app starts at the
# default compound, then re-sync as the user navigates.
if "session_initialized" not in st.session_state:
    st.session_state.session_initialized = True
    st.query_params.clear()

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
# ── Tooltip knowledge dictionaries ───────────────────────────────────────────

_CS_TIPS = {
    "cubic":        "<b>Cubic</b> — Three equal axes, all angles 90°. Highest symmetry of the 7 crystal systems. Includes FCC, BCC, and diamond structures. Examples: Fe, NaCl, Si.",
    "hexagonal":    "<b>Hexagonal</b> — Two equal axes at 120°, third axis perpendicular. Common in close-packed metals and layered materials. Examples: graphite, Mg, ice.",
    "tetragonal":   "<b>Tetragonal</b> — Two equal axes, third different, all angles 90°. Like a stretched or squashed cube. Examples: TiO₂ (rutile), In, white tin.",
    "orthorhombic": "<b>Orthorhombic</b> — Three unequal axes, all angles 90°. Common in minerals and organic crystals. Examples: BaSO₄, Ga, olivine.",
    "trigonal":     "<b>Trigonal</b> — Three equal axes at equal angles (rhombohedral) or viewed as hexagonal with 3-fold symmetry. Examples: Bi₂Te₃, calcite, quartz.",
    "monoclinic":   "<b>Monoclinic</b> — Three unequal axes, one angle ≠ 90°. Still has one mirror plane or 2-fold rotation axis. Examples: gypsum, Se, many silicates.",
    "triclinic":    "<b>Triclinic</b> — All three axes unequal, no angle = 90°. Lowest symmetry — only possible symmetry is inversion. Examples: feldspar, CuSO₄·5H₂O.",
}

_SG_TIPS = {
    "Fm-3m":   "<b>Fm-3m</b> — Cubic face-centered (FCC). Highest-symmetry cubic group. Atoms at cube corners + face centers. Found in Cu, Al, NaCl structure, many metals.",
    "Im-3m":   "<b>Im-3m</b> — Cubic body-centered (BCC). Atom at corners + body center. Found in Fe (α,δ), W, Mo, Cr.",
    "Fd-3m":   "<b>Fd-3m</b> — Diamond cubic. FCC with a 2-atom basis giving a tetrahedral network. Found in Si, Ge, diamond.",
    "F-43m":   "<b>F-43m</b> — Zinc-blende structure. Like diamond but with two atom types. Found in GaAs, InP, ZnS.",
    "P63/mmc": "<b>P6₃/mmc</b> — Hexagonal close-packed (HCP). Atoms stacked ABAB... Very common in metals: Mg, Ti, Zn. Also graphite.",
    "R-3m":    "<b>R-3m</b> — Rhombohedral layered structure. 3-fold axis + mirror planes. Classic structure for topological insulators: Bi₂Te₃, Bi₂Se₃.",
    "Pm-3m":   "<b>Pm-3m</b> — Simple cubic with full mirror symmetry. Prototype for perovskites (ABO₃) at high temperature. Found in CsCl, cubic BaTiO₃.",
    "Pnma":    "<b>Pnma</b> — Orthorhombic with glide planes and screw axes. One of the most common space groups — over 12% of all known structures. Found in distorted perovskites, olivine.",
    "P63mc":   "<b>P6₃mc</b> — Hexagonal with 6₃ screw axis and mirror planes. Found in wurtzite structure: ZnO, GaN, many semiconductors.",
    "C2/c":    "<b>C2/c</b> — Monoclinic with C-centering and glide plane. Common in silicates, pyroxenes, organic compounds.",
    "P-1":     "<b>P-1</b> — Triclinic with only an inversion center. Minimum symmetry possible in a crystal. Very common in molecular/organic crystals.",
    "R-3m:H":  "<b>R-3m (hexagonal setting)</b> — Layered rhombohedral structure in the hexagonal description. Found in Bi₂Te₃-family topological insulators and Li-ion cathodes like LiCoO₂.",
    "P-3m1":   "<b>P-3m1</b> — Trigonal structure with 3-fold symmetry and vertical mirror planes. Found in simple layered compounds.",
    "P4/mmm":  "<b>P4/mmm</b> — Tetragonal with full mirror symmetry. Common in cuprate superconductors and layered oxides.",
    "I4/mmm":  "<b>I4/mmm</b> — Body-centered tetragonal with full mirror symmetry. Found in high-Tc superconductors and intermetallics.",
    "Cmcm":    "<b>Cmcm</b> — C-centered orthorhombic. Common in layered and chain structures.",
}

_CAT_TIPS = {
    "Strong Magnets":                      "Permanent magnet materials with extremely high energy product (B·H)max. Tiny volume = huge field. Used in EV motors, MRI machines, wind turbines, loudspeakers.",
    "Perovskites (Solar & Ferroelectric)": "ABO₃ crystal structure — small B-cation in an oxygen octahedron, large A-cation filling the gaps. Enormously tunable: ferroelectric, piezoelectric, superconducting, or photovoltaic depending on A and B.",
    "Semiconductors":                      "Materials with a band gap between 0 and ~3 eV — small enough for electrons to jump with thermal energy or light. The foundation of transistors, diodes, solar cells, and LEDs.",
    "Space Elevator Candidates":           "Materials with ultra-high specific strength (strength ÷ density). A space elevator tether would need specific strength ~50× better than the best steel cables. Covalent ceramics and composites lead here.",
    "Re-entry & Thermal Shield Materials": "Ultra-high-temperature ceramics (UHTCs) stable above 2000°C with low thermal expansion and high thermal shock resistance. Used in spacecraft nose cones and rocket nozzle liners.",
    "Superconductors":                     "Zero DC electrical resistance below a critical temperature Tc, and expulsion of magnetic fields (Meissner effect). Used in MRI magnets, particle accelerators, maglev trains, and quantum computers.",
    "Battery Cathodes & Anodes":           "Li-ion battery electrode materials. Cathodes (positive) store Li⁺ between layers; anodes (negative) intercalate Li into graphite or convert. Choice determines voltage, energy density, and cycle life.",
    "Catalysts":                           "Materials that lower the activation energy of chemical reactions without being consumed. Essential for catalytic converters, fuel cells, industrial synthesis (Haber-Bosch), and pollution control.",
    "Thermoelectrics":                     "Convert heat gradients directly to electricity (Seebeck effect) or vice versa (Peltier). Performance = ZT = S²σT/κ. Need high Seebeck S, high conductivity σ, and low thermal conductivity κ — competing demands.",
    "Topological Insulators":              "Bulk insulators with topologically protected metallic surface states. Surface electrons cannot be backscattered by non-magnetic defects — relevant for dissipationless spintronic devices and quantum computing.",
}

_SECTION_TIPS = {
    "Electronic & Magnetic": "DFT-computed electronic structure: band gap, band edge energies (CBM/VBM), gap type, and magnetic ordering from spin-polarized calculations.",
    "Mechanical & Thermal":  "Elastic stiffness from DFT stress-strain simulations. Voigt and Reuss bounds are averaged (Hill average) to give polycrystalline moduli. Thermal properties estimated from elastic wave velocities.",
    "Dielectric & Optical":  "Frequency-dependent dielectric response from density functional perturbation theory (DFPT). ε_total = ε_ionic + ε_electronic. Refractive index n = √ε_electronic at optical frequencies.",
    "Stability & Physical":  "Thermodynamic stability from the convex hull of DFT formation energies. Hull energy = 0 means the stable ground state; > 0.025 eV/atom is typically not synthesizable at ambient conditions.",
    "Applications":          "Rule-based application tags derived from computed properties. Not exhaustive — used as a starting point to explore what technologies this material is relevant to.",
    "Property Radar":        "Spider chart normalizing each property to 0–1 relative to the full database range. Lets you compare the overall 'fingerprint' of two compounds at a glance.",
    "ML Bandgap Prediction": "A GradientBoostingRegressor trained on the local database using only structural and compositional descriptors (no electronic structure input). Shows how well crystal geometry alone predicts the band gap.",
    "XRD Pattern (Cu Kα)":   "Simulated powder X-ray diffraction using Cu Kα radiation (λ=1.5406 Å). Peak positions follow Bragg's law: 2d·sinθ = nλ. Heights approximate structure factors; no broadening or instrumental effects.",
    "About":                 "Plain-language summary fetched from Wikipedia and cached locally. Covers history of discovery, key applications, and notable physical properties.",
    "Electronic Structure":  "Density of states (DOS): how many electron energy levels exist at each energy. Band structure: how electron energy varies along high-symmetry paths in reciprocal space (k-space).",
    "Parallel Coordinates Explorer": "Multi-property comparison across all compounds in the database. Each vertical axis = one property; each polyline = one compound. Scroll to zoom; hover any line for details.",
}

_SH_TIPS = {
    "Electronic":              "Band gap, CBM, and VBM from the DFT band structure. CBM = conduction band minimum (lowest empty state); VBM = valence band maximum (highest filled state).",
    "Magnetic":                "Magnetic ordering from spin-polarized DFT. FM = ferromagnetic (all spins parallel), AFM = antiferromagnetic (alternating ±), FiM = ferrimagnetic (unequal opposing), NM = non-magnetic.",
    "Elastic Moduli":          "Polycrystalline averages from the full elastic stiffness tensor Cᵢⱼ. Bulk K resists compression; shear G resists shape change; Young's E = uniaxial stiffness; Poisson ν = lateral contraction ratio.",
    "Thermal":                 "Thermal conductivity estimated from Clarke and Cahill models (uses elastic moduli + density). Debye temperature θD is the phonon energy scale — above θD, classical heat capacity is reached.",
    "Dielectric & Optical":   "Static dielectric constant ε measures polarization in a DC field. The electronic part ε∞ responds at optical frequencies. Refractive index n = √ε∞; reflectivity R = ((n−1)/(n+1))².",
    "Thermodynamic Stability": "Convex hull distance: the energy (eV/atom) above the most stable phase(s) at this composition. Zero = ground state. Values > 0.025 eV/atom usually mean the compound is hard or impossible to synthesize.",
    "Physical & Structural":  "Unit cell parameters from the DFT-relaxed structure. Volume and density reflect the equilibrium lattice constant (typically slightly overestimated by GGA DFT).",
}

_KPI_TIPS = {
    "Density":       "Mass per unit volume (g/cm³). Determined by atomic masses and packing efficiency. Low density + high stiffness = high specific strength — key for aerospace and structural applications.",
    "Band Gap":      "Energy window forbidden to electrons (eV). Zero = metal. 0–3 eV = semiconductor. >3 eV = insulator. The gap controls optical absorption, electrical conductivity, and transistor switching.",
    "Young's E":     "Axial stiffness — force needed to stretch or compress per unit area (GPa). Steel ≈ 200 GPa, diamond ≈ 1050 GPa, rubber < 0.1 GPa. High E = stiff; low E = flexible.",
    "Bulk K":        "Resistance to uniform compression (GPa). Higher = harder to compress. Directly related to the second derivative of the energy-volume curve. Diamond K ≈ 440 GPa.",
    "Dielectric ε":  "Static dielectric constant. How much the material polarizes in an electric field. Higher = stronger field shielding / more charge stored per volt. Metals → ε = ∞.",
    "Refr. Index":   "Optical refractive index n = √ε_electronic. Controls how light bends (Snell's law) and surface reflectivity R = ((n−1)/(n+1))². Diamond n ≈ 2.42; glass n ≈ 1.5.",
    "Magnetization": "Total magnetic moment per formula unit (μB/f.u.). Non-zero in ferro-, ferri-, and antiferromagnetic materials. One Bohr magneton (μB) ≈ 9.27×10⁻²⁴ J/T.",
    "Thermal κ":     "Rate of heat flow per unit temperature gradient (W/m·K). Diamond ≈ 2000; Cu ≈ 400; stainless steel ≈ 15; thermal barrier coatings target < 3 W/m·K.",
}

_BADGE_TIPS = {
    "Stable":                  "Energy above the convex hull = 0 eV/atom. This is the thermodynamic ground state at this composition — the phase that forms at equilibrium.",
    "Experimentally observed":  "At least one entry in the ICSD (Inorganic Crystal Structure Database) matches this compound — meaning it has been synthesized and its structure confirmed by experiment.",
    "Computational only":       "No experimental crystal structure in the ICSD. This structure comes from DFT calculations or structure prediction — it may or may not be synthesizable.",
}

def _sg_tip(sg: str) -> str:
    if sg in _SG_TIPS:
        return _SG_TIPS[sg]
    return (f"<b>{sg}</b> — one of the 230 space groups that classify all possible 3D "
            f"crystal symmetries. The symbol encodes point-group operations (rotations, "
            f"reflections) plus translational symmetries (screw axes, glide planes).")

def badge(text, style="", tooltip=""):
    cls = f"badge badge-{style}" if style else "badge"
    inner = f'<span class="{cls}">{text}</span>'
    if tooltip:
        return f'<span class="ttip">{inner}<span class="ttip-box">{tooltip}</span></span>'
    return inner

def _rank_tier(top_pct: float) -> tuple:
    """
    5-tier ranking system.  top_pct is 'top X%' where small = impressive.
    Returns (tier_label, text_color, bar_color, track_color).
    """
    if top_pct <= 10:
        return "Exceptional", "#3fb950", "#2ea043", "#0d2818"   # emerald
    if top_pct <= 25:
        return "Strong",      "#58a6ff", "#1f6feb", "#0d1f3c"   # blue
    if top_pct <= 50:
        return "Average",     "#e3b341", "#9e6a03", "#2d2000"   # amber
    if top_pct <= 75:
        return "Below avg",   "#e08547", "#b45309", "#3a1500"   # orange
    return     "Low",         "#f85149", "#c63131", "#3c0a09"   # crimson

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
            # bar fills proportionally to how much of the DB this value surpasses
            beats_pct = 100.0 - top_pct   # uniform for all cols: top 5% → bar 95% full
            tier, txt_color, bar_color, track_color = _rank_tier(top_pct)
            n_total = col_stats(col).get("total", 6816)
            top_label = "< 1" if top_pct < 1 else f"{top_pct:.0f}"
            rank_html = (
                f'<div class="sc-rank" style="background:{track_color};">'
                f'<div class="sc-rank-f" style="background:{bar_color};width:{beats_pct:.1f}%;"></div></div>'
                f'<div class="sc-n" style="color:{txt_color};font-size:0.63rem;">'
                f'<span style="font-weight:600;">{tier}</span>'
                f'<span style="color:#484f58;"> · top {top_label}% of {n_total:,}</span></div>'
            )

    return (f'<div class="sc">{lbl_html}'
            f'<div class="sc-v">{value}</div>'
            f'{note_html}{rank_html}</div>')

def sh(text, tooltip=""):
    tt = tooltip or _SH_TIPS.get(text, "")
    if tt:
        return (f'<div class="sh"><span class="ttip">'
                f'{text}<span class="ttip-box">{tt}</span></span></div>')
    return f'<div class="sh">{text}</div>'

def na(msg="Not available"): return f'<div class="na">{msg}</div>'

def kpi(label, value, unit="", tooltip=""):
    tt = tooltip or _KPI_TIPS.get(label, "")
    if tt:
        return (f'<div class="kpi kpi-tip">'
                f'<div class="kl">{label}</div>'
                f'<div class="kv">{value}<span class="ku"> {unit}</span></div>'
                f'<span class="ttip-box">{tt}</span></div>')
    return (f'<div class="kpi"><div class="kl">{label}</div>'
            f'<div class="kv">{value}<span class="ku"> {unit}</span></div></div>')

def section_hdr(text, tooltip="", style=""):
    """Section header div with optional hover tooltip."""
    tt = tooltip or _SECTION_TIPS.get(text, "")
    sty = f' style="{style}"' if style else ""
    if tt:
        return (f'<div class="section-hdr"{sty}>'
                f'<span class="ttip">{text}<span class="ttip-box">{tt}</span></span></div>')
    return f'<div class="section-hdr"{sty}>{text}</div>'

def panel(html, height=345):
    return f'<div class="panel" style="height:{height}px;">{html}</div>'


# ── CSV export ────────────────────────────────────────────────────────────────
_EXPORT_COLS = [
    "mp_id","formula","crystal_system","space_group","bandgap","is_direct_gap",
    "cbm","vbm","total_magnetization","ordering","formation_energy_per_atom",
    "energy_above_hull","nsites","volume","density","k_voigt","g_voigt",
    "young_modulus","poisson_ratio","universal_anisotropy","e_total","e_ionic",
    "e_electronic","refractive_index","thermal_conductivity","debye_temperature",
    "nelements","chemsys",
]
def make_csv_bytes(row: dict) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_EXPORT_COLS)
    w.writerow([row.get(c, "") for c in _EXPORT_COLS])
    return buf.getvalue().encode()


# ── Radar chart ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_radar_norms() -> dict:
    COLS = {
        "bandgap":                   "bandgap > 0 AND bandgap < 15",
        "young_modulus":             "young_modulus > 0 AND young_modulus < 2000",
        "k_voigt":                   "k_voigt > 0 AND k_voigt < 1000",
        "density":                   "density > 0 AND density < 30",
        "refractive_index":          "refractive_index > 0 AND refractive_index < 10",
        "total_magnetization":       "total_magnetization > 0",
        "thermal_conductivity":      "thermal_conductivity > 0 AND thermal_conductivity < 500",
        "formation_energy_per_atom": "formation_energy_per_atom IS NOT NULL",
    }
    norms = {}
    with local_db.get_conn() as conn:
        for col, where in COLS.items():
            r = conn.execute(
                f"SELECT MIN({col}), MAX({col}) FROM materials "
                f"WHERE {col} IS NOT NULL AND {where}"
            ).fetchone()
            if r and r[0] is not None and r[1] is not None and r[1] > r[0]:
                norms[col] = (r[0], r[1])
    return norms

_RADAR_PROPS = [
    ("Band Gap",     "bandgap",                   False),
    ("Young's E",    "young_modulus",              False),
    ("Bulk K",       "k_voigt",                    False),
    ("Density",      "density",                    True),   # lower = better → invert
    ("Refr. Index",  "refractive_index",           False),
    ("Magnetization","total_magnetization",        False),
    ("Thermal κ",    "thermal_conductivity",       False),
    ("Stability",    "formation_energy_per_atom",  True),   # more negative = better → invert
]

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def build_radar_chart(row_a: dict, row_b: dict | None,
                      label_a: str, label_b: str,
                      accent_a: str, accent_b: str) -> go.Figure:
    norms = get_radar_norms()
    labels = [p[0] for p in _RADAR_PROPS]

    def _norm(val, col, invert):
        if val is None or col not in norms: return 0.0
        lo, hi = norms[col]
        n = (val - lo) / (hi - lo)
        return max(0.0, min(1.0, 1.0 - n if invert else n))

    def _vals(row):
        return [_norm(row.get(col), col, inv) for _, col, inv in _RADAR_PROPS]

    fig = go.Figure()
    va = _vals(row_a)
    fig.add_trace(go.Scatterpolar(
        r=va + [va[0]], theta=labels + [labels[0]],
        fill="toself", fillcolor=_hex_to_rgba(accent_a, 0.157),
        line=dict(color=accent_a, width=2), name=label_a,
        hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
    ))
    if row_b:
        vb = _vals(row_b)
        fig.add_trace(go.Scatterpolar(
            r=vb + [vb[0]], theta=labels + [labels[0]],
            fill="toself", fillcolor=_hex_to_rgba(accent_b, 0.157),
            line=dict(color=accent_b, width=2), name=label_b,
            hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
        ))
    fig.update_layout(
        polar=dict(
            bgcolor="#161b22",
            radialaxis=dict(visible=True, range=[0,1], showticklabels=False,
                            gridcolor="#30363d"),
            angularaxis=dict(gridcolor="#21262d",
                             tickfont=dict(size=9, color="#8b949e")),
        ),
        template="plotly_dark", paper_bgcolor="#0d1117",
        margin=dict(l=38, r=38, t=32, b=32), height=200,
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
                    font=dict(size=9), x=0.82, y=1.12),
        showlegend=True,
    )
    return fig


# ── Applications badges ───────────────────────────────────────────────────────
_APP_RULES = [
    # (label, color_hex, check_fn, tooltip)
    ("Solar cell", "#f9ca24",
     lambda r, el: (r.get("bandgap") is not None and 0.9 <= r["bandgap"] <= 1.8
                    and r.get("is_direct_gap") == 1),
     "Direct band gap 0.9–1.8 eV — matches the solar spectrum peak. Direct gap means photons are absorbed efficiently without a phonon assist. GaAs (1.42 eV) and CdTe (1.44 eV) are real-world examples."),
    ("Wide-gap LED", "#6c5ce7",
     lambda r, el: (r.get("bandgap") is not None and 2.5 <= r["bandgap"] <= 4.5
                    and r.get("is_direct_gap") == 1),
     "Direct band gap 2.5–4.5 eV — emission falls in the visible-to-UV range. GaN (3.4 eV) enables blue LEDs; AlGaN alloys cover UV. Direct gap is required for efficient electroluminescence."),
    ("Permanent magnet", "#e17055",
     lambda r, el: (r.get("ordering") in ("FM","FiM")
                    and r.get("total_magnetization") is not None
                    and r["total_magnetization"] > 5.0),
     "Ferromagnetic or ferrimagnetic with total magnetization > 5 μB/f.u. High magnetization + high coercivity = high energy product (B·H)max. Used in EV motors, MRI, wind turbines."),
    ("Thermal barrier", "#fd79a8",
     lambda r, el: (r.get("thermal_conductivity") is not None and r["thermal_conductivity"] < 5.0
                    and r.get("young_modulus") is not None and r["young_modulus"] > 100),
     "Low thermal conductivity (< 5 W/m·K) + stiff (E > 100 GPa). Thermal barrier coatings (TBCs) on turbine blades insulate metal from combustion heat. ZrO₂-based ceramics are the standard."),
    ("Superconductor hint", "#74b9ff",
     lambda r, el: (r.get("bandgap") == 0
                    and r.get("energy_above_hull") is not None
                    and r["energy_above_hull"] < 0.05),
     "Metal (zero band gap) that is thermodynamically stable (hull < 0.05 eV/atom). DFT can't predict Tc directly, but stability + metallic character are necessary conditions for superconductivity."),
    ("Optical coating", "#00cec9",
     lambda r, el: (r.get("refractive_index") is not None and 1.3 <= r["refractive_index"] <= 2.5),
     "Refractive index 1.3–2.5 — useful range for anti-reflection coatings, optical filters, and waveguides. Reflectivity at normal incidence = ((n−1)/(n+1))². MgF₂ (n=1.38) and TiO₂ (n=2.5) are common coating materials."),
    ("Aerospace structural", "#a29bfe",
     lambda r, el: (r.get("young_modulus") is not None and r.get("density") is not None
                    and r["density"] > 0 and (r["young_modulus"] / r["density"]) > 80),
     "Specific stiffness E/ρ > 80 GPa·cm³/g — lightweight yet stiff. Carbon fiber composites reach ~200; Al alloys ~26; steel ~26. High specific stiffness is critical for launch vehicle structures and satellite frames."),
    ("Thermoelectric hint", "#55efc4",
     lambda r, el: (r.get("bandgap") is not None and 0.1 < r["bandgap"] < 1.5
                    and r.get("thermal_conductivity") is not None
                    and r["thermal_conductivity"] < 3.0),
     "Narrow gap (0.1–1.5 eV) + low thermal conductivity (< 3 W/m·K). Good thermoelectrics need high Seebeck coefficient S (from narrow gap), high electrical conductivity, and low κ — competing demands often satisfied by heavy, complex structures like Bi₂Te₃."),
    ("Battery cathode hint", "#fdcb6e",
     lambda r, el: (bool(el) and any(e in {"Fe","Co","Ni","Mn","V","Ti","Cr","Mo"} for e in el)
                    and "O" in el
                    and r.get("bandgap") is not None and 0 < r["bandgap"] < 4),
     "Contains a redox-active transition metal (Fe/Co/Ni/Mn/V…) + oxygen + has a band gap (not metallic). Li-ion cathodes store charge by oxidizing/reducing the metal as Li⁺ intercalates. LiFePO₄ and LiCoO₂ are the commercial standards."),
    ("High dielectric", "#e84393",
     lambda r, el: (r.get("e_total") is not None and r["e_total"] > 20),
     "Total static dielectric constant ε > 20. High-k dielectrics store more charge per unit voltage — used in capacitors, DRAM, and gate oxides to replace SiO₂ and reduce leakage current at smaller node sizes."),
]

def build_applications(row: dict) -> str:
    if not row:
        return na("No property data")
    try:
        el = set(json.loads(row.get("elements") or "[]"))
    except Exception:
        el = set()

    found = []
    for label, color, check, tip_text in _APP_RULES:
        try:
            if check(row, el):
                found.append((label, color, tip_text))
        except Exception:
            pass

    if not found:
        return (f'<div style="font-size:0.72rem;color:#484f58;padding:4px 0;">'
                f'No strong application signal from current data — '
                f'more properties needed (run fetch.py to fill in mechanical/dielectric data).</div>')

    badges = "".join(
        f'<span class="app-badge ttip">'
        f'<span class="ab-dot" style="background:{c};"></span>{lbl}'
        f'<span class="ttip-box">{tt}</span></span>'
        for lbl, c, tt in found
    )
    return (f'<div style="padding:3px 0;">{badges}</div>'
            f'<div style="font-size:0.60rem;color:#484f58;margin-top:4px;">'
            f'Rule-based heuristics — not a substitute for expert evaluation</div>')


# ── Find Similar ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def find_similar(mp_id: str, top_n: int = 8) -> list[dict]:
    FEAT = ["bandgap","young_modulus","density",
            "total_magnetization","formation_energy_per_atom","refractive_index"]
    all_rows = local_db.get_all_for_similarity()
    # Per-column min/max
    ranges = {}
    for col in FEAT:
        vals = [r[col] for r in all_rows if r.get(col) is not None]
        if vals:
            lo, hi = min(vals), max(vals)
            ranges[col] = (lo, hi - lo if hi > lo else 1.0)

    def to_vec(row):
        v = []
        for col in FEAT:
            val = row.get(col)
            if val is None or col not in ranges:
                v.append(None)
            else:
                lo, rng = ranges[col]
                v.append((val - lo) / rng)
        return v

    query = next((r for r in all_rows if r["mp_id"] == mp_id), None)
    if not query:
        return []
    qv = to_vec(query)

    results = []
    for r in all_rows:
        if r["mp_id"] == mp_id:
            continue
        rv = to_vec(r)
        # Euclidean distance over shared non-None dimensions
        ss, n = 0.0, 0
        for a, b in zip(qv, rv):
            if a is not None and b is not None:
                ss += (a - b) ** 2
                n += 1
        if n >= 2:
            results.append({"mp_id": r["mp_id"], "formula": r["formula"],
                             "dist": (ss / n) ** 0.5})
    results.sort(key=lambda x: x["dist"])
    return results[:top_n]


# ── ML model (trained once per session) ──────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_ml_model():
    rows = local_db.get_ml_rows()
    return ml_mod.build_model(rows)


# ── DOS rendering ─────────────────────────────────────────────────────────────
def render_dos(mp_id: str, api_key: str):
    """Render DOS chart, fetching from MP API if not cached."""
    cached = local_db.get_dos(mp_id)
    if cached is None:
        if not api_key:
            st.caption("No API key — cannot fetch DOS.")
            return
        with st.spinner("Fetching density of states…"):
            try:
                from mp_api.client import MPRester
                from pymatgen.electronic_structure.core import Spin
                with MPRester(api_key) as mpr:
                    dos = mpr.get_dos_by_material_id(mp_id)
                if dos is None:
                    st.caption("DOS not available for this compound.")
                    local_db.save_dos(mp_id, {"unavailable": True})
                    return
                efermi = dos.efermi
                energies = [e - efermi for e in dos.energies]
                if Spin.down in dos.densities:
                    d_up   = dos.densities[Spin.up].tolist()
                    d_down = dos.densities[Spin.down].tolist()
                else:
                    d_up   = dos.get_densities().tolist()
                    d_down = None
                cached = {"energies": energies, "up": d_up, "down": d_down,
                          "efermi": 0.0}
                local_db.save_dos(mp_id, cached)
            except Exception as e:
                st.caption(f"DOS fetch error: {e}")
                return

    if cached.get("unavailable"):
        st.caption("DOS not available for this compound.")
        return

    energies = cached["energies"]
    d_up     = cached["up"]
    d_down   = cached.get("down")
    # Clip to ±5 eV window for readability
    lo, hi = -5.0, 5.0
    idxs = [i for i, e in enumerate(energies) if lo <= e <= hi]
    if not idxs:
        idxs = list(range(len(energies)))
    e_plot  = [energies[i] for i in idxs]
    up_plot = [d_up[i] for i in idxs]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=up_plot, y=e_plot, mode="lines",
        line=dict(color="#58a6ff", width=1.5),
        fill="tozerox", fillcolor="rgba(88,166,255,0.12)",
        name="Spin up" if d_down else "DOS",
    ))
    if d_down:
        dn_plot = [-d_down[i] for i in idxs]
        fig.add_trace(go.Scatter(
            x=dn_plot, y=e_plot, mode="lines",
            line=dict(color="#f85149", width=1.5),
            fill="tozerox", fillcolor="rgba(248,81,73,0.12)",
            name="Spin down",
        ))
    fig.add_hline(y=0, line=dict(color="#d29922", width=1, dash="dot"),
                  annotation_text="Eᶠ", annotation_font_size=9)
    fig.add_vline(x=0, line=dict(color="#30363d", width=1))
    fig.update_layout(
        xaxis_title="DOS (states/eV)", yaxis_title="E − Eᶠ (eV)",
        template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        margin=dict(l=50, r=10, t=8, b=40), height=220,
        xaxis=dict(gridcolor="#21262d", tickfont=dict(size=9)),
        yaxis=dict(gridcolor="#21262d", tickfont=dict(size=9), range=[lo, hi]),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
                    font=dict(size=9), x=0.78, y=0.98),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Density of states ± 5 eV around Fermi level  ·  source: Materials Project")


# ── Band structure rendering ──────────────────────────────────────────────────
def render_bandstructure(mp_id: str, api_key: str, accent: str):
    """Render band structure chart, fetching from MP API if not cached."""
    cached = local_db.get_bandstructure(mp_id)
    if cached is None:
        if not api_key:
            st.caption("No API key — cannot fetch band structure.")
            return
        with st.spinner("Fetching band structure…"):
            try:
                from mp_api.client import MPRester
                from pymatgen.electronic_structure.core import Spin
                with MPRester(api_key) as mpr:
                    bs = mpr.get_bandstructure_by_material_id(mp_id)
                if bs is None:
                    st.caption("Band structure not available for this compound.")
                    local_db.save_bandstructure(mp_id, {"unavailable": True})
                    return
                efermi = bs.efermi
                # Build distance array across all branches
                distances, bands_up, bands_down = [], [], []
                tick_pos, tick_lbl = [], []
                dist_offset = 0.0
                prev_end = None
                for branch in bs.branches:
                    si, ei = branch["start_index"], branch["end_index"]
                    kpts = bs.kpoints[si:ei+1]
                    # distances within branch
                    seg_d = [0.0]
                    for j in range(1, len(kpts)):
                        seg_d.append(seg_d[-1] + float(
                            sum((kpts[j].frac_coords[k]-kpts[j-1].frac_coords[k])**2
                                for k in range(3)) ** 0.5))
                    tick_lbl.append(branch.get("name","").split("-")[0] or "")
                    tick_pos.append(dist_offset)
                    for d in seg_d:
                        distances.append(dist_offset + d)
                    dist_offset = distances[-1]
                    prev_end = branch.get("name","")
                tick_lbl.append(prev_end.split("-")[-1] if prev_end else "")
                tick_pos.append(dist_offset)

                nb = bs.nb_bands
                # Collect only bands within ±3 eV of Fermi for compactness
                su = bs.bands[Spin.up]
                bands_up = []
                for bi in range(nb):
                    band = [float(su[bi][i]) - efermi
                            for i in range(len(distances))]
                    if min(band) <= 3.0 and max(band) >= -3.0:
                        bands_up.append(band)
                if Spin.down in bs.bands:
                    sd = bs.bands[Spin.down]
                    for bi in range(nb):
                        band = [float(sd[bi][i]) - efermi
                                for i in range(len(distances))]
                        if min(band) <= 3.0 and max(band) >= -3.0:
                            bands_down.append(band)
                cached = {
                    "distances": distances, "bands_up": bands_up,
                    "bands_down": bands_down if bands_down else None,
                    "tick_pos": tick_pos, "tick_lbl": tick_lbl,
                }
                local_db.save_bandstructure(mp_id, cached)
            except Exception as e:
                st.caption(f"Band structure fetch error: {e}")
                return

    if cached.get("unavailable"):
        st.caption("Band structure not available for this compound.")
        return

    distances  = cached["distances"]
    bands_up   = cached["bands_up"]
    bands_down = cached.get("bands_down") or []
    tick_pos   = cached["tick_pos"]
    tick_lbl   = cached["tick_lbl"]

    fig = go.Figure()
    for band in bands_up:
        fig.add_trace(go.Scatter(
            x=distances, y=band, mode="lines",
            line=dict(color=accent, width=1), showlegend=False,
            hovertemplate="E−Eᶠ=%{y:.3f} eV<extra></extra>",
        ))
    for band in bands_down:
        fig.add_trace(go.Scatter(
            x=distances, y=band, mode="lines",
            line=dict(color="#f85149", width=1, dash="dot"),
            showlegend=False,
        ))
    fig.add_hline(y=0, line=dict(color="#d29922", width=1, dash="dot"),
                  annotation_text="Eᶠ", annotation_font_size=9)
    for xp in tick_pos:
        fig.add_vline(x=xp, line=dict(color="#30363d", width=1))
    fig.update_layout(
        xaxis=dict(tickvals=tick_pos, ticktext=tick_lbl, gridcolor="#21262d",
                   tickfont=dict(size=10)),
        yaxis=dict(title="E − Eᶠ (eV)", range=[-3, 3], gridcolor="#21262d",
                   tickfont=dict(size=9), zeroline=True, zerolinecolor="#444"),
        template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        margin=dict(l=50, r=10, t=8, b=36), height=220,
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Band structure along high-symmetry path  ·  ±3 eV window  ·  source: Materials Project")


# ── Parallel coordinates ──────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_parcoords_data(cols: tuple, limit: int = 3000) -> list[dict]:
    safe = {
        "density","young_modulus","k_voigt","g_voigt","bandgap",
        "total_magnetization","formation_energy_per_atom","energy_above_hull",
        "e_total","refractive_index","poisson_ratio","debye_temperature",
        "thermal_conductivity","nsites","volume",
    }
    cols = [c for c in cols if c in safe]
    if len(cols) < 2:
        return []
    where = " AND ".join(f"{c} IS NOT NULL" for c in cols)
    q = f"SELECT mp_id, formula, {', '.join(cols)} FROM materials WHERE {where} LIMIT ?"
    with local_db.get_conn() as conn:
        conn.row_factory = __import__("sqlite3").Row
        rows = conn.execute(q, (limit,)).fetchall()
    return [dict(r) for r in rows]

def render_parallel_coords(accent: str):
    PC_PROPS = {
        "Density (g/cm³)":          "density",
        "Young's E (GPa)":          "young_modulus",
        "Bulk K (GPa)":             "k_voigt",
        "Band Gap (eV)":            "bandgap",
        "Magnetization (μB)":       "total_magnetization",
        "Formation E (eV/at)":      "formation_energy_per_atom",
        "Hull Energy (eV/at)":      "energy_above_hull",
        "Dielectric ε":             "e_total",
        "Refr. Index":              "refractive_index",
        "Debye Temp (K)":           "debye_temperature",
        "Thermal κ (W/m·K)":        "thermal_conductivity",
    }
    all_keys = list(PC_PROPS.keys())
    defaults = ["Density (g/cm³)", "Young's E (GPa)", "Band Gap (eV)",
                "Formation E (eV/at)", "Dielectric ε"]
    sel = st.multiselect("Axes", all_keys, default=defaults, key="pc_axes",
                         label_visibility="collapsed")
    if len(sel) < 2:
        st.caption("Select at least 2 axes.")
        return
    cols = tuple(PC_PROPS[s] for s in sel)
    rows = get_parcoords_data(cols)
    if not rows:
        st.caption("No compounds have all selected properties.")
        return

    n_axes = len(sel)
    # Compute per-axis min/max for normalisation
    ax_min = {}
    ax_max = {}
    for s, col in zip(sel, cols):
        vals = [r[col] for r in rows]
        lo, hi = min(vals), max(vals)
        ax_min[col] = lo
        ax_max[col] = hi if hi != lo else lo + 1.0

    # Band-gap colour scale (Viridis-like: blue → green → yellow)
    def _bg_color(bg_val: float) -> str:
        bg_max = ax_max.get("bandgap", 10) or 10
        t = max(0.0, min(1.0, (bg_val or 0) / bg_max))
        r = int(68 + t * (253 - 68))
        g = int(1  + t * (231 - 1))
        b = int(84 + t * (37  - 84))
        return f"rgb({r},{g},{b})"

    # Current compound mp_id for highlight
    cur_mp = st.session_state.get("mp_id", "")

    MAX_TRACES = 300
    display_rows = rows[:MAX_TRACES]

    fig = go.Figure()

    # Draw vertical axis lines and labels as shapes/annotations
    for i in range(n_axes):
        x_pos = i / (n_axes - 1) if n_axes > 1 else 0.5
        fig.add_shape(
            type="line", xref="paper", yref="paper",
            x0=x_pos, y0=0.06, x1=x_pos, y1=0.96,
            line=dict(color="#30363d", width=1.5),
        )
        # Tick labels: min at bottom, max at top
        col = cols[i]
        lo_v, hi_v = ax_min[col], ax_max[col]
        for val, y_frac, anchor in [(lo_v, 0.04, "top"), (hi_v, 0.98, "bottom")]:
            label = f"{val:.2g}"
            fig.add_annotation(
                xref="paper", yref="paper",
                x=x_pos, y=y_frac,
                text=label,
                showarrow=False,
                font=dict(size=8, color="#6e7681"),
                yanchor=anchor,
                xanchor="center",
            )
        # Axis name label above
        fig.add_annotation(
            xref="paper", yref="paper",
            x=x_pos, y=1.02,
            text=sel[i],
            showarrow=False,
            font=dict(size=9, color="#8b949e"),
            yanchor="bottom",
            xanchor="center",
        )

    # One Scatter trace per compound
    for row in display_rows:
        is_cur = row.get("mp_id") == cur_mp
        norm_vals = []
        for col in cols:
            v = row[col]
            norm_vals.append((v - ax_min[col]) / (ax_max[col] - ax_min[col]))

        x_pts = [i / (n_axes - 1) if n_axes > 1 else 0.5 for i in range(n_axes)]
        # Normalised y in [0.06, 0.96] paper coords → but scatter uses data coords.
        # Use paper y directly by setting yaxis range [0,1].
        y_pts = [0.06 + v * 0.90 for v in norm_vals]

        # Build tooltip
        tip_lines = [f"<b>{row.get('formula', row.get('mp_id',''))}</b>"]
        for s, col in zip(sel, cols):
            tip_lines.append(f"{s}: {row[col]:.3g}")
        tip = "<br>".join(tip_lines) + "<extra></extra>"

        bg_v = row.get("bandgap") or 0
        line_color = accent if is_cur else _bg_color(bg_v)
        line_w = 2.5 if is_cur else 0.8
        opacity = 1.0 if is_cur else 0.55

        fig.add_trace(go.Scatter(
            x=x_pts, y=y_pts,
            mode="lines",
            line=dict(color=line_color, width=line_w),
            opacity=opacity,
            hovertemplate=tip,
            name=row.get("formula", ""),
            showlegend=False,
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        margin=dict(l=20, r=20, t=40, b=20),
        height=300,
        xaxis=dict(visible=False, range=[-0.02, 1.02]),
        yaxis=dict(visible=False, range=[0, 1]),
        dragmode="zoom",
        hoverlabel=dict(
            bgcolor="#161b22", bordercolor="#30363d",
            font=dict(size=11, color="#e6edf3"),
        ),
    )
    st.plotly_chart(fig, config={"scrollZoom": True}, width="stretch")
    st.caption(
        f"{len(display_rows):,} of {len(rows):,} compounds shown · "
        "scroll to zoom · hover for compound details · "
        "color = band gap · current compound highlighted"
    )


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
        decomposes_to=[{"formula": str(d.formula), "amount": float(d.amount)}
                        for d in (getattr(doc,"decomposes_to",None) or [])
                        if hasattr(d, "formula")] or None,
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
    n_atoms = len(structure)
    def _r(dim, target=9.0):
        return max(1, min(4, int(target / dim + 0.5)))
    na, nb, nc = _r(a), _r(b), _r(c)
    # For large c (layered materials), boost to 2 layers if atom count stays manageable
    if nc == 1 and na * nb * 2 * n_atoms <= 250:
        nc = 2
    # Cap total atoms at ~300 to keep render fast
    while na * nb * nc * n_atoms > 300:
        if na >= nb and na >= nc and na > 1: na -= 1
        elif nb >= nc and nb > 1: nb -= 1
        elif nc > 1: nc -= 1
        else: break
    sup = structure * (na, nb, nc)
    cif = json.dumps(str(CifWriter(sup, symprec=None)))
    uid = f"v{abs(hash(structure.formula))%999999}"
    w_css = f"{w}px" if isinstance(w, int) else w   # e.g. "100%" or "430px"
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.4.2/3Dmol-min.js"></script>
<style>body{{margin:0;background:#0d1117;overflow:hidden}}
#{uid}{{width:{w_css};height:{h}px}}</style>
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
        h += sc("Anisotropy", f"{au:.3f}", alab,
                col="universal_anisotropy", raw=au)
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
    if e_ion:  h += sc("Ionic εᵢₒₙ", f"{e_ion:.2f}", "Phonon-driven",
                       col="e_ionic", raw=e_ion)
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
    if row.get("volume"):  h += sc("Cell Volume", f"{row['volume']:.2f} Å³",
                                    col="volume", raw=row["volume"])
    if row.get("nsites"):  h += sc("Sites", str(row["nsites"]), "Atoms per unit cell",
                                    col="nsites", raw=row["nsites"])
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
        if st.button("Save", type="primary", width='stretch'):
            local_db.save_note(mp_id, new_text)
            st.rerun()
    with cb:
        if existing and st.button("Clear", width='stretch'):
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
        clickmode="event+select",
        dragmode="select",
    )
    event = st.plotly_chart(fig, on_select="rerun", key="pos_chart", width="stretch")
    st.markdown(
        f'<div style="font-size:0.58rem;color:#8b949e;margin-top:-6px;">'
        f'★ = {db_row.get("formula","")} · {len(rows):,} compounds · click any point to navigate</div>',
        unsafe_allow_html=True)

    # ── Handle chart click → navigate ─────────────────────────────────────────
    if event and event.selection and event.selection.points:
        raw_cd = event.selection.points[0].get("customdata")
        # Plotly may wrap scalar customdata in a list; unwrap if needed
        clicked_mp = raw_cd[0] if isinstance(raw_cd, list) else raw_cd
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
        src = curated if curated else row
        if not src:
            return ""
        parts = []
        cs = src.get("crystal_system", "")
        sg = src.get("space_group", "")
        if cs:
            cs_tt = _CS_TIPS.get(cs.lower(), f"<b>{cs}</b> — one of the 7 crystal systems.")
            parts.append(f'<span class="ttip" style="color:{accent};font-weight:600;cursor:help;">'
                         f'{cs}<span class="ttip-box">{cs_tt}</span></span>')
        if sg:
            parts.append(f'<span class="ttip" style="color:#8b949e;cursor:help;">'
                         f'{sg}<span class="ttip-box">{_sg_tip(sg)}</span></span>')
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
            st.iframe("data:text/html;base64," + base64.b64encode(
                render_crystal(struct_a, accent_a, w=430, h=280).encode()).decode(),
                height=295)
            lat = struct_a.lattice
            st.markdown(f'<div style="font-size:0.62rem;color:#8b949e;">a={lat.a:.3f} b={lat.b:.3f} c={lat.c:.3f} Å · {struct_a.num_sites} sites</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div style="height:280px;display:flex;align-items:center;justify-content:center;'
                        'background:#161b22;border-radius:6px;color:#8b949e;">Structure unavailable</div>',
                        unsafe_allow_html=True)
        if curated_a:
            if st.button(f"Why {fa} works", key="why_a", width='stretch'):
                st.session_state["_why_text"]   = curated_a["why_it_works"]
                st.session_state["_why_accent"] = accent_a
                dlg_why()

    with v2:
        st.markdown(f'<div style="font-size:0.65rem;color:{accent_b};font-weight:600;margin-bottom:3px;">{fb}</div>',
                    unsafe_allow_html=True)
        if struct_b:
            st.iframe("data:text/html;base64," + base64.b64encode(
                render_crystal(struct_b, accent_b, w=430, h=280).encode()).decode(),
                height=295)
            lat = struct_b.lattice
            st.markdown(f'<div style="font-size:0.62rem;color:#8b949e;">a={lat.a:.3f} b={lat.b:.3f} c={lat.c:.3f} Å · {struct_b.num_sites} sites</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div style="height:280px;display:flex;align-items:center;justify-content:center;'
                        'background:#161b22;border-radius:6px;color:#8b949e;">Structure unavailable</div>',
                        unsafe_allow_html=True)
        if curated_b:
            if st.button(f"Why {fb} works", key="why_b", width='stretch'):
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

    # ── Mode buttons — always visible at the top ───────────────────────────
    _mc1, _mc2 = st.columns(2, gap="small")
    with _mc1:
        _ashby_lbl = "Ashby ✦" if st.session_state.ashby_mode else "Ashby Charts"
        if st.button(_ashby_lbl, key="ashby_top", use_container_width=True):
            st.session_state.ashby_mode   = not st.session_state.ashby_mode
            st.session_state.compare_mode = False
            st.session_state.browse_mode  = False
            st.rerun()
    with _mc2:
        _browse_lbl = "Browse ✦" if st.session_state.browse_mode else "Browse All"
        if st.button(_browse_lbl, key="browse_top", use_container_width=True):
            st.session_state.browse_mode  = not st.session_state.browse_mode
            st.session_state.ashby_mode   = False
            st.session_state.compare_mode = False
            st.session_state.browse_page  = 0
            st.rerun()

    # ── Fetch any MP compound ──────────────────────────────────────────────
    with st.expander("Fetch any compound", expanded=False):
        _fetch_in = st.text_input("MP ID", placeholder="e.g. mp-1234",
                                  label_visibility="collapsed", key="fetch_mp_input")
        if st.button("Go", key="fetch_mp_go") and _fetch_in.strip():
            _fid = _fetch_in.strip()
            st.session_state.mp_id        = _fid
            st.session_state.compound_name = _fid
            st.session_state.curated_data  = None
            st.session_state.ashby_mode    = False
            st.session_state.compare_mode  = False
            st.query_params["mp"] = _fid
            st.rerun()

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
                             width='stretch'):
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
                    chosen = st.selectbox(hdr, OPTIONS, index=default_idx,
                                         key=f"dd_{cat}",
                                         help=_CAT_TIPS.get(cat, ""))
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

    st.divider()
    db_info = local_db.stats()
    st.caption(
        f"**{db_info['total']:,}** compounds  \n"
        f"Elastic: {db_info['with_elasticity']}  ·  ε: {db_info['with_dielectric']}"
    )

    # ── My Collection ──────────────────────────────────────────────────────
    _cur_mp = st.session_state.mp_id
    _cur_formula = (st.session_state.curated_data["formula"]
                    if st.session_state.curated_data
                    else st.session_state.mp_id)
    with st.expander(
        f"My Collection  ({len(local_db.collection_get())})", expanded=False
    ):
        _in_col = local_db.collection_has(_cur_mp)
        _btn_lbl = "Remove from collection" if _in_col else "Add to collection"
        if st.button(_btn_lbl, key="col_toggle", width="stretch"):
            if _in_col:
                local_db.collection_remove(_cur_mp)
            else:
                local_db.collection_add(_cur_mp, _cur_formula)
            st.rerun()
        _col_items = local_db.collection_get()
        if _col_items:
            for _ci in _col_items:
                _is_cur = _ci["mp_id"] == _cur_mp
                _lbl = f"{'▶ ' if _is_cur else ''}{_ci['formula']}"
                if st.button(_lbl, key=f"col_nav_{_ci['mp_id']}", width="stretch"):
                    st.session_state.mp_id        = _ci["mp_id"]
                    st.session_state.compound_name = _ci["formula"]
                    st.session_state.curated_data  = None
                    st.query_params["mp"] = _ci["mp_id"]
                    st.rerun()
        else:
            st.caption("No compounds saved yet.")

    # ── Prev / Next ────────────────────────────────────────────────────────
    _all_curated = [(d["mp_id"], d["formula"])
                    for cat in COMPOUNDS.values()
                    for d in cat.values()]
    _cur_idx = next((i for i, (mid, _) in enumerate(_all_curated)
                     if mid == _cur_mp), None)
    if _cur_idx is not None:
        _pn1, _pn2 = st.columns(2, gap="small")
        with _pn1:
            if st.button("← Prev", key="nav_prev", width="stretch"):
                _pmid, _pf = _all_curated[(_cur_idx - 1) % len(_all_curated)]
                st.session_state.mp_id        = _pmid
                st.session_state.compound_name = _pf
                st.session_state.curated_data  = None
                for _cat2, _cmpds2 in COMPOUNDS.items():
                    for _n2, _d2 in _cmpds2.items():
                        if _d2["mp_id"] == _pmid:
                            st.session_state.curated_data = _d2; break
                st.query_params["mp"] = _pmid
                st.rerun()
        with _pn2:
            if st.button("Next →", key="nav_next", width="stretch"):
                _nmid, _nf = _all_curated[(_cur_idx + 1) % len(_all_curated)]
                st.session_state.mp_id        = _nmid
                st.session_state.compound_name = _nf
                st.session_state.curated_data  = None
                for _cat2, _cmpds2 in COMPOUNDS.items():
                    for _n2, _d2 in _cmpds2.items():
                        if _d2["mp_id"] == _nmid:
                            st.session_state.curated_data = _d2; break
                st.query_params["mp"] = _nmid
                st.rerun()


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

if st.session_state.browse_mode:
    _BROWSE_COLS = {
        "Formula":          "formula",
        "Crystal System":   "crystal_system",
        "Space Group":      "space_group",
        "Band Gap (eV)":    "bandgap",
        "Density (g/cm³)":  "density",
        "Young's E (GPa)":  "young_modulus",
        "Formation E":      "formation_energy_per_atom",
        "Hull E":           "energy_above_hull",
        "Ordering":         "ordering",
        "Dielectric ε":     "e_total",
    }
    PAGE_SIZE = 50

    # ── Controls row ──────────────────────────────────────────────────────────
    _bc1, _bc2, _bc3, _bc4 = st.columns([2, 2, 2, 1], gap="small")
    with _bc1:
        _bq = st.text_input("Filter formula / mp-id", placeholder="e.g. Ti, mp-149",
                            key="browse_q", label_visibility="collapsed")
    with _bc2:
        _cs_opts = ["All crystal systems"] + sorted([
            r[0] for r in local_db.get_conn().execute(
                "SELECT DISTINCT crystal_system FROM materials "
                "WHERE crystal_system IS NOT NULL ORDER BY crystal_system"
            ).fetchall()
        ])
        _bcs = st.selectbox("Crystal system", _cs_opts, key="browse_cs",
                            label_visibility="collapsed")
    with _bc3:
        _sort_col = st.selectbox("Sort by", list(_BROWSE_COLS.keys()),
                                 index=3, key="browse_sort",
                                 label_visibility="collapsed")
    with _bc4:
        _sort_asc = st.checkbox("↑ Asc", value=True, key="browse_asc")

    # ── Query ─────────────────────────────────────────────────────────────────
    @st.cache_data(show_spinner=False)
    def _browse_query(q, cs, sort_db_col, asc, page):
        wheres = []
        params = []
        if q:
            wheres.append("(formula LIKE ? OR mp_id LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if cs and cs != "All crystal systems":
            wheres.append("crystal_system = ?")
            params.append(cs)
        where_sql = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        order = "ASC" if asc else "DESC"
        null_last = f"{sort_db_col} IS NULL, {sort_db_col} {order}"
        offset = page * PAGE_SIZE
        cols = ", ".join(["mp_id", "formula", "crystal_system", "space_group",
                          "bandgap", "density", "young_modulus",
                          "formation_energy_per_atom", "energy_above_hull",
                          "ordering", "e_total"])
        with local_db.get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            total = conn.execute(
                f"SELECT COUNT(*) FROM materials {where_sql}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT {cols} FROM materials {where_sql} "
                f"ORDER BY {null_last} LIMIT {PAGE_SIZE} OFFSET {offset}",
                params
            ).fetchall()
        return [dict(r) for r in rows], total

    _db_sort = _BROWSE_COLS[_sort_col]
    _filter_sig = (_bq, _bcs, _db_sort, _sort_asc)
    if st.session_state.get("_browse_last_filter") != _filter_sig:
        st.session_state.browse_page = 0
        st.session_state["_browse_last_filter"] = _filter_sig
    _rows, _total = _browse_query(_bq, _bcs if _bcs != "All crystal systems" else "",
                                  _db_sort, _sort_asc, st.session_state.browse_page)
    _n_pages = max(1, (_total + PAGE_SIZE - 1) // PAGE_SIZE)

    st.caption(f"**{_total:,}** compounds match · page "
               f"{st.session_state.browse_page + 1} of {_n_pages} · "
               f"click a row to navigate · sort by {_sort_col}")

    # ── Table ─────────────────────────────────────────────────────────────────
    import pandas as pd

    def _fmt(v, decimals=3):
        if v is None: return ""
        return f"{v:.{decimals}f}"

    _tbl_data = []
    for r in _rows:
        _tbl_data.append({
            "▶": "▶" if r["mp_id"] == st.session_state.mp_id else "",
            "mp-id":          r["mp_id"],
            "Formula":        r["formula"] or "",
            "System":         r["crystal_system"] or "",
            "SG":             r["space_group"] or "",
            "Gap (eV)":       _fmt(r["bandgap"]),
            "ρ (g/cm³)":      _fmt(r["density"]),
            "E (GPa)":        _fmt(r["young_modulus"], 0) if r["young_modulus"] else "",
            "Fmn E":          _fmt(r["formation_energy_per_atom"]),
            "Hull E":         _fmt(r["energy_above_hull"]),
            "Order":          r["ordering"] or "",
            "ε":              _fmt(r["e_total"], 1) if r["e_total"] else "",
        })
    _df = pd.DataFrame(_tbl_data)

    _sel = st.dataframe(
        _df, hide_index=True, use_container_width=True,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "▶":       st.column_config.TextColumn("", width=20),
            "mp-id":   st.column_config.TextColumn("mp-id",   width=90),
            "Formula": st.column_config.TextColumn("Formula", width=110),
            "System":  st.column_config.TextColumn("System",  width=90),
            "SG":      st.column_config.TextColumn("SG",      width=75),
            "Gap (eV)":st.column_config.TextColumn("Gap(eV)", width=65),
            "ρ (g/cm³)":st.column_config.TextColumn("ρ",      width=60),
            "E (GPa)": st.column_config.TextColumn("E(GPa)",  width=60),
            "Fmn E":   st.column_config.TextColumn("Fmn E",   width=60),
            "Hull E":  st.column_config.TextColumn("Hull E",  width=60),
            "Order":   st.column_config.TextColumn("Order",   width=50),
            "ε":       st.column_config.TextColumn("ε",       width=50),
        },
        key="browse_tbl",
    )
    if _sel and _sel.selection and _sel.selection.rows:
        _row_idx = _sel.selection.rows[0]
        _clicked = _rows[_row_idx]
        if _clicked["mp_id"] != st.session_state.mp_id:
            st.session_state.mp_id        = _clicked["mp_id"]
            st.session_state.compound_name = _clicked["formula"]
            st.session_state.curated_data  = None
            st.session_state.browse_mode   = True   # stay in browse mode
            st.query_params["mp"] = _clicked["mp_id"]
            st.rerun()

    # ── Pagination ────────────────────────────────────────────────────────────
    _pg1, _pg2, _pg3 = st.columns([1, 3, 1], gap="small")
    with _pg1:
        if st.button("← Prev", disabled=st.session_state.browse_page == 0,
                     key="browse_prev", width="stretch"):
            st.session_state.browse_page -= 1
            st.rerun()
    with _pg2:
        _jump = st.number_input("Page", min_value=1, max_value=_n_pages,
                                value=st.session_state.browse_page + 1,
                                key="browse_jump", label_visibility="collapsed")
        if _jump - 1 != st.session_state.browse_page:
            st.session_state.browse_page = _jump - 1
            st.rerun()
    with _pg3:
        if st.button("Next →", disabled=st.session_state.browse_page >= _n_pages - 1,
                     key="browse_next", width="stretch"):
            st.session_state.browse_page += 1
            st.rerun()

    st.stop()

elif st.session_state.ashby_mode:
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
    if db_row.get("crystal_system"):
        cs = db_row["crystal_system"]
        badges += badge(cs, tooltip=_CS_TIPS.get(cs.lower(),
            f"<b>{cs}</b> — one of the 7 crystal systems classifying all periodic structures by symmetry."))
    if db_row.get("space_group"):
        sg = db_row["space_group"]
        badges += badge(sg, tooltip=_sg_tip(sg))
    theoretical = db_row.get("theoretical")
    if theoretical == 0:
        badges += badge("Experimentally observed", "green",
                        tooltip=_BADGE_TIPS["Experimentally observed"])
    elif theoretical == 1:
        badges += badge("Computational only", "orange",
                        tooltip=_BADGE_TIPS["Computational only"])
    hull = db_row.get("energy_above_hull")
    if hull is not None:
        if hull < 0.001:
            badges += badge("Stable", "green", tooltip=_BADGE_TIPS["Stable"])
        elif hull < 0.025:
            badges += badge(f"Metastable +{hull:.3f}", "orange",
                            tooltip="Energy above the convex hull is between 0 and 0.025 eV/atom — thermodynamically unstable but often synthesizable. Many functional materials are metastable.")
        else:
            badges += badge(f"Unstable +{hull:.3f}", "red",
                            tooltip=f"Energy {hull:.3f} eV/atom above the convex hull — competing phases are significantly more stable. Difficult or impossible to synthesize at ambient conditions.")
badges += badge(selected_mp_id, "blue",
                tooltip="Materials Project ID — a unique identifier for this compound in the Materials Project database (materialsproject.org). Hover any property for details.")

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
        st.iframe("data:text/html;base64," + base64.b64encode(
            render_crystal(structure, accent, w="100%", h=VIEWER_H).encode()).decode(),
            height=VIEWER_H + 16)
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

    # ── Note + Download buttons — one compact row ─────────────────────────
    existing_note = local_db.get_note(selected_mp_id)
    note_label = f"✎ Note ({len(existing_note)}c)" if existing_note else "✎ Note"
    _nb, _cb, _fb = st.columns(3, gap="small")
    with _nb:
        st.markdown('<div class="action-row">', unsafe_allow_html=True)
        if st.button(note_label, key="note_btn", use_container_width=True):
            st.session_state["_note_mp_id"]   = selected_mp_id
            st.session_state["_note_formula"] = formula_display
            note_dialog()
        st.markdown('</div>', unsafe_allow_html=True)
    with _cb:
        st.markdown('<div class="action-row">', unsafe_allow_html=True)
        if db_row:
            st.download_button("⬇ CSV", data=make_csv_bytes(db_row),
                               file_name=f"{selected_mp_id}.csv",
                               mime="text/csv", key="csv_dl",
                               use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with _fb:
        st.markdown('<div class="action-row">', unsafe_allow_html=True)
        if structure:
            _cif_str = str(CifWriter(structure, symprec=0.1))
            st.download_button("⬇ CIF", data=_cif_str.encode(),
                               file_name=f"{selected_mp_id}.cif",
                               mime="chemical/x-cif", key="cif_dl",
                               use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Find Similar ──────────────────────────────────────────────────────
    with st.expander("Find similar compounds", expanded=False):
        _sim = find_similar(selected_mp_id)
        if _sim:
            for _s in _sim:
                _sc1, _sc2 = st.columns([3, 1], gap="small")
                with _sc1:
                    if st.button(_s["formula"], key=f"sim_{_s['mp_id']}",
                                 width="stretch"):
                        st.session_state.mp_id        = _s["mp_id"]
                        st.session_state.compound_name = _s["formula"]
                        st.session_state.curated_data  = None
                        st.query_params["mp"] = _s["mp_id"]
                        st.rerun()
                with _sc2:
                    st.markdown(
                        f'<div class="sim-dist" style="padding-top:4px;">'
                        f'd={_s["dist"]:.2f}</div>',
                        unsafe_allow_html=True)
        else:
            st.caption("Not enough property data to compute similarity.")

    # Position in property space (compact)
    if db_row:
        st.markdown(
            '<div style="font-size:0.6rem;color:#8b949e;text-transform:uppercase;'
            'letter-spacing:.09em;font-weight:700;margin:6px 0 2px;">Position in property space</div>',
            unsafe_allow_html=True)
        try:
            render_position_chart(db_row, accent, chart_h=170)
        except Exception as _e:
            st.caption(f"Chart error: {_e}")

# ── RIGHT: property panels (grid layout) ──────────────────────────────────────
with right_col:
    # Row 1: Electronic & Magnetic | Mechanical & Thermal
    r1c1, r1c2 = st.columns(2, gap="medium")
    with r1c1:
        st.markdown(section_hdr("Electronic & Magnetic"), unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_electronic(db_row)}</div>',
                    unsafe_allow_html=True)
    with r1c2:
        st.markdown(section_hdr("Mechanical & Thermal"), unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_mechanical(db_row)}</div>',
                    unsafe_allow_html=True)

    # Row 2: Dielectric & Optical | Stability & Physical
    r2c1, r2c2 = st.columns(2, gap="medium")
    with r2c1:
        st.markdown(section_hdr("Dielectric & Optical"), unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_dielectric(db_row)}</div>',
                    unsafe_allow_html=True)
    with r2c2:
        st.markdown(section_hdr("Stability & Physical"), unsafe_allow_html=True)
        st.markdown(f'<div class="sc-grid">{build_stability(db_row, pc_data)}</div>',
                    unsafe_allow_html=True)

    # ── Applications + Radar (side by side) ──────────────────────────────
    _app_col, _rad_col = st.columns([1, 1], gap="medium")
    with _app_col:
        st.markdown(section_hdr("Applications"), unsafe_allow_html=True)
        st.markdown(build_applications(db_row), unsafe_allow_html=True)
    with _rad_col:
        st.markdown(section_hdr("Property Radar"), unsafe_allow_html=True)
        if db_row:
            _pinned_row = (local_db.get_material_row(st.session_state.compare_mp_id)
                           if st.session_state.compare_mp_id else None)
            _pinned_lbl = st.session_state.compare_name or ""
            _pinned_acc = (st.session_state.compare_curated["accent"]
                           if st.session_state.compare_curated else "#f9ca24")
            st.plotly_chart(
                build_radar_chart(db_row, _pinned_row, formula_display,
                                  _pinned_lbl, accent, _pinned_acc),
                width="stretch")
            _rad_note = "Normalized 0–1  ·  Density & Stability inverted"
            if _pinned_row:
                _rad_note += f"  ·  vs {_pinned_lbl}"
            st.caption(_rad_note)

    # ── ML Bandgap Prediction ─────────────────────────────────────────────
    _ml_bundle = get_ml_model()
    if _ml_bundle and db_row:
        _pred = ml_mod.predict_bandgap(_ml_bundle, db_row)
        _actual = db_row.get("bandgap")
        st.markdown(section_hdr("ML Bandgap Prediction", style="margin-top:10px;"),
                    unsafe_allow_html=True)
        _mc1, _mc2 = st.columns(2, gap="medium")
        with _mc1:
            st.markdown(
                f'<div class="pred-card">'
                f'<div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;'
                f'letter-spacing:.06em;margin-bottom:3px;">Predicted</div>'
                f'<div class="pred-val">{_pred:.3f} eV</div>'
                f'<div class="pred-sub">GradientBoosting · '
                f'MAE {_ml_bundle["mae"]:.3f} eV · {_ml_bundle["n_train"]:,} training pts</div>'
                f'</div>',
                unsafe_allow_html=True)
        with _mc2:
            if _actual is not None:
                _err = abs(_pred - _actual)
                _err_col = "#3fb950" if _err < 0.3 else "#d29922" if _err < 0.8 else "#f85149"
                st.markdown(
                    f'<div class="pred-card">'
                    f'<div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;'
                    f'letter-spacing:.06em;margin-bottom:3px;">Actual (DFT)</div>'
                    f'<div class="pred-val" style="color:#e6edf3;">{_actual:.3f} eV</div>'
                    f'<div class="pred-sub" style="color:{_err_col};">'
                    f'Error: {_err:.3f} eV</div>'
                    f'</div>',
                    unsafe_allow_html=True)
        # Feature importances mini bar
        _imps = sorted(_ml_bundle["importances"].items(), key=lambda x: -x[1])
        _imp_html = "".join(
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">'
            f'<div style="font-size:0.58rem;color:#8b949e;width:140px;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{lbl}</div>'
            f'<div style="background:#21262d;border-radius:2px;height:5px;flex:1;">'
            f'<div style="background:#58a6ff;width:{imp*100:.0f}%;height:100%;border-radius:2px;"></div>'
            f'</div><div style="font-size:0.58rem;color:#484f58;width:30px;text-align:right;">'
            f'{imp*100:.0f}%</div></div>'
            for lbl, imp in _imps
        )
        with st.expander("Feature importances", expanded=False):
            st.markdown(_imp_html, unsafe_allow_html=True)

    # XRD Pattern (full width)
    st.markdown(section_hdr("XRD Pattern (Cu Kα)", style="margin-top:12px;"),
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
            st.markdown(section_hdr("About", style="margin-top:12px;"),
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
                    st.image(wiki["thumbnail"]["source"], width='stretch')

    # ── Electronic Structure (DOS + Band Structure) ────────────────────────
    st.markdown(section_hdr("Electronic Structure", style="margin-top:12px;"),
                unsafe_allow_html=True)
    _es1, _es2 = st.columns(2, gap="medium")
    with _es1:
        st.markdown('<div style="font-size:0.62rem;color:#8b949e;margin-bottom:4px;">'
                    'Density of States</div>', unsafe_allow_html=True)
        if st.button("Load DOS", key="load_dos"):
            st.session_state["_load_dos"] = True
        if st.session_state.get("_load_dos") or local_db.get_dos(selected_mp_id):
            st.session_state["_load_dos"] = True
            render_dos(selected_mp_id, api_key)
        else:
            st.caption("Click 'Load DOS' to fetch from Materials Project (requires API key).")
    with _es2:
        st.markdown('<div style="font-size:0.62rem;color:#8b949e;margin-bottom:4px;">'
                    'Band Structure</div>', unsafe_allow_html=True)
        if st.button("Load Band Structure", key="load_bs"):
            st.session_state["_load_bs"] = True
        if st.session_state.get("_load_bs") or local_db.get_bandstructure(selected_mp_id):
            st.session_state["_load_bs"] = True
            render_bandstructure(selected_mp_id, api_key, accent)
        else:
            st.caption("Click 'Load Band Structure' to fetch from Materials Project (requires API key).")

    # ── Parallel Coordinates ───────────────────────────────────────────────
    st.markdown(section_hdr("Parallel Coordinates Explorer", style="margin-top:12px;"),
                unsafe_allow_html=True)
    with st.expander("Open parallel coordinates chart", expanded=False):
        st.caption("Select axes below — brush any axis range to filter compounds.")
        render_parallel_coords(accent)
