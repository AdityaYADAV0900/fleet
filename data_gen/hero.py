"""Hero-aircraft scenarios for demonstration and scripted validation."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class HeroScenario:
    aircraft_id: str
    target_component_type_id: str
    scenario_type: str  # 'hydraulic_degradation_tight_spares', 'compressor_gradual_creep', 'sudden_electrical_shock', 'scheduled_heavy_servicing'
    onset_date: date
    target_health_at_end: float
    description: str
    force_spare_stock: dict[str, int] | None = None


HERO_SCENARIOS: list[HeroScenario] = [
    # 1. Primary Hero: AC-017 Hydraulic Pump Degradation with Tight Spares
    HeroScenario(
        aircraft_id="AC-017",
        target_component_type_id="CT-HYD-01",
        scenario_type="hydraulic_degradation_tight_spares",
        onset_date=date(2025, 11, 10),
        target_health_at_end=0.41,
        description=(
            "AC-017 Primary Hydraulic Pump (HYD-114) experiences accelerated internal seal wear "
            "and outlet pressure drop starting mid-Nov 2025. Stock is constrained to 1 unit with "
            "a 45-day replenishment lead time, creating high operational availability risk."
        ),
        force_spare_stock={"HYD-114": 1},
    ),
    # 2. Hero 2: AC-005 Engine Compressor Thermal/Vibration Creep
    HeroScenario(
        aircraft_id="AC-005",
        target_component_type_id="CT-PROP-01",
        scenario_type="compressor_gradual_creep",
        onset_date=date(2025, 9, 20),
        target_health_at_end=0.52,
        description=(
            "AC-005 Main Engine Compressor develops blade fouling and mechanical vibration "
            "drift starting late Sep 2025. Early predictive anomaly detection candidate."
        ),
    ),
    # 3. Hero 3: AC-023 Sudden Electrical Generator Shock Failure
    HeroScenario(
        aircraft_id="AC-023",
        target_component_type_id="CT-ELEC-01",
        scenario_type="sudden_electrical_shock",
        onset_date=date(2024, 8, 14),
        target_health_at_end=0.02,
        description=(
            "AC-023 Main Integrated Drive Generator suffers an unheralded rotor winding short "
            "in Aug 2024 (~15% sudden failure profile), demonstrating reactive unscheduled repair."
        ),
    ),
    # 4. Hero 4: AC-031 Heavy Scheduled Depot Inspection Bundle
    HeroScenario(
        aircraft_id="AC-031",
        target_component_type_id="CT-LG-02",
        scenario_type="scheduled_heavy_servicing",
        onset_date=date(2025, 6, 1),
        target_health_at_end=0.98,
        description=(
            "AC-031 undergoes a major 1200-Hour C-Check in June 2025 with multiple components "
            "serviced in parallel at Base Maintenance Depot."
        ),
    ),
]

# Lookup map by aircraft_id
HERO_MAP: dict[str, HeroScenario] = {s.aircraft_id: s for s in HERO_SCENARIOS}
