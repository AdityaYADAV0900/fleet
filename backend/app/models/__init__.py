from app.models.base import Base
from app.models.fleet import (
    Aircraft,
    AircraftDailyStatus,
    Component,
    ComponentType,
    System,
)
from app.models.maintenance import (
    Agency,
    MaintenanceEvent,
    ScheduledTask,
    WorkOrder,
)
from app.models.platform import (
    Advisory,
    Alert,
    AnomalyScore,
    ModelRun,
    Prediction,
    ScenarioRun,
    SimulationTruth,
    TwinSnapshot,
    User,
)
from app.models.sensors import (
    FaultEvent,
    Flight,
    SensorReading,
)
from app.models.spares import (
    Inventory,
    InventoryTransaction,
    SparePart,
)

__all__ = [
    "Base",
    # Fleet
    "System",
    "ComponentType",
    "Aircraft",
    "Component",
    "AircraftDailyStatus",
    # Sensors
    "Flight",
    "SensorReading",
    "FaultEvent",
    # Maintenance
    "Agency",
    "ScheduledTask",
    "WorkOrder",
    "MaintenanceEvent",
    # Spares
    "SparePart",
    "Inventory",
    "InventoryTransaction",
    # Platform
    "User",
    "SimulationTruth",
    "AnomalyScore",
    "Prediction",
    "Advisory",
    "TwinSnapshot",
    "Alert",
    "ScenarioRun",
    "ModelRun",
]
