"""Latent-health degradation engine modeling stochastic component deterioration."""

import random
from dataclasses import dataclass
from datetime import date

from data_gen.config import DegradationConfig
from data_gen.hero import HERO_MAP, HeroScenario
from data_gen.hierarchy import COMPONENT_TYPE_MAP


@dataclass
class ComponentHealthState:
    component_id: str
    component_type_id: str
    aircraft_id: str | None
    true_health: float
    wear_rate_multiplier: float  # Per-unit personality
    is_sudden_shock_candidate: bool
    shock_flight_count: int | None = None
    flights_completed: int = 0
    hours_accumulated: float = 0.0
    degradation_phase: str = "linear"  # linear, exponential, sudden
    is_failed: bool = False
    hero_scenario: HeroScenario | None = None


class DegradationEngine:
    """Manages latent true health states, degradation steps, and ground-truth simulation records."""

    def __init__(self, config: DegradationConfig, rng: random.Random):
        self.config = config
        self.rng = rng
        self.component_states: dict[str, ComponentHealthState] = {}

    def register_component(
        self,
        component_id: str,
        component_type_id: str,
        aircraft_id: str | None,
        initial_health: float,
        hours_since_new: float = 0.0,
    ) -> ComponentHealthState:
        """Register a new or replacement component with a unique unit personality."""
        # Check if aircraft has a scripted hero scenario targeting this component type
        hero = None
        if aircraft_id and aircraft_id in HERO_MAP:
            sc = HERO_MAP[aircraft_id]
            if sc.target_component_type_id == component_type_id:
                hero = sc

        # Draw per-unit personality
        wear_mult = max(0.5, self.rng.gauss(1.0, 0.18))

        # Check if candidate for ~15% sudden shock failures (deliberate unheralded failure mode)
        is_shock = False
        shock_flight = None
        if not hero:
            is_shock = self.rng.random() < self.config.sudden_failure_prob
            if is_shock:
                # Shock triggers between 300 and 1500 flights
                shock_flight = self.rng.randint(300, 1600)

        state = ComponentHealthState(
            component_id=component_id,
            component_type_id=component_type_id,
            aircraft_id=aircraft_id,
            true_health=round(initial_health, 4),
            wear_rate_multiplier=wear_mult,
            is_sudden_shock_candidate=is_shock,
            shock_flight_count=shock_flight,
            hours_accumulated=hours_since_new,
            hero_scenario=hero,
        )
        self.component_states[component_id] = state
        return state

    def step_degradation(
        self,
        component_id: str,
        flight: dict,
    ) -> tuple[float, str, bool]:
        """Apply one flight's wear and environmental stress to the component's true health.

        Returns:
            (new_true_health, degradation_phase, is_failed)
        """
        state = self.component_states[component_id]
        if state.is_failed:
            return state.true_health, state.degradation_phase, True

        duration = flight["duration_hours"]
        ambient_temp = flight["ambient_temp_c"] or 20.0
        load_factor = flight["load_factor"] or 1.0
        current_date: date = flight["date"]

        state.flights_completed += 1
        state.hours_accumulated += duration

        # Check Hero Scenario script first
        if state.hero_scenario is not None:
            hero = state.hero_scenario
            if hero.scenario_type == "hydraulic_degradation_tight_spares":
                if current_date < hero.onset_date:
                    base_healthy = 0.88 - (state.hours_accumulated / 20000.0)
                    state.true_health = round(max(0.82, base_healthy + self.rng.gauss(0, 0.003)), 4)
                    state.degradation_phase = "linear"
                    return state.true_health, state.degradation_phase, False
                else:
                    days_since_onset = (current_date - hero.onset_date).days
                    # Smoothly drop from ~0.84 down to target_health_at_end (~0.41)
                    frac = min(1.0, days_since_onset / 40.0)
                    target = 0.84 - frac * (0.84 - hero.target_health_at_end)
                    state.true_health = round(target + self.rng.gauss(0, 0.004), 4)
                    state.degradation_phase = "exponential"
                    return state.true_health, state.degradation_phase, False

            elif hero.scenario_type == "compressor_gradual_creep":
                if current_date < hero.onset_date:
                    base_healthy = 0.90 - (state.hours_accumulated / 20000.0)
                    state.true_health = round(max(0.85, base_healthy + self.rng.gauss(0, 0.003)), 4)
                    state.degradation_phase = "linear"
                    return state.true_health, state.degradation_phase, False
                else:
                    days_since_onset = (current_date - hero.onset_date).days
                    frac = min(1.0, days_since_onset / 90.0)
                    target = 0.86 - frac * (0.86 - hero.target_health_at_end)
                    state.true_health = round(target + self.rng.gauss(0, 0.004), 4)
                    state.degradation_phase = "linear"
                    return state.true_health, state.degradation_phase, False

            elif hero.scenario_type == "sudden_electrical_shock":
                if current_date < hero.onset_date:
                    base_healthy = 0.92 - (state.hours_accumulated / 20000.0)
                    state.true_health = round(max(0.86, base_healthy + self.rng.gauss(0, 0.003)), 4)
                    state.degradation_phase = "linear"
                    return state.true_health, state.degradation_phase, False
                else:
                    state.true_health = hero.target_health_at_end
                    state.degradation_phase = "sudden"
                    state.is_failed = True
                    return state.true_health, state.degradation_phase, True

        # Check Sudden Shock profile (~15% of fleet components)
        if state.is_sudden_shock_candidate and state.shock_flight_count is not None:
            if state.flights_completed >= state.shock_flight_count:
                # Sudden failure shock
                state.true_health = round(self.rng.uniform(0.01, 0.04), 4)
                state.degradation_phase = "sudden"
                state.is_failed = True
                return state.true_health, state.degradation_phase, True

        # Standard Stochastic Latent Health Process (Gamma increment with stress-dependent drift)
        ct_def = COMPONENT_TYPE_MAP.get(state.component_type_id)
        base_rate = (1.0 / max(ct_def.mtbf_hours if ct_def else 2500.0, 500.0)) * 0.85

        # Operational stress factor
        temp_stress = max(0.0, (ambient_temp - 22.0) / 18.0)
        load_stress = max(0.0, (load_factor - 1.0) / 0.25)
        stress_factor = 1.0 + self.config.stress_weight * (0.5 * temp_stress + 0.5 * load_stress)

        # Gamma distributed degradation increment per flight hour
        # shape=gamma_shape, scale = base_rate / shape
        shape = self.config.gamma_shape
        scale = (base_rate / shape) * duration * state.wear_rate_multiplier * stress_factor
        delta_h = self.rng.gammavariate(shape, scale)

        # If health has degraded into warning zone, degradation accelerates (exponential phase)
        if state.true_health < self.config.warning_threshold:
            delta_h *= 1.8
            state.degradation_phase = "exponential"
        else:
            state.degradation_phase = "linear"

        new_health = max(0.0, state.true_health - delta_h)
        state.true_health = round(new_health, 4)

        if state.true_health <= self.config.failure_threshold:
            state.is_failed = True

        return state.true_health, state.degradation_phase, state.is_failed
