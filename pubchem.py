# pubchem.py
# Cross-reference compounds against PubChem for experimental chemical data.
#
# Materials Project gives us computed crystal physics (bandgap, magnetism, stability).
# PubChem gives us experimentally measured chemical properties:
# melting/boiling/flash points, CAS numbers, safety data, molecular identifiers.
#
# Note: PubChem covers well-known molecular/ionic compounds. Many materials in MP
# are theoretical (never synthesized) or complex enough that PubChem has no entry.
# The lookup is best-effort — we show data when found, gracefully skip when not.

import re
import requests

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
TIMEOUT = 8  # seconds — don't block the UI if PubChem is slow

# Properties to request in one call
_PROPS = ",".join([
    "MolecularWeight",
    "MeltingPoint",
    "BoilingPoint",
    "FlashPoint",
    "IUPACName",
    "InChI",
    "InChIKey",
    "CanonicalSMILES",
    "MolecularFormula",
])


def _fetch_props(endpoint: str) -> dict | None:
    """Raw fetch from PubChem property API."""
    url = f"{PUBCHEM_BASE}/{endpoint}/property/{_PROPS}/JSON"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        props = r.json().get("PropertyTable", {}).get("Properties", [])
        return props[0] if props else None
    except Exception:
        return None


def _get_cas(cid: int) -> str | None:
    """Extract CAS registry number from PubChem synonyms."""
    try:
        r = requests.get(f"{PUBCHEM_BASE}/cid/{cid}/synonyms/JSON", timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        synonyms = (
            r.json()
            .get("InformationList", {})
            .get("Information", [{}])[0]
            .get("Synonym", [])
        )
        for s in synonyms:
            if re.match(r"^\d{2,7}-\d{2}-\d$", s):
                return s
    except Exception:
        pass
    return None


def lookup(formula: str, name: str | None = None) -> dict | None:
    """
    Look up a compound in PubChem.
    Tries formula first, then common name if provided.
    Returns a flat dict of available properties, or None.
    """
    data = _fetch_props(f"formula/{formula}")

    if data is None and name:
        # Strip subscripts/superscripts from display name for the search
        clean_name = re.sub(r"[₀-₉⁰-⁹\u2080-\u2089]", "", name).strip()
        clean_name = requests.utils.quote(clean_name)
        data = _fetch_props(f"name/{clean_name}")

    if data is None:
        return None

    cid = data.get("CID")
    if cid:
        data["PubChemCID"] = cid
        cas = _get_cas(cid)
        if cas:
            data["CASNumber"] = cas

    return data


def format_prop(data: dict, key: str, unit: str = "") -> str | None:
    """Return a formatted property string, or None if missing."""
    val = data.get(key)
    if val is None or val == "":
        return None
    return f"{val} {unit}".strip()
