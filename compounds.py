# compounds.py
# Catalog of compounds with Materials Project IDs, key properties,
# and plain-English explanations connecting crystal structure to behavior.

COMPOUNDS = {
    "Strong Magnets": {
        "Nd₂Fe₁₄B  (Neodymium Magnet)": {
            "mp_id": "mp-5182",
            "formula": "Nd₂Fe₁₄B",
            "crystal_system": "Tetragonal",
            "space_group": "P4₂/mnm",
            "key_props": {
                "Magnetic energy product": "~400 kJ/m³  (strongest known)",
                "Curie temperature": "585 K",
                "Crystal structure": "Tetragonal — 68 atoms/unit cell",
            },
            "why_it_works": (
                "The tetragonal crystal structure is everything here. Iron's 3d electrons "
                "carry the magnetic moment, but on their own they'd point in random "
                "directions and cancel out. The tetragonal geometry — combined with "
                "neodymium's 4f electrons — creates a powerful 'crystal field' that forces "
                "all those moments to align along one axis (the c-axis). This is called "
                "**magnetocrystalline anisotropy**. The result: 68 atoms per unit cell, "
                "all pulling in the same direction, multiplied across trillions of unit cells."
            ),
            "accent": "#e17055",
            "wiki_search": "Neodymium magnet",
        },
        "Fe  (Iron)": {
            "mp_id": "mp-13",
            "formula": "Fe",
            "crystal_system": "Cubic (BCC)",
            "space_group": "Im-3m",
            "key_props": {
                "Saturation magnetization": "2.2 μB/atom",
                "Curie temperature": "1043 K",
                "Crystal structure": "Body-centered cubic",
            },
            "why_it_works": (
                "Iron's body-centered cubic (BCC) structure places each atom at the "
                "center of a cube with 8 neighbors at the corners. This geometry "
                "maximizes orbital overlap between neighboring Fe 3d electrons, "
                "creating a strong **exchange interaction** that locks electron spins "
                "into parallel alignment. Below 1043 K (the Curie temperature), this "
                "spontaneous alignment creates magnetic domains — the origin of all "
                "ferromagnetism."
            ),
            "accent": "#b2bec3",
            "wiki_search": "Iron",
        },
        "SmCo₅  (Samarium Cobalt)": {
            "mp_id": "mp-1429",
            "formula": "SmCo₅",
            "crystal_system": "Hexagonal",
            "space_group": "P6/mmm",
            "key_props": {
                "Coercivity": "up to 3 T (resists demagnetization)",
                "Max operating temp": "~300 °C (vs ~80 °C for NdFeB)",
                "Crystal structure": "Hexagonal layered",
            },
            "why_it_works": (
                "Samarium cobalt has a hexagonal layered structure: alternating planes "
                "of Sm and Co. The hexagonal symmetry has a single preferred magnetic "
                "axis (the c-axis), and Sm's 4f electrons create an even stronger "
                "crystal field than Nd in NdFeB. The tradeoff: it's harder to magnetize "
                "(high coercivity = resists being demagnetized), making it ideal for "
                "motors and sensors that operate at high temperatures."
            ),
            "accent": "#fdcb6e",
            "wiki_search": "Samarium–cobalt magnet",
        },
    },

    "Perovskites (Solar & Ferroelectric)": {
        "BaTiO₃  (Barium Titanate)": {
            "mp_id": "mp-2998",
            "formula": "BaTiO₃",
            "crystal_system": "Tetragonal",
            "space_group": "P4mm",
            "key_props": {
                "Bandgap": "3.2 eV",
                "Behavior": "Ferroelectric below 120 °C",
                "ABX₃ roles": "A=Ba, B=Ti, X=O",
            },
            "why_it_works": (
                "Classic ABX₃ perovskite. Ba²⁺ (the A-site) sits at cube corners, "
                "O²⁻ (X) on face centers forming an octahedron, and Ti⁴⁺ (B) "
                "sits inside that octahedron. The Ti ion is small enough to shift "
                "off-center within its oxygen cage — creating an electric dipole. "
                "When all Ti atoms shift the same direction, you get a macroscopic "
                "**spontaneous electric polarization**: ferroelectricity. The ABX₃ "
                "cage is what enables this off-centering."
            ),
            "accent": "#00cec9",
            "wiki_search": "Barium titanate",
        },
        "SrTiO₃  (Strontium Titanate)": {
            "mp_id": "mp-5229",
            "formula": "SrTiO₃",
            "crystal_system": "Cubic",
            "space_group": "Pm-3m",
            "key_props": {
                "Bandgap": "3.2 eV",
                "Tolerance factor": "~1.00 (nearly perfect cubic)",
                "Role": "Reference perovskite, substrate for thin films",
            },
            "why_it_works": (
                "SrTiO₃ is the 'hydrogen atom' of perovskites — the textbook perfect "
                "cubic case. The **Goldschmidt tolerance factor** (t = (rA+rX) / √2(rB+rX)) "
                "is almost exactly 1, meaning Sr, Ti, and O radii fit the cage geometry "
                "perfectly. TiO₆ octahedra are regular and don't tilt. This makes it "
                "the ideal substrate for growing other perovskite films — the lattice "
                "parameters match, minimizing strain."
            ),
            "accent": "#74b9ff",
            "wiki_search": "Strontium titanate",
        },
        "CsPbBr₃  (Cesium Lead Bromide)": {
            "mp_id": "mp-567629",
            "formula": "CsPbBr₃",
            "crystal_system": "Orthorhombic",
            "space_group": "Pbnm",
            "key_props": {
                "Bandgap": "~2.3 eV (direct)",
                "Quantum yield": ">90% photoluminescence",
                "Role": "LED emitters, solar, detectors",
            },
            "why_it_works": (
                "Halide perovskite: replace O with Br (or I, Cl). Pb²⁺ forms PbBr₆ "
                "octahedra that corner-share in 3D. The key physics: this structure "
                "is **defect-tolerant**. In silicon, a missing atom creates a "
                "mid-gap trap that kills efficiency. In CsPbBr₃, vacancies create "
                "shallow states near the band edges — carriers flow around them. "
                "Combined with a direct bandgap, this makes halide perovskites "
                "exceptional for both solar cells and LEDs despite being easy to "
                "grow from solution at room temperature."
            ),
            "accent": "#f9ca24",
            "wiki_search": "Caesium lead bromide",
        },
    },

    "Semiconductors": {
        "Si  (Silicon)": {
            "mp_id": "mp-149",
            "formula": "Si",
            "crystal_system": "Cubic (diamond)",
            "space_group": "Fd-3m",
            "key_props": {
                "Bandgap": "1.1 eV (indirect)",
                "Abundance": "Second most abundant element in Earth's crust",
                "Role": "Transistors, solar cells, all of modern electronics",
            },
            "why_it_works": (
                "Diamond cubic structure: each Si forms 4 covalent bonds in a "
                "tetrahedral arrangement (sp³ hybridization). The 1.1 eV **indirect "
                "bandgap** means the conduction band minimum and valence band maximum "
                "are at different crystal momenta — an electron needs both a photon "
                "and a phonon (lattice vibration) to make the jump. This makes Si "
                "inefficient for light emission, but ideal for transistors where you "
                "want precise electrical switching, not light output."
            ),
            "accent": "#a8d8ea",
            "wiki_search": "Silicon",
        },
        "GaAs  (Gallium Arsenide)": {
            "mp_id": "mp-2534",
            "formula": "GaAs",
            "crystal_system": "Cubic (zinc blende)",
            "space_group": "F-43m",
            "key_props": {
                "Bandgap": "1.42 eV (direct)",
                "Electron mobility": "6× higher than Si",
                "Role": "High-efficiency solar, LEDs, high-speed electronics",
            },
            "why_it_works": (
                "Zinc blende structure — like diamond cubic but alternating Ga and As "
                "atoms. The **direct bandgap** (conduction and valence band extrema "
                "at the same crystal momentum) means an electron can emit or absorb "
                "a photon directly, no phonon needed. The 1.42 eV gap is nearly "
                "perfect for the solar spectrum. Used in the highest-efficiency "
                "solar cells ever made (multi-junction cells for space applications, "
                ">47% efficiency)."
            ),
            "accent": "#fd79a8",
            "wiki_search": "Gallium arsenide",
        },
        "TiO₂  (Rutile)": {
            "mp_id": "mp-2657",
            "formula": "TiO₂",
            "crystal_system": "Tetragonal",
            "space_group": "P4₂/mnm",
            "key_props": {
                "Bandgap": "3.0 eV (absorbs UV)",
                "Role": "Photocatalysis, dye-sensitized solar cells (DSSCs)",
                "Fun fact": "The white pigment in most paint and sunscreen",
            },
            "why_it_works": (
                "Rutile structure: Ti in octahedral coordination with 6 oxygen neighbors. "
                "The wide 3.0 eV bandgap absorbs UV photons, generating electron-hole "
                "pairs that migrate to the surface and drive chemical reactions. In "
                "Grätzel cells (dye-sensitized solar), TiO₂ nanoparticles serve as "
                "an electron highway — dye molecules absorb visible light and inject "
                "electrons into TiO₂'s conduction band. The high surface area of "
                "nanoparticles maximizes the dye-TiO₂ interface."
            ),
            "accent": "#a29bfe",
            "wiki_search": "Titanium dioxide",
        },
    },

    "Space Elevator Candidates": {
        "Diamond  (C)": {
            "mp_id": "mp-66",
            "formula": "C (Diamond)",
            "crystal_system": "Cubic (diamond)",
            "space_group": "Fd-3m",
            "key_props": {
                "Young's modulus": "~1,050 GPa — stiffest known bulk material",
                "Density": "3.51 g/cm³",
                "Specific modulus E/ρ": "~300 GPa·cm³/g",
                "Vickers hardness": "~100 GPa",
            },
            "why_it_works": (
                "Diamond's cubic carbon lattice — every atom tetrahedrally bonded to four "
                "neighbors — is the densest packing of the strongest bond in nature (C–C, 347 kJ/mol). "
                "The result is the highest Young's modulus of any bulk material: ~1,050 GPa. "
                "For a space elevator, the metric is <b>specific modulus</b> (E/ρ): the stiffness "
                "you get per gram of material. Diamond's ~300 GPa·cm³/g dwarfs steel (~26). "
                "The catch: bulk diamond is expensive and brittle. The real hope is carbon nanotubes "
                "(same bonding, rolled into a cylinder) with theoretical specific tensile strength "
                "47,000 kN·m/kg — roughly 50× what any current cable can achieve."
            ),
            "accent": "#b9f2ff",
            "wiki_search": "Diamond",
        },
        "h-BN  (Hexagonal Boron Nitride)": {
            "mp_id": "mp-13150",
            "formula": "BN",
            "crystal_system": "Hexagonal",
            "space_group": "P6₃/mmc",
            "key_props": {
                "In-plane Young's modulus": "~865 GPa",
                "Density": "2.28 g/cm³  (lighter than diamond)",
                "Bandgap": "~6 eV  (electrical insulator)",
                "Max operating temp": ">900 °C in air (oxidation resistant)",
            },
            "why_it_works": (
                "Hexagonal BN is isostructural with graphite — alternating B and N atoms in "
                "honeycomb layers held together by van der Waals forces. The B–N bond (bond energy "
                "~400 kJ/mol) is slightly stronger than graphite's C–C in-plane, and BN is "
                "chemically inert up to ~900 °C in air where graphite would oxidize. "
                "This makes h-BN nanotubes a serious space elevator candidate: nearly the same "
                "specific strength as carbon nanotubes, but electrically insulating and far more "
                "oxidation-resistant. The wide 6 eV bandgap also makes BN transparent — "
                "a structural cable that doesn't absorb laser propulsion light."
            ),
            "accent": "#dfe6e9",
            "wiki_search": "Hexagonal boron nitride",
        },
        "SiC  (Silicon Carbide, cubic)": {
            "mp_id": "mp-7631",
            "formula": "SiC",
            "crystal_system": "Cubic (zinc blende)",
            "space_group": "F-43m",
            "key_props": {
                "Young's modulus": "~460 GPa",
                "Density": "3.21 g/cm³",
                "Melting point": "2,730 °C (sublimes)",
                "Fracture toughness": "3–5 MPa·m^½  (ceramic, but decent)",
            },
            "why_it_works": (
                "Cubic SiC (3C, or β-SiC) takes the zinc blende structure — alternating Si and C "
                "in a diamond cubic arrangement. The mixed ionic-covalent Si–C bond (bond energy "
                "~435 kJ/mol) yields a Young's modulus of ~460 GPa at a density of only 3.21 g/cm³. "
                "Its specific modulus (~143 GPa·cm³/g) places it among the best structural ceramics. "
                "SiC fibers are already used in aerospace — combined with a polymer matrix, "
                "they make composites lighter and stiffer than titanium. For a space elevator, "
                "SiC is a realistic near-term option while nanotube production scales up."
            ),
            "accent": "#55efc4",
            "wiki_search": "Silicon carbide",
        },
        "TiC  (Titanium Carbide)": {
            "mp_id": "mp-631",
            "formula": "TiC",
            "crystal_system": "Cubic (rock salt)",
            "space_group": "Fm-3m",
            "key_props": {
                "Young's modulus": "~440 GPa",
                "Density": "4.93 g/cm³",
                "Melting point": "3,160 °C",
                "Vickers hardness": "~30 GPa",
            },
            "why_it_works": (
                "TiC adopts the rock salt structure — Ti and C in alternating face-centered cubic "
                "sublattices. The strong mixed metallic-covalent Ti–C bond gives extreme hardness "
                "(nearly as hard as diamond) and a very high melting point. Unlike diamond, TiC "
                "is electrically conducting (metallic band structure from Ti d-electrons), so it "
                "can be machined by EDM and deposited as coatings. In space elevator design, "
                "TiC coatings on structural cables would resist micrometeorite abrasion — "
                "a key failure mode for any cable extending into low Earth orbit."
            ),
            "accent": "#fdcb6e",
            "wiki_search": "Titanium carbide",
        },
        "Al₂O₃  (Corundum / Sapphire)": {
            "mp_id": "mp-1143",
            "formula": "Al₂O₃",
            "crystal_system": "Trigonal",
            "space_group": "R-3c",
            "key_props": {
                "Young's modulus": "~400 GPa",
                "Density": "3.99 g/cm³",
                "Melting point": "2,072 °C",
                "Fracture toughness": "3–4 MPa·m^½",
            },
            "why_it_works": (
                "Corundum's trigonal structure packs Al³⁺ ions into octahedral sites in a "
                "hexagonal close-packed O²⁻ lattice. This arrangement maximizes Al–O bond "
                "density, giving Al₂O₃ its exceptional hardness (9 on Mohs — only diamond is "
                "harder) and chemical inertness. Single-crystal sapphire fibers grown by "
                "the edge-defined film-fed growth (EFG) process can achieve tensile strengths "
                "of ~3 GPa — competitive with high-performance Kevlar. Combined with its "
                "radiation hardness (important in high-altitude and space environments), "
                "sapphire fiber composites are a serious contender for near-term elevator cables."
            ),
            "accent": "#74b9ff",
            "wiki_search": "Corundum",
        },
    },

    "Re-entry & Thermal Shield Materials": {
        "ZrB₂  (Zirconium Diboride)": {
            "mp_id": "mp-1472",
            "formula": "ZrB₂",
            "crystal_system": "Hexagonal",
            "space_group": "P6/mmm",
            "key_props": {
                "Melting point": "3,245 °C  (among highest known)",
                "Young's modulus": "~490 GPa",
                "Thermal conductivity": "~60 W/m·K  (high for a ceramic)",
                "Class": "Ultra-High Temperature Ceramic (UHTC)",
            },
            "why_it_works": (
                "ZrB₂ is the leading UHTC for hypersonic re-entry applications. Its hexagonal "
                "AlB₂-type structure packs Zr in a simple hexagonal sublattice with boron "
                "honeycombs between layers. The strong mixed covalent-ionic Zr–B bonds give an "
                "exceptionally high melting point (3,245 °C) while the metallic-like B network "
                "conducts heat rapidly away from the hot surface — preventing catastrophic "
                "thermal shock. During starship re-entry, surface temperatures reach ~1,600–2,000 °C. "
                "ZrB₂ composites (typically ZrB₂ + SiC) can handle this with less mass than "
                "traditional silica tiles, critical for reusable vehicles."
            ),
            "accent": "#e17055",
            "wiki_search": "Zirconium diboride",
        },
        "HfB₂  (Hafnium Diboride)": {
            "mp_id": "mp-1994",
            "formula": "HfB₂",
            "crystal_system": "Hexagonal",
            "space_group": "P6/mmm",
            "key_props": {
                "Melting point": "3,380 °C  (highest of all diborides)",
                "Young's modulus": "~480 GPa",
                "Density": "10.5 g/cm³  (heavier than ZrB₂)",
                "Class": "Ultra-High Temperature Ceramic (UHTC)",
            },
            "why_it_works": (
                "HfB₂ is isostructural with ZrB₂ but hafnium's larger atomic radius and "
                "stronger Hf–B bonds push the melting point to 3,380 °C — the highest of "
                "any diboride. The heavier Hf nucleus also creates stronger spin-orbit coupling, "
                "which minutely affects bonding character but more importantly gives Hf-based "
                "ceramics superior radiation tolerance (useful at re-entry altitudes where "
                "cosmic ray flux is significant). The plasma shielding application you described "
                "— dielectric nodes that redirect plasma rather than absorb it — is physically "
                "consistent with HfB₂'s properties: it can survive the plasma while its "
                "dielectric tensor redirects the electric field component of the plasma wave."
            ),
            "accent": "#d63031",
            "wiki_search": "Hafnium diboride",
        },
        "TiB₂  (Titanium Diboride)": {
            "mp_id": "mp-1145",
            "formula": "TiB₂",
            "crystal_system": "Hexagonal",
            "space_group": "P6/mmm",
            "key_props": {
                "Melting point": "3,225 °C",
                "Young's modulus": "~565 GPa  (highest of the diborides)",
                "Density": "4.52 g/cm³  (lightest UHTC diboride)",
                "Specific modulus": "~125 GPa·cm³/g",
            },
            "why_it_works": (
                "TiB₂ has the same AlB₂-type hexagonal structure as ZrB₂ and HfB₂ but with "
                "titanium's smaller atomic radius creating shorter, stiffer Ti–B bonds. This "
                "gives TiB₂ the highest Young's modulus (~565 GPa) and lowest density among "
                "the diboride UHTCs — making it the most mass-efficient stiffener. The B₂ "
                "graphene-like layers provide high in-plane conductivity, allowing TiB₂ to "
                "rapidly redistribute thermal energy from hot spots. TiB₂ coatings are already "
                "used on cutting tools and armor. For re-entry shielding, TiB₂/SiC laminates "
                "trade some maximum temperature capability for lighter weight."
            ),
            "accent": "#fd79a8",
            "wiki_search": "Titanium diboride",
        },
        "ZrC  (Zirconium Carbide)": {
            "mp_id": "mp-1014307",
            "formula": "ZrC",
            "crystal_system": "Cubic (rock salt)",
            "space_group": "Fm-3m",
            "key_props": {
                "Melting point": "3,540 °C  (highest of the carbides)",
                "Young's modulus": "~440 GPa",
                "Thermal conductivity": "~20 W/m·K",
                "Bandgap": "~1 eV  (semi-metallic)",
            },
            "why_it_works": (
                "ZrC in the rock salt structure has the highest melting point of all transition "
                "metal carbides at 3,540 °C. Zirconium's 4d electrons partially fill a bonding "
                "band with carbon's 2p electrons, creating a mixed metallic-covalent bond of "
                "extraordinary strength. At re-entry temperatures, ZrC forms a ZrO₂ surface "
                "layer that acts as additional thermal protection — a self-healing behavior "
                "called 'passive oxidation.' For the plasma shielding concept: ZrC's "
                "semi-metallic band structure means it can reflect plasma-frequency radiation "
                "while remaining structurally intact, unlike fully metallic conductors that "
                "would ablate."
            ),
            "accent": "#6c5ce7",
            "wiki_search": "Zirconium carbide",
        },
        "ZrO₂  (Zirconia — Thermal Barrier)": {
            "mp_id": "mp-776404",
            "formula": "ZrO₂",
            "crystal_system": "Monoclinic",
            "space_group": "P2₁/c",
            "key_props": {
                "Melting point": "2,715 °C",
                "Thermal conductivity": "~2 W/m·K  (very low — insulating)",
                "Dielectric constant": "~25  (high — good for plasma shielding)",
                "Application": "Thermal barrier coating (TBC) on turbine blades & re-entry vehicles",
            },
            "why_it_works": (
                "Pure ZrO₂ transitions through three crystal phases with temperature: monoclinic "
                "(room temp) → tetragonal (1,170°C) → cubic (2,370°C), each with a volume change "
                "that would crack any coating. Yttria-stabilized zirconia (YSZ, ZrO₂ + 7–8% Y₂O₃) "
                "locks ZrO₂ in the cubic phase at all temperatures, eliminating the cracking. "
                "The resulting material has the lowest thermal conductivity of any ceramic at "
                "high temperature (~2 W/m·K), making YSZ the standard thermal barrier coating "
                "on jet engines and space vehicle leading edges. Its high dielectric constant "
                "of ~25 makes it particularly relevant to your plasma shielding vision: "
                "thick ZrO₂ layers would reflect microwave-frequency plasma oscillations "
                "much like a plasma mirror."
            ),
            "accent": "#00b894",
            "wiki_search": "Zirconium dioxide",
        },
    },

    "Superconductors": {
        "Nb  (Niobium)": {
            "mp_id": "mp-2739273",
            "formula": "Nb",
            "crystal_system": "Cubic (BCC)",
            "space_group": "Im-3m",
            "key_props": {
                "Critical temperature Tc": "9.26 K",
                "Type": "Type II superconductor",
                "Upper critical field Hc₂": "~0.4 T",
                "Application": "MRI magnets, particle accelerators (SRF cavities)",
            },
            "why_it_works": (
                "Niobium has the highest Tc of any elemental superconductor (9.26 K). Its BCC "
                "structure and half-filled 4d band create strong electron-phonon coupling — "
                "the lattice vibrations that 'pair' electrons into Cooper pairs (BCS theory). "
                "Nb is the workhorse of superconducting RF cavities in particle accelerators "
                "(CERN's LHC uses ~6,000 tonnes of Nb–Ti wire). The mechanism: at Tc, "
                "Cooper pairs condense into a macroscopic quantum state where electrical "
                "resistance vanishes completely. No energy is lost to heat — relevant to "
                "space applications where power budgets are critical."
            ),
            "accent": "#74b9ff",
            "wiki_search": "Niobium",
        },
        "MgB₂  (Magnesium Diboride)": {
            "mp_id": "mp-763",
            "formula": "MgB₂",
            "crystal_system": "Hexagonal",
            "space_group": "P6/mmm",
            "key_props": {
                "Critical temperature Tc": "39 K  (highest conventional BCS superconductor)",
                "Type": "Two-band BCS superconductor",
                "Discovery year": "2001  (previously thought impossible above ~30 K for BCS)",
                "Application": "MRI machines (cheaper than Nb–Ti at liquid H₂ temperatures)",
            },
            "why_it_works": (
                "MgB₂ has the same AlB₂-type hexagonal structure as the UHTC diborides above — "
                "but here it's the boron honeycomb layers that matter, not the interlayer metal. "
                "MgB₂ is a conventional BCS superconductor but with two distinct conduction bands "
                "(σ and π) that both participate in superconductivity simultaneously. This '2-band' "
                "mechanism is what pushes Tc to 39 K — nearly double what single-band BCS theory "
                "predicts for its phonon spectrum. Same structure as ZrB₂ and HfB₂, completely "
                "different physics: structure is not destiny — chemistry and electron count are."
            ),
            "accent": "#55efc4",
            "wiki_search": "Magnesium diboride",
        },
        "Pb  (Lead)": {
            "mp_id": "mp-20483",
            "formula": "Pb",
            "crystal_system": "Cubic (FCC)",
            "space_group": "Fm-3m",
            "key_props": {
                "Critical temperature Tc": "7.19 K",
                "Type": "Type I superconductor",
                "Penetration depth λ": "~83 nm",
                "Historical role": "First superconductor studied in detail (1911–1950s)",
            },
            "why_it_works": (
                "Lead FCC — tightest-packed metal structure — and its high atomic mass (Z=82) "
                "mean strong spin-orbit coupling that modifies the phonon spectrum in ways that "
                "enhance electron-phonon coupling despite Pb being a 'poor metal.' Lead is a "
                "Type I superconductor: magnetic field is completely expelled below Tc (Meissner "
                "effect), but a single critical field Hc destroys superconductivity abruptly. "
                "This makes Pb less practical than Type II (Nb) for magnets, but historically "
                "crucial: Pb was the test material that verified BCS theory and the isotope "
                "effect (Tc scales with 1/√M, proving phonons drive pairing)."
            ),
            "accent": "#b2bec3",
            "wiki_search": "Lead",
        },
        "NbN  (Niobium Nitride)": {
            "mp_id": "mp-2701",
            "formula": "NbN",
            "crystal_system": "Cubic (rock salt)",
            "space_group": "Fm-3m",
            "key_props": {
                "Critical temperature Tc": "~16 K",
                "Type": "Type II superconductor",
                "Key application": "Single-photon detectors (SNSPDs) for quantum computing & space",
                "Coherence length ξ": "~4–5 nm  (extremely short — enables nanowire detectors)",
            },
            "why_it_works": (
                "NbN in the rock salt structure has a rock-solid (pun intended) case for space "
                "applications: its 16 K Tc is achievable with compact cryocoolers, and its "
                "extremely short superconducting coherence length (~5 nm) allows patterning into "
                "nanowires just 4–6 atoms wide. These superconducting nanowire single-photon "
                "detectors (SNSPDs) can detect individual photons with >95% efficiency — "
                "crucial for laser communication links between Earth and spacecraft. "
                "The rock salt structure (same as TiC, ZrC above) provides hardness for "
                "thin-film durability. NbN is already in prototype space telescope detectors."
            ),
            "accent": "#a29bfe",
            "wiki_search": "Niobium nitride",
        },
    },

    "Battery Cathodes & Anodes": {
        "LiCoO₂  (Lithium Cobalt Oxide)": {
            "mp_id": "mp-22526",
            "formula": "LiCoO₂",
            "crystal_system": "Trigonal",
            "space_group": "R-3m",
            "key_props": {
                "Practical capacity": "~140 mAh/g  (theoretical: 274 mAh/g)",
                "Voltage vs Li/Li⁺": "~3.9 V",
                "Structure type": "Layered O3 — alternating Li⁺ and CoO₂ sheets",
            },
            "why_it_works": (
                "LiCoO₂ launched the lithium-ion age — it's in every smartphone and laptop "
                "built before 2015. The R-3m trigonal structure stacks layers in a precise sequence: "
                "a sheet of edge-sharing CoO₆ octahedra, then a sheet of Li⁺ ions, then another CoO₆ "
                "sheet. This **layered architecture** is a 2D highway: Li⁺ can slide in and out "
                "laterally between the cobalt oxide sheets while electrons flow through the external "
                "circuit. When you charge your phone, you're literally pulling Li⁺ out of this "
                "structure; when it discharges, they flow back in. The catch: extract more than "
                "~50% of the Li and the CoO₂ layers collapse — which is why practical capacity "
                "(140 mAh/g) is half the theoretical limit."
            ),
            "accent": "#0984e3",
            "wiki_search": "Lithium cobalt oxide",
        },
        "LiFePO₄  (Lithium Iron Phosphate)": {
            "mp_id": "mp-19017",
            "formula": "LiFePO₄",
            "crystal_system": "Orthorhombic",
            "space_group": "Pnma",
            "key_props": {
                "Capacity": "170 mAh/g  (nearly all usable)",
                "Voltage vs Li/Li⁺": "~3.4 V  (flat — no fade)",
                "Safety": "Does not release oxygen on overcharge (NCA/NMC do)",
            },
            "why_it_works": (
                "LiFePO₄ is the safety champion of EV batteries — used in Tesla Model 3 Standard "
                "Range and almost all grid storage. Its olivine structure (a dense 3D network of "
                "FeO₆ octahedra and PO₄ tetrahedra) is the key: the strong **P–O covalent bonds** "
                "inside the phosphate group lock oxygen in place chemically. At 500°C, NMC cathodes "
                "release oxygen and combust; LFP doesn't. The tradeoff is 1D Li-ion channels "
                "(along the b-axis only) — much slower than LiCoO₂'s 2D highway. Nanostructuring "
                "LFP shortens these tunnels, recovering the rate capability. The flat discharge "
                "voltage plateau means the battery reads ~100% capacity until it's genuinely nearly dead."
            ),
            "accent": "#00b894",
            "wiki_search": "Lithium iron phosphate battery",
        },
        "LiMn₂O₄  (Spinel Manganese)": {
            "mp_id": "mp-25338",
            "formula": "LiMn₂O₄",
            "crystal_system": "Cubic",
            "space_group": "Fd-3m",
            "key_props": {
                "Capacity": "~120 mAh/g",
                "Voltage vs Li/Li⁺": "~4.0 V",
                "Structure": "Spinel — 3D Li-ion tunnels through Mn₂O₄ framework",
            },
            "why_it_works": (
                "The spinel structure (same crystal type as magnetite Fe₃O₄) gives LiMn₂O₄ "
                "a fully **3D network of Li-ion tunnels** — unlike LiCoO₂'s 2D sheets. Mn occupies "
                "octahedral sites in a face-centered cubic oxygen lattice, forming a rigid "
                "Mn₂O₄ cage. Li⁺ can exit and re-enter from any direction, enabling fast charging. "
                "Manganese is also cheap, abundant, and non-toxic — unlike cobalt. "
                "The problem: near room temperature, a Jahn-Teller distortion causes the Mn₂O₄ "
                "framework to periodically distort its octahedra, dissolving Mn into the electrolyte "
                "over thousands of cycles. Doping with Ni or Al suppresses this — which led to "
                "LNMO (LiNi₀.₅Mn₁.₅O₄), a 4.7V spinel pushing current battery research."
            ),
            "accent": "#e17055",
            "wiki_search": "Lithium manganese oxide battery",
        },
        "Li₄Ti₅O₁₂  (Lithium Titanate — LTO)": {
            "mp_id": "mp-776745",
            "formula": "Li4Ti5O12",
            "crystal_system": "Cubic",
            "space_group": "Fd-3m",
            "key_props": {
                "Capacity": "175 mAh/g",
                "Voltage vs Li/Li⁺": "~1.55 V  (low — but no lithium plating)",
                "Cycle life": ">10,000 cycles  (vs ~500–1000 for graphite)",
            },
            "why_it_works": (
                "LTO is the **zero-strain anode** — a nearly miraculous property. Most anodes "
                "expand 10–15% as lithium inserts; graphite swells ~13.2%, eventually fracturing. "
                "LTO's cubic spinel structure absorbs lithium with only ~0.1% volume change. "
                "The reason: titanium changes oxidation state (Ti⁴⁺ → Ti³⁺) without moving — "
                "electrons fill the Ti 3d band while the oxide lattice barely shifts. "
                "This structural rigidity means LTO survives 10,000+ charge cycles with minimal "
                "degradation — ideal for grid storage and rapid-charge transit buses (Toshiba's "
                "SCiB cells can charge to 90% in 6 minutes). The low voltage plateau (1.55 V) "
                "prevents lithium metal plating, eliminating dendrite-related fires."
            ),
            "accent": "#a29bfe",
            "wiki_search": "Lithium titanate",
        },
    },

    "Catalysts": {
        "Pt  (Platinum — Fuel Cell Catalyst)": {
            "mp_id": "mp-126",
            "formula": "Pt",
            "crystal_system": "Cubic (FCC)",
            "space_group": "Fm-3m",
            "key_props": {
                "Oxygen reduction activity": "Best single-element catalyst known",
                "d-band center": "−2.25 eV  (near-ideal for O binding)",
                "Role": "Cathode in PEM fuel cells, car catalytic converters",
            },
            "why_it_works": (
                "Platinum's FCC structure exposes {111} and {100} surface facets with exactly "
                "the right spacing to adsorb oxygen molecules, break the O=O bond, and release "
                "water — the oxygen reduction reaction (ORR). The key descriptor is the "
                "**d-band center theory** (Hammer & Nørskov, 1995): Pt's 5d electrons sit at "
                "−2.25 eV relative to the Fermi level, which is almost perfectly positioned "
                "to bind O₂ strongly enough to dissociate it, but weakly enough to release "
                "the product (H₂O). Too strong = surface poisoned; too weak = no reaction. "
                "Pt is nature's compromise. The challenge: Pt costs ~$30,000/kg. "
                "Current research uses Pt₃Ni or Pt₃Co alloys — the Ni/Co contracts the "
                "lattice slightly, shifting the d-band center and multiplying activity by 10–100×."
            ),
            "accent": "#dfe6e9",
            "wiki_search": "Platinum",
        },
        "CeO₂  (Ceria — Oxygen Storage Catalyst)": {
            "mp_id": "mp-20194",
            "formula": "CeO₂",
            "crystal_system": "Cubic (fluorite)",
            "space_group": "Fm-3m",
            "key_props": {
                "Oxygen storage capacity": "High — can absorb/release O₂ reversibly",
                "Bandgap": "~3.2 eV (UV absorber)",
                "Role": "Three-way catalytic converter, SOFC electrolyte, UV filter",
            },
            "why_it_works": (
                "Ceria has the fluorite crystal structure: Ce⁴⁺ in an FCC array with O²⁻ filling "
                "all tetrahedral holes. The secret is **redox cycling**: CeO₂ ⇌ Ce₂O₃ + ½O₂. "
                "When the engine runs rich (excess fuel), Ce⁴⁺ accepts oxygen from the exhaust "
                "stream and reduces to Ce³⁺ — storing O²⁻ in crystal vacancies. When it runs "
                "lean (excess air), Ce³⁺ releases that oxygen to burn residual hydrocarbons. "
                "This stores and releases oxygen in milliseconds, smoothing out the combustion "
                "cycle. The crystal is forgiving of oxygen vacancies because the fluorite framework "
                "can accommodate up to ~30% vacancy without collapsing — a structural feature "
                "unique to the fluorite topology."
            ),
            "accent": "#fdcb6e",
            "wiki_search": "Cerium dioxide",
        },
        "MoS₂  (Molybdenum Disulfide — HER Catalyst)": {
            "mp_id": "mp-1023924",
            "formula": "MoS₂",
            "crystal_system": "Hexagonal",
            "space_group": "P6₃/mmc",
            "key_props": {
                "Bandgap": "~1.23 eV  (bulk indirect) / ~1.8 eV (monolayer, direct)",
                "Active sites": "Sulfur edge sites — basal plane is inert",
                "Role": "Hydrogen evolution reaction (HER), hydrodesulfurization",
            },
            "why_it_works": (
                "MoS₂ is the graphene of the catalysis world. Its hexagonal structure stacks "
                "S–Mo–S sandwiches held by van der Waals forces — just like graphite layers. "
                "The basal (flat top) surface is catalytically inert. All the action happens "
                "at the **edges**: sulfur atoms at the edge of each layer have dangling bonds "
                "that bind H⁺, then combine two H to release H₂ — the hydrogen evolution reaction. "
                "This makes MoS₂ a potential cheap replacement for Pt in green hydrogen production. "
                "The transition from bulk (indirect 1.23 eV bandgap) to monolayer (direct 1.8 eV) "
                "was a landmark 2010 discovery that launched the '2D materials beyond graphene' field. "
                "A monolayer MoS₂ transistor has been demonstrated — the thinest possible semiconductor."
            ),
            "accent": "#55efc4",
            "wiki_search": "Molybdenum disulfide",
        },
        "Fe₂O₃  (Hematite — Solar Water Splitting)": {
            "mp_id": "mp-19770",
            "formula": "Fe2O3",
            "crystal_system": "Trigonal",
            "space_group": "R-3c",
            "key_props": {
                "Bandgap": "~2.1 eV  (visible light absorber)",
                "Abundance": "Most common iron oxide — rust",
                "Role": "Photoanode for solar water splitting",
            },
            "why_it_works": (
                "Hematite (α-Fe₂O₃) is literally rust — the most abundant iron oxide on Earth, "
                "costing essentially nothing. Its corundum-type structure (same as Al₂O₃) places "
                "Fe³⁺ in octahedral holes of a hexagonal close-packed O²⁻ lattice. "
                "The 2.1 eV bandgap absorbs about 40% of the solar spectrum, giving it "
                "a theoretical solar-to-hydrogen efficiency of 15%. The catch: hole mobility is "
                "catastrophically low (~0.01 cm²/V·s vs 450 for Si) because Fe 3d states are "
                "localized — holes 'self-trap' as small polarons (the hole deforms its local "
                "crystal environment and gets stuck). The solution discovered in the 2000s: "
                "nanostructure the hematite so that every hole is within ~2–4 nm of the "
                "water interface before it can recombine. Elegant materials physics, real green energy."
            ),
            "accent": "#d63031",
            "wiki_search": "Hematite",
        },
    },

    "Thermoelectrics": {
        "Bi₂Te₃  (Bismuth Telluride)": {
            "mp_id": "mp-34202",
            "formula": "Bi₂Te₃",
            "crystal_system": "Trigonal",
            "space_group": "R-3m",
            "key_props": {
                "ZT at 300 K": "~1.0  (best room-temperature thermoelectric)",
                "Bandgap": "~0.15 eV",
                "Application": "Peltier coolers, USB beverage coolers, waste heat generators",
            },
            "why_it_works": (
                "Bi₂Te₃ is the undisputed champion of room-temperature thermoelectrics. "
                "Its layered trigonal structure — quintuple layers of Te–Bi–Te–Bi–Te held "
                "by van der Waals forces — creates a remarkable combination: high electrical "
                "conductivity (electrons flow easily along the layers) yet low thermal "
                "conductivity (phonons scatter at the weak interlayer bonds). "
                "The thermoelectric figure of merit ZT = S²σT/κ captures this: "
                "S (Seebeck coefficient) ≈ 200–250 μV/K for Bi₂Te₃, σ is high, and κ is "
                "unusually low (~1.5 W/m·K). The layered crystal structure is precisely what "
                "decouples heat flow from electron flow — the same physics makes it a "
                "topological insulator at its surface."
            ),
            "accent": "#00b894",
            "wiki_search": "Bismuth telluride",
        },
        "PbTe  (Lead Telluride)": {
            "mp_id": "mp-19717",
            "formula": "PbTe",
            "crystal_system": "Cubic (rock salt)",
            "space_group": "Fm-3m",
            "key_props": {
                "ZT at 900 K": "~2.2  (with Na doping — record for bulk material)",
                "Bandgap": "~0.32 eV",
                "Application": "NASA deep-space RTGs (Voyager, New Horizons power source)",
            },
            "why_it_works": (
                "PbTe's rock salt structure (alternating Pb and Te in a cubic lattice) "
                "seems simple, but hides remarkable physics. Pb has an unusually large, "
                "polarizable electron cloud that creates 'lone pair' resonance — the "
                "Pb atoms vibrate anharmonically, scattering phonons that carry heat "
                "while leaving electron transport largely intact. "
                "This gives PbTe an intrinsically low κ (1–2 W/m·K at high temperature). "
                "Doped with sodium (Na → Pb substitution), ZT reaches 2.2 at 900 K, "
                "the highest ever measured for a bulk thermoelectric. "
                "PbTe-based RTGs have powered NASA spacecraft continuously for 50+ years — "
                "the Voyager probes are still transmitting."
            ),
            "accent": "#74b9ff",
            "wiki_search": "Lead telluride",
        },
        "CoSb₃  (Cobalt Antimonide — Skutterudite)": {
            "mp_id": "mp-2490",
            "formula": "CoSb₃",
            "crystal_system": "Cubic",
            "space_group": "Im-3",
            "key_props": {
                "ZT (filled)": "~1.5 at 800 K  (with rare-earth filler atoms)",
                "Structure type": "Skutterudite — large voids in unit cell",
                "Application": "Automotive waste heat recovery (BMW, Toyota R&D)",
            },
            "why_it_works": (
                "CoSb₃ has a cubic structure with large cage-like voids formed by "
                "corner-sharing CoSb₆ octahedra. On its own it's a decent thermoelectric, "
                "but the breakthrough came from 'filling' those voids with rattling atoms — "
                "rare earth elements like Ce or La that are too small for the cage and "
                "literally rattle around inside it. These rattlers scatter phonons "
                "selectively — they're tuned to the heat-carrying phonon frequencies — "
                "dramatically reducing thermal conductivity without touching electron paths. "
                "This concept, called the **phonon glass, electron crystal** paradigm, "
                "is now a design principle for all advanced thermoelectrics. "
                "Filled skutterudites achieve ZT ≈ 1.5, making them candidates for "
                "converting car exhaust heat into electricity."
            ),
            "accent": "#e17055",
            "wiki_search": "Skutterudite",
        },
    },

    "Topological Insulators": {
        "Bi₂Se₃  (Bismuth Selenide)": {
            "mp_id": "mp-541837",
            "formula": "Bi₂Se₃",
            "crystal_system": "Trigonal",
            "space_group": "R-3m",
            "key_props": {
                "Bulk bandgap": "~0.35 eV  (largest among 3D TIs)",
                "Surface state": "Single Dirac cone — massless electrons at surface",
                "Application": "Quantum computing, spintronics, axion detection",
            },
            "why_it_works": (
                "Bi₂Se₃ is the textbook 3D topological insulator. Its layered structure "
                "(same R-3m as Bi₂Te₃) is critical, but the magic is in its band topology. "
                "Bismuth's heavy atomic mass creates enormous **spin-orbit coupling** — "
                "the relativistic effect where an electron's spin locks to its momentum. "
                "This inverts the normal band order near the Fermi level: what should be "
                "the conduction band drops below the valence band. This **band inversion** "
                "means the surface between Bi₂Se₃ and vacuum has a topological mismatch "
                "that *must* be bridged by metallic surface states — states protected "
                "by time-reversal symmetry that cannot be destroyed by impurities or defects. "
                "The surface electrons form a single Dirac cone: massless, spin-polarized, "
                "immune to backscattering. This is why topological insulators are being "
                "explored for dissipation-free electronics and fault-tolerant quantum bits."
            ),
            "accent": "#a29bfe",
            "wiki_search": "Bismuth selenide",
        },
        "Bi₂Te₂Se  (Bismuth Telluride Selenide)": {
            "mp_id": "mp-29227",
            "formula": "Bi₂Te₂Se",
            "crystal_system": "Trigonal",
            "space_group": "R-3m",
            "key_props": {
                "Bulk bandgap": "~0.3 eV",
                "Advantage": "Lower bulk conductivity than Bi₂Se₃ → cleaner surface signal",
                "Application": "ARPES studies, topological surface state experiments",
            },
            "why_it_works": (
                "Bi₂Te₂Se sits between Bi₂Te₃ and Bi₂Se₃ in the topological insulator family. "
                "Its quintuple-layer structure (Se–Bi–Te–Bi–Se) has the Te atoms at the "
                "layer interior and Se at the outer surface — this arrangement suppresses "
                "bulk carriers more effectively than either pure compound. "
                "The result: bulk electrical conductivity is very low, so when surface "
                "state electrons are measured (e.g., with photoemission spectroscopy), "
                "they're not drowned out by bulk signal. This made Bi₂Te₂Se the "
                "material where topological surface states were most clearly resolved "
                "experimentally in the 2010s. The Dirac cone is the same physics "
                "as Bi₂Se₃ but easier to observe cleanly."
            ),
            "accent": "#fd79a8",
            "wiki_search": "Topological insulator",
        },
        "SnTe  (Tin Telluride — Topological Crystalline Insulator)": {
            "mp_id": "mp-1883",
            "formula": "SnTe",
            "crystal_system": "Cubic (rock salt)",
            "space_group": "Fm-3m",
            "key_props": {
                "Type": "Topological crystalline insulator (TCI) — different symmetry protection",
                "Bandgap": "~0.18 eV",
                "Application": "Majorana fermion research, thermoelectrics",
            },
            "why_it_works": (
                "SnTe is a topological crystalline insulator — a new class discovered in 2012 "
                "where topological surface states are protected by crystal mirror symmetry "
                "rather than time-reversal symmetry. In the rock salt structure, SnTe has "
                "mirror planes that cannot be broken without changing the crystal symmetry. "
                "Surface states appear on the {001} and {111} faces, but NOT on surfaces "
                "that break mirror symmetry — you can control which surfaces are topological "
                "by how you cut the crystal. "
                "SnTe is also a ferroelectric above a critical Sn vacancy concentration, "
                "making it a rare material with simultaneously topological and ferroelectric "
                "properties. Topological crystalline insulators are being explored as hosts "
                "for Majorana fermions — exotic quasiparticles that are their own antiparticle, "
                "a leading candidate for fault-tolerant quantum computing qubits."
            ),
            "accent": "#fdcb6e",
            "wiki_search": "Topological insulator",
        },
    },
}
