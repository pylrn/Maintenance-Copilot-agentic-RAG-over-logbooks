"""Reviewed component educational context and 2D visual mapping service."""

import json
from pathlib import Path
from typing import Any

from maintenance.contracts import ComponentContextEnvelope

ROOT = Path(__file__).resolve().parents[2]


class VisualService:
    def __init__(self, catalog_path: Path | None = None, mappings_path: Path | None = None):
        catalog_path = catalog_path or (ROOT / "config/component_catalog.json")
        mappings_path = mappings_path or (ROOT / "config/visual_mappings.json")

        self.catalog: dict[str, Any] = {}
        if catalog_path.exists():
            self.catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

        self.mappings: dict[str, Any] = {}
        if mappings_path.exists():
            self.mappings = json.loads(mappings_path.read_text(encoding="utf-8"))

        self.components_by_id = {
            c["component_id"]: c for c in self.catalog.get("components", [])
        }

        # Curated reviewed component explanations (educational only, not log authority)
        self.curated_explanations: dict[str, dict[str, Any]] = {
            "cylinder_assembly": {
                "name": "Cylinder Assembly",
                "explanation": (
                    "In horizontally-opposed aviation engines, each cylinder forms the combustion chamber "
                    "housing the piston, valves, and spark plugs. Cylinder numbering convention differs by engine "
                    "manufacturer (e.g. Lycoming numbers odd cylinders front-to-back on right, Continental on left). "
                    "Logs frequently cite specific cylinder numbers for leaks, compression checks, or replacement."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B Aviation Maintenance Technician Handbook—Powerplant",
                        "chapter": "Chapter 1: Aircraft Engines",
                        "section": "Reciprocating Engine Construction - Cylinders",
                    }
                ],
            },
            "intake_system": {
                "name": "Intake System",
                "explanation": (
                    "The induction system distributes air (or fuel/air mixture) from the throttle body or carburetor "
                    "to individual cylinder intake ports. Leaks at intake pipes or gaskets induce unmetered ambient air, "
                    "causing lean mixtures, rough idling, and RPM drops during ground checks."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B",
                        "chapter": "Chapter 1",
                        "section": "Induction Systems",
                    }
                ],
            },
            "intake_gasket": {
                "name": "Intake Flange Gasket",
                "explanation": (
                    "The intake gasket seals the junction between the cylinder intake port and the intake manifold pipe flange. "
                    "A deteriorated gasket allows ambient air into the cylinder under manifold vacuum. Common maintenance logs "
                    "record removal and replacement of the intake gasket to resolve induction leaks detected on ground run-up."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B",
                        "chapter": "Chapter 1",
                        "section": "Induction Flange Seals",
                    }
                ],
            },
            "intake_pipe": {
                "name": "Intake Pipe / Induction Tube",
                "explanation": (
                    "Intake tubes run from the induction plenum beneath the crankcase to each cylinder intake port. "
                    "Subject to vibration and thermal expansion, tubes may crack, loosen at hose couplings, or suffer "
                    "flange distortion, leading to audible hissing or lean operation."
                ),
                "citations": [
                    {"source": "FAA-H-8083-32B", "chapter": "Chapter 1", "section": "Manifold Runners"}
                ],
            },
            "rocker_cover": {
                "name": "Rocker Box Cover & Gasket",
                "explanation": (
                    "The rocker cover encloses the rocker arms and valve springs on the cylinder head. Rocker cover gasket "
                    "failures allow engine oil to leak onto cylinder cooling fins or exhaust pipes, producing burning oil odor "
                    "and oil streaks, distinct from vacuum leaks at the intake."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B",
                        "chapter": "Chapter 1",
                        "section": "Valve Operating Mechanisms",
                    }
                ],
            },
            "exhaust_system": {
                "name": "Exhaust Manifold & Riser",
                "explanation": (
                    "Exhaust risers channel high-temperature combustion gases away from cylinder exhaust ports to the muffler "
                    "or turbocharger. Exhaust leaks present carbon monoxide and fire hazards and produce distinctive gray/white exhaust staining."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B",
                        "chapter": "Chapter 3",
                        "section": "Engine Exhaust and Reversing Systems",
                    }
                ],
            },
            "crankcase": {
                "name": "Crankcase",
                "explanation": (
                    "The crankcase is the central cast aluminum alloy housing supporting the crankshaft, camshaft, and cylinder bases. "
                    "It sustains high structural and hydraulic loads and forms the main oil return gallery."
                ),
                "citations": [
                    {"source": "FAA-H-8083-32B", "chapter": "Chapter 1", "section": "Crankcase Sections"}
                ],
            },
            "baffle_assembly": {
                "name": "Cooling Baffles & Flexible Seals",
                "explanation": (
                    "Sheet metal baffles and flexible rubber/silicone seals direct ram cooling air across cylinder barrel fins "
                    "and oil coolers. Missing or damaged baffles cause uneven cylinder head temperatures (CHT) and localized overheating."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B",
                        "chapter": "Chapter 6",
                        "section": "Engine Cooling Systems",
                    }
                ],
            },
            "fuel_system": {
                "name": "Fuel Metering & Injection",
                "explanation": (
                    "Fuel injectors or carburetors meter fuel based on mass airflow into cylinders. Clogged nozzles or leaking "
                    "fittings result in uneven cylinder temperatures and fuel staining."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B",
                        "chapter": "Chapter 2",
                        "section": "Engine Fuel and Metering Systems",
                    }
                ],
            },
            "oil_system": {
                "name": "Oil Lubrication & Filtration",
                "explanation": (
                    "Provides pressure lubrication to bearings, valve gear, and pistons. Includes pump, full-flow filter, "
                    "thermostatic vernatherm valve, and oil cooler."
                ),
                "citations": [
                    {
                        "source": "FAA-H-8083-32B",
                        "chapter": "Chapter 4",
                        "section": "Engine Lubrication Systems",
                    }
                ],
            },
        }

    def get_asset_info(self, asset_id: str) -> dict[str, Any] | None:
        if asset_id == self.mappings.get("asset_id"):
            asset_file = ROOT / "api/static/assets/engine-concept.svg"
            return {
                "asset_id": asset_id,
                "license": self.mappings.get("license", "CC-BY-4.0"),
                "attribution": self.mappings.get("attribution", ""),
                "applicability": self.mappings.get("applicability", {}),
                "illustrative": True,
                "file_path": str(asset_file),
                "exists": asset_file.exists(),
            }
        return None

    def get_component_context(
        self, component_id: str, aircraft_profile: dict[str, Any] | None = None
    ) -> ComponentContextEnvelope:
        curated = self.curated_explanations.get(component_id)
        comp_def = self.components_by_id.get(component_id)

        canonical_name = (
            curated["name"]
            if curated
            else (comp_def["canonical_name"] if comp_def else component_id.replace("_", " ").title())
        )
        explanation = (
            curated["explanation"]
            if curated
            else "Reviewed educational background for this component is pending."
        )
        citations = curated["citations"] if curated else []

        # Find visual mapping hotspots
        asset_mapping_ids = [
            m["hotspot_id"]
            for m in self.mappings.get("mappings", [])
            if m.get("component_id") == component_id
        ]

        # Determine applicability based on aircraft profile
        # Dataset records have unknown applicability. A user profile is user context.
        applicability = "generic"
        if aircraft_profile and aircraft_profile.get("model"):
            applicability = "generic"  # Still generic since educational schematics are generic

        return ComponentContextEnvelope(
            component_id=component_id,
            name=canonical_name,
            explanation=explanation,
            citations=citations,
            profile_revision=0,
            applicability=applicability,
            source_available=True,
            asset_mapping_ids=asset_mapping_ids,
            related_log_ids=[],
        )
