export type UserRole = 'COORDINATOR' | 'COMPANY' | 'STUDENT';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  name?: string;
  entity_id?: string;
  is_active: boolean;
}

export interface Student {
  id: string;
  user_id: string;
  student_code: string;
  name: string;
  email: string;
  branch: string;
  cgpa: number;
  graduation_year: number;
  skills: string[];
  is_active: boolean;
  is_withdrawn: boolean;
  shortlisted_companies?: string[];
  interview_count?: number;
}

export interface CompanyRequirement {
  min_cgpa: number;
  eligible_branches: string[];
  rounds_count: number;
}

export interface CompanyAvailability {
  day_number: number;
  start_time_slot: number;
  end_time_slot: number;
  is_available: boolean;
}

export interface Company {
  id: string;
  user_id: string;
  company_code: string;
  name: string;
  industry: string;
  priority_tier: number;
  interview_duration_mins: number;
  max_panels: number;
  is_active: boolean;
  requirements?: CompanyRequirement;
  availability?: CompanyAvailability[];
  panels_count: number;
  shortlisted_count: number;
}

export interface Room {
  id: string;
  room_code: string;
  building: string;
  floor: number;
  capacity: number;
  has_video_conf: boolean;
  is_active: boolean;
}

export interface Panel {
  id: string;
  company_id: string;
  company_name?: string;
  panel_code: string;
  interviewer_names: string;
  is_active: boolean;
}

export interface Shortlist {
  id: string;
  company_id: string;
  student_id: string;
  student_code: string;
  student_name: string;
  student_branch: string;
  student_cgpa: number;
  preference_rank: number;
  status: string;
}

export interface InterviewAuditMetadata {
  constraint_checks: Record<string, boolean>;
  optimization_reasons: string[];
  rejected_alternatives: Array<{ slot: string; reason: string }>;
  replan_reason?: string;
  strategy_applied?: string;
}

export interface Interview {
  id: string;
  schedule_version_id: string;
  student_id: string;
  student_code: string;
  student_name: string;
  student_branch: string;
  student_cgpa: number;
  company_id: string;
  company_name: string;
  company_tier: number;
  room_id: string;
  room_code: string;
  panel_id: string;
  panel_code: string;
  day_number: number;
  slot_index: number;
  start_time_str: string;
  end_time_str: string;
  status: string;
  audit_metadata?: InterviewAuditMetadata;
}

export interface ScheduleMetrics {
  total_interviews: number;
  scheduled_interviews: number;
  unscheduled_interviews: number;
  total_students: number;
  total_companies: number;
  total_rooms: number;
  total_panels: number;
  active_conflicts: number;
  schedule_stability: number;
  room_utilization_pct: number;
  panel_utilization_pct: number;
  avg_student_waiting_slots: number;
  bottleneck_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  solve_duration_seconds?: number;
  solver_status?: string;
}

export interface ScheduleVersion {
  schedule_version_id: string;
  version_number: number;
  stability_score: number;
  created_at: string;
  metrics: ScheduleMetrics;
  interviews: Interview[];
}

export interface BottleneckItem {
  time_window: string;
  entity_name: string;
  entity_type: string;
  utilization_pct: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reason: string;
  suggested_action: string;
}

export interface ResourceUtilizationItem {
  name: string;
  code: string;
  type: string;
  utilization_pct: number;
  total_slots: number;
  used_slots: number;
}

export interface AnalyticsDashboard {
  total_students: number;
  total_companies: number;
  total_rooms: number;
  total_panels: number;
  total_interviews: number;
  scheduled_interviews: number;
  unscheduled_interviews: number;
  active_conflicts_count: number;
  schedule_stability: number;
  current_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  bottleneck_risk_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  room_utilization_avg: number;
  panel_utilization_avg: number;
  room_utilization_pct?: number;
  panel_utilization_pct?: number;
  student_waiting_avg: number;
  bottlenecks: BottleneckItem[];
  top_utilized_rooms: ResourceUtilizationItem[];
  top_utilized_panels: ResourceUtilizationItem[];
  hourly_interview_density: Record<string, number>;
  company_load_distribution: Array<{
    company_name: string;
    company_code: string;
    interviews_count: number;
    tier: number;
  }>;
}

