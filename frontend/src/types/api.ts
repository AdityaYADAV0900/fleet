/**
 * Typed API interfaces matching backend Pydantic schemas across all domains.
 */

export type UserRole = 'commander' | 'planner' | 'technician';

export interface UserOut {
  id: number;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: UserRole;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ----------------------------------------------------
// Fleet & Components
// ----------------------------------------------------

export interface SystemOut {
  system_id: string;
  name: string;
}

export interface ComponentTypeOut {
  component_type_id: string;
  system_id: string;
  name: string;
  criticality: number;
  design_life_hours: number;
  mtbf_hours: number;
  part_number: string;
  is_repairable: boolean;
}

export interface ComponentOut {
  component_id: string;
  aircraft_id: string | null;
  component_type_id: string;
  serial_no: string;
  installed_date: string | null;
  hours_at_install: number;
  hours_since_new: number;
  status: string;
}

export interface AircraftListOut {
  aircraft_id: string;
  tail_code: string;
  type_code: string;
  commissioned_date: string;
  total_flight_hours: number;
  total_cycles: number;
  base_id: string | null;
  current_status: string;
}

export interface AircraftDetailOut {
  aircraft_id: string;
  tail_code: string;
  type_code: string;
  commissioned_date: string;
  total_flight_hours: number;
  total_cycles: number;
  base_id: string | null;
  current_status: string;
  components_count: number;
  systems: SystemOut[];
  installed_components: ComponentOut[];
}

// ----------------------------------------------------
// Digital Twin
// ----------------------------------------------------

export interface DriverComponentOut {
  component_id: string;
  component_name: string;
  system_name: string;
  criticality: number;
  health_index: number;
  state: string;
  risk: number | null;
  rul_p50: number | null;
}

export interface TwinTrajectoryPoint {
  date: string;
  health_index: number;
  risk: number | null;
  rul: number | null;
  is_forecast: boolean;
}

export interface TwinMaintenanceEvent {
  event_id: string | number;
  event_type: string;
  date: string;
  description: string;
  status: string;
}

export interface TwinComponentNodeOut {
  component_id: string;
  component_name: string;
  part_number: string;
  serial_number: string;
  system_id: string;
  system_name: string;
  aircraft_id: string;
  criticality: number;
  health_index: number;
  state: string;
  risk: number | null;
  rul_p50: number | null;
}

export interface TwinSystemNodeOut {
  system_id: string;
  system_name: string;
  health_index: number;
  state: string;
  risk: number | null;
  rul_p50: number | null;
  driver_component: DriverComponentOut | null;
  components: TwinComponentNodeOut[];
}

export interface TwinAircraftNodeOut {
  aircraft_id: string;
  tail_code: string;
  type_code: string;
  health_index: number;
  state: string;
  risk: number | null;
  rul_p50: number | null;
  as_of_date: string;
  is_replay: boolean;
  driver_component: DriverComponentOut | null;
  systems: TwinSystemNodeOut[];
  maintenance_history: TwinMaintenanceEvent[];
  predicted_trajectory: TwinTrajectoryPoint[];
}

export interface TwinFleetSummaryAircraftOut {
  aircraft_id: string;
  tail_code: string;
  type_code: string;
  health_index: number;
  state: string;
  risk: number | null;
  rul_p50: number | null;
  driver_component: DriverComponentOut | null;
}

export interface TwinFleetOut {
  node_id: string;
  as_of_date: string;
  health_index: number;
  total_aircraft: number;
  state_distribution: Record<string, number>;
  driver_aircraft_id: string | null;
  aircraft: TwinFleetSummaryAircraftOut[];
}

export interface TwinComponentDetailOut {
  component_id: string;
  component_name: string;
  part_number: string;
  serial_number: string;
  system_id: string;
  system_name: string;
  aircraft_id: string;
  criticality: number;
  health_index: number;
  state: string;
  risk: number | null;
  rul_p50: number | null;
  as_of_date: string;
  is_replay: boolean;
  hours_since_new: number;
  operating_hours: number;
  active_advisory: Record<string, unknown> | null;
  recent_sensor_metrics: Record<string, unknown>;
  maintenance_history: TwinMaintenanceEvent[];
  predicted_trajectory: TwinTrajectoryPoint[];
}

// ----------------------------------------------------
// Predictive Engine, Advisories, Alerts, Predictions
// ----------------------------------------------------

export interface PredictionOut {
  prediction_id: number;
  component_id: string;
  aircraft_id: string | null;
  tail_code: string | null;
  system_name: string | null;
  component_name: string | null;
  as_of_date: string;
  risk_14d: number;
  risk_30d: number;
  rul_p10: number;
  rul_p50: number;
  rul_p90: number;
  model_version: string;
  created_at: string;
}

export interface AdvisoryOut {
  advisory_id: string;
  component_id: string;
  aircraft_id: string | null;
  tail_code: string | null;
  system_name: string | null;
  component_name: string | null;
  as_of_date: string;
  priority: 'P1' | 'P2' | 'P3' | 'P4' | string;
  action: string;
  status: 'proposed' | 'accepted' | 'scheduled' | 'completed' | 'dismissed' | string;
  dismiss_reason: string | null;
  explanation: {
    rule?: string;
    factors?: Record<string, number | string>;
    top_drivers?: Array<{ feature: string; impact: number }>;
    top_shap_factors?: Array<{ feature: string; shap_impact: number }>;
    top_factors?: Array<{ feature: string; shap_impact?: number; impact?: number }>;
    text?: string;
    [key: string]: unknown;
  } | null;
  spare_status: string | null;
  expected_downtime_days: number | null;
  created_at: string;
}

export interface AlertOut {
  alert_id: number;
  type: 'risk_threshold' | 'spare_shortfall' | 'overdue' | 'backlog' | string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  aircraft_id: string | null;
  component_id: string | null;
  advisory_id: string | null;
  message: string;
  created_at: string;
  acknowledged: boolean;
}

export interface EngineRunSummaryOut {
  as_of_date: string;
  duration_seconds: number;
  components_scored: number;
  predictions_recorded: number;
  anomaly_scores_recorded: number;
  advisories_generated: number;
  alerts_generated: number;
  p1_count: number;
  p2_count: number;
  high_risk_components: number;
}

// ----------------------------------------------------
// Fleet Availability & KPIs
// ----------------------------------------------------

export interface DowntimeByCauseOut {
  scheduled_days: number;
  unscheduled_days: number;
  supply_wait_days: number;
  agency_wait_days: number;
  total_downtime_days: number;
  scheduled_pct: number;
  unscheduled_pct: number;
  supply_wait_pct: number;
  agency_wait_pct: number;
}

export interface BacklogOut {
  open_orders: number;
  outstanding_man_hours: number;
}

export interface ComponentTypeKpiOut {
  component_type_id: string;
  name: string;
  failures: number;
  mtbf_spec: number;
  calculated_mtbf: number;
  mttr_hours: number;
}

export interface KpiResponse {
  fleet_availability_pct: number;
  inherent_availability_pct: number;
  operational_availability_pct: number;
  serviceability_pct: number;
  downtime_by_cause: DowntimeByCauseOut;
  mtbf_hours: number;
  mttr_hours: number;
  turnaround_days: number;
  failure_rate_per_1000_hours: number;
  backlog: BacklogOut;
  readiness_proxy_pct: number;
  spare_fill_rate_pct: number;
  total_aircraft: number;
  total_flight_hours: number;
  by_component_type: ComponentTypeKpiOut[];
}

export interface FleetSummaryOut {
  as_of: string;
  total_aircraft: number;
  serviceable_count: number;
  availability_pct: number;
  by_state: Record<string, number>;
  open_p1: number;
  open_p2: number;
  backlog: {
    open_orders?: number;
    outstanding_man_hours?: number;
    [key: string]: unknown;
  };
  parts_at_risk: number;
}

export interface AvailabilityTrendPoint {
  date: string;
  avail: number;
  p10: number | null;
  p90: number | null;
  is_forecast: boolean;
}

export interface AvailabilityTrendOut {
  points: AvailabilityTrendPoint[];
}

export interface ScenarioMetricsOut {
  availability_p50: number;
  availability_p10: number;
  availability_p90: number;
  aircraft_days_lost: number;
  stockout_probability: number;
}

export interface ScenarioDeltaOut {
  availability_pct_points: number;
  aircraft_days_lost: number;
}

export interface DailyTrendPoint {
  day: number;
  p10: number;
  p50: number;
  p90: number;
  mean_avail?: number;
}

export interface ScenarioRunOut {
  id: string;
  type: string;
  params: Record<string, unknown>;
  horizon_days: number;
  runs: number;
  seed: number;
  baseline: ScenarioMetricsOut;
  scenario: ScenarioMetricsOut;
  delta: ScenarioDeltaOut;
  by_cause: Record<string, number>;
  daily_trend?: {
    baseline?: DailyTrendPoint[];
    scenario?: DailyTrendPoint[];
    days?: number[];
    baseline_p50?: number[];
    scenario_p50?: number[];
    scenario_p10?: number[];
    scenario_p90?: number[];
    [key: string]: unknown;
  } | null;
}

// ----------------------------------------------------
// Maintenance & Work Orders
// ----------------------------------------------------

export interface AgencyOut {
  agency_id: string;
  name: string;
  level: string;
  bays: number;
  capacity_hours_per_day: number;
  avg_turnaround_days: number;
}

export interface ScheduledTaskOut {
  task_id: string;
  aircraft_id: string;
  task_name: string;
  interval_hours: number;
  last_done_hours: number;
  due_hours: number;
  due_date: string | null;
}

export interface WorkOrderOut {
  wo_id: string;
  aircraft_id: string;
  component_id: string | null;
  advisory_id: string | null;
  agency_id: string;
  opened: string;
  planned_start: string | null;
  actual_start: string | null;
  promised_done: string | null;
  actual_done: string | null;
  status: string;
  priority: string;
  delay_reason: string | null;
}

export interface WorkOrderCreateIn {
  aircraft_id: string;
  component_id?: string | null;
  advisory_id?: string | null;
  agency_id: string;
  priority?: string;
  planned_start?: string | null;
  promised_done?: string | null;
  bundle_inspection?: boolean;
  delay_reason?: string | null;
}

export interface MaintenanceEventOut {
  event_id: string;
  aircraft_id: string;
  component_id: string | null;
  type: string;
  start: string;
  end: string | null;
  action: string;
  labor_hours: number;
  work_order_id: string | null;
  root_cause: string | null;
}

// ----------------------------------------------------
// Spares & Inventory
// ----------------------------------------------------

export interface SparePartOut {
  part_number: string;
  description: string;
  criticality: number;
  unit_cost: number;
  lead_time_days: number;
  reorder_level: number;
}

export interface InventoryOut {
  inventory_id: number;
  part_number: string;
  location_id: string;
  on_hand: number;
  reserved: number;
  on_order: number;
  expected_receipt_date: string | null;
  is_low_stock: boolean;
}

export interface InventoryTransactionOut {
  txn_id: number;
  part_number: string;
  date: string;
  qty: number;
  type: string;
  work_order_id: string | null;
}

// ----------------------------------------------------
// Telemetry & Sensors
// ----------------------------------------------------

export interface SensorReadingOut {
  reading_id: number;
  flight_id: string;
  component_id: string;
  parameter: string;
  mean: number;
  max: number;
  min: number;
  std: number;
  quality_flag: string;
  date?: string | null;
}

export interface FaultEventOut {
  event_id: string;
  aircraft_id: string;
  component_id: string;
  timestamp: string;
  fault_code: string;
  severity: string;
  description: string;
  source: string;
}

export interface AnomalyScoreOut {
  score_id: number;
  component_id: string;
  flight_id: string;
  date?: string | null;
  score: number;
  is_anomaly: boolean;
  top_parameters?: Record<string, unknown> | null;
}
