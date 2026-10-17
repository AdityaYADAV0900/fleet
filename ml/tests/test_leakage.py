"""Temporal leakage verification test suite.

CRITICAL RULE (AGENTS.md):
Features may use only information available at or before the prediction date.
This test proves that altering or appending future events does NOT leak into past feature vectors.
"""

from datetime import UTC, date, datetime

import pandas as pd

from ml.data import RawFleetData
from ml.features import FeaturePipeline


def create_mock_raw_data(include_future_events: bool = False) -> RawFleetData:
    """Create a controlled mini-fleet dataset for leakage verification."""
    flights = pd.DataFrame(
        [
            {
                "flight_id": f"FL-{i:03d}",
                "aircraft_id": "AC-001",
                "date": date(2023, 1, i),
                "duration_hours": 2.0,
                "cycles": 1,
                "ambient_temp_c": 15.0,
                "altitude_band": "Medium",
                "load_factor": 1.0,
            }
            for i in range(1, 11)
        ]
    )

    readings = []
    for i in range(1, 11):
        readings.append(
            {
                "flight_id": f"FL-{i:03d}",
                "component_id": "CMP-001",
                "parameter": "vibration",
                "mean": 1.5 + (0.05 * i if i <= 5 else (10.0 if include_future_events else 1.8)),
                "max": 2.0,
                "min": 1.0,
                "std": 0.2,
                "quality_flag": "valid",
            }
        )
    readings_df = pd.DataFrame(readings)

    components_df = pd.DataFrame(
        [
            {
                "component_id": "CMP-001",
                "aircraft_id": "AC-001",
                "component_type_id": "CT-PROP-01",
                "install_date": date(2022, 1, 1),
            }
        ]
    )

    types_df = pd.DataFrame(
        [
            {
                "component_type_id": "CT-PROP-01",
                "system_id": "SYS-PROP",
                "name": "Compressor",
                "criticality": 5,
                "design_life_hours": 5000.0,
                "mtbf_hours": 2000.0,
            }
        ]
    )

    # Past fault on day 2
    faults = [
        {
            "event_id": "EVT-001",
            "aircraft_id": "AC-001",
            "component_id": "CMP-001",
            "timestamp": datetime(2023, 1, 2, 12, 0, tzinfo=UTC),
            "date": date(2023, 1, 2),
            "severity": "low",
            "fault_code": "WARN",
        }
    ]
    # Future fault on day 9 if include_future_events is True
    if include_future_events:
        faults.append(
            {
                "event_id": "EVT-002",
                "aircraft_id": "AC-001",
                "component_id": "CMP-001",
                "timestamp": datetime(2023, 1, 9, 12, 0, tzinfo=UTC),
                "date": date(2023, 1, 9),
                "severity": "critical",
                "fault_code": "CRIT",
            }
        )

    # Maintenance replacement in future (day 10)
    maint = [
        {
            "event_id": "ME-001",
            "aircraft_id": "AC-001",
            "component_id": "CMP-001",
            "type": "unscheduled",
            "action": "replace",
            "start": datetime(2023, 1, 10, 16, 0, tzinfo=UTC),
            "date": date(2023, 1, 10),
            "end": datetime(2023, 1, 12, 16, 0, tzinfo=UTC),
            "labor_hours": 12.0,
        }
    ]

    return RawFleetData(
        flights=flights,
        sensor_readings=readings_df,
        fault_events=pd.DataFrame(faults),
        maintenance_events=pd.DataFrame(maint),
        components=components_df,
        component_types=types_df,
    )


def test_no_future_leakage_in_features() -> None:
    """Prove that features computed on day 4 are completely unchanged by future events on day 9-10."""
    raw_nominal = create_mock_raw_data(include_future_events=False)
    raw_altered_future = create_mock_raw_data(include_future_events=True)

    pipeline_nom = FeaturePipeline()
    bundle_nom = pipeline_nom.fit_transform(raw_nominal)

    pipeline_alt = FeaturePipeline()
    bundle_alt = pipeline_alt.fit_transform(raw_altered_future)

    # Filter to observation at Day 4 (2023-01-04)
    nom_day4 = bundle_nom.X[bundle_nom.features_df["date"] == date(2023, 1, 4)].iloc[0]
    alt_day4 = bundle_alt.X[bundle_alt.features_df["date"] == date(2023, 1, 4)].iloc[0]

    # Verify all engineered feature values are strictly equal
    for feat in bundle_nom.feature_names:
        val_nom = float(nom_day4[feat])
        val_alt = float(alt_day4[feat])
        assert abs(val_nom - val_alt) < 1e-6, (
            f"LEAKAGE DETECTED in feature '{feat}' at Day 4: "
            f"nominal={val_nom} vs future-altered={val_alt}"
        )