export interface DisruptionOut {
  id: string;
  schedule_id: string;
  event_type: string;
  target_entity_type: string;
  target_entity_id?: string;
  severity: string;
  status: string;
  parameters: Record<string, any>;
  created_at: string;
}

export interface ConflictItem {
  conflict_id: string;
  conflict_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  time_slot: string;
  day_number: number;
  student_code?: string;
  company_name?: string;
  room_code?: string;
  panel_code?: string;
  explanation: string;
  suggested_action: string;
}

export interface RecoveryStrategyOption {
  strategy_type: 'STUDENT_FIRST' | 'BALANCED' | 'STABILITY_FIRST';
  strategy_title: string;
  moved_interviews: number;
  unchanged_interviews: number;
  cancelled_interviews: number;
  new_assignments: number;
  scheduled_interviews?: number;
  unscheduled_interviews: number;
  stability_score: number;
  student_waiting_minutes?: number;
  waiting_time_level: string;
  room_utilization_pct: number;
  panel_utilization_pct: number;
  overall_score: number;
  is_recommended: boolean;
  explanation: string;
  candidate_interviews?: Interview[];
  diff?: ScheduleDiffItem[];
}

export interface ScheduleDiffItem {
  id?: string;
  student_id: string;
  student_code: string;
  student_name: string;
  company_name: string;
  change_type: 'UNCHANGED' | 'MOVED' | 'CANCELLED' | 'NEW';
  old_time?: string;
  new_time?: string;
  old_time_str?: string;
  new_time_str?: string;
  old_room?: string;
  new_room?: string;
  old_room_code?: string;
  new_room_code?: string;
  old_panel?: string;
  new_panel?: string;
  old_panel_code?: string;
  new_panel_code?: string;
  reason: string;
}

export interface ReplanningResult {
  replanning_run_id: string;
  disruption_id: string;
  source_version_id: string;
  resulting_version_id?: string;
  selected_strategy: string;
  strategies_comparison: RecoveryStrategyOption[];
  diff: ScheduleDiffItem[];
  strategy_diffs?: Record<string, ScheduleDiffItem[]>;
  stability_score: number;
  moved_count: number;
  unchanged_count: number;
  cancelled_count: number;
  metrics_after: ScheduleMetrics;
}

export interface AICopilotResponse {
  answer: string;
  insights: string[];
  relevant_metrics: Record<string, any>;
  suggested_followups: string[];
  data_grounding: Record<string, any>;
}

// Document Management Types
export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  document_type: string;
  detected_type?: string;
  confidence_score?: number;
  uploaded_by: string;
  version: number;
  status: string;
  record_count: number;
  valid_count: number;
  warning_count?: number;
  error_count: number;
  created_at: string;
}

export interface DocumentValidationError {
  row_number: number;
  column_name?: string;
  error_type: string;
  error_message: string;
  raw_value?: string;
  raw_row_data?: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  document_type: string;
  detected_type: string;
  confidence_score: number;
  version: number;
  record_count: number;
  valid_count: number;
  warning_count: number;
  error_count: number;
  status: string;
  columns: string[];
  preview: Record<string, any>[];
  errors?: DocumentValidationError[];
}

// Notification & Audit Types
export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: string;
  is_read: boolean;
  schedule_version_id?: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  user_id?: string;
  user_email?: string;
  user_role?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  before_state: Record<string, any>;
  after_state: Record<string, any>;
  reason?: string;
  trigger_event?: string;
  schedule_version_id?: string;
  details: Record<string, any>;
  created_at: string;
}
