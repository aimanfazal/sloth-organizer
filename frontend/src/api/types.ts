// ---------------------------------------------------------------------------
// LM Studio
// ---------------------------------------------------------------------------

export interface LmStudioStatus {
  connected: boolean;
  model: string | null;
}

// ---------------------------------------------------------------------------
// Scan
// ---------------------------------------------------------------------------

export interface ScanResponse {
  scan_id: string;
  file_count: number;
  duplicate_groups: number;
}

export interface ScanStatus {
  scan_id: string;
  folder_path: string;
  status: 'scanning' | 'complete' | 'error';
  file_count: number;
  folder_count: number;
  duplicate_groups: number;
  total_size_bytes: number;
  created_at: string;
}

export interface ScannedFile {
  id: string;
  scan_id: string;
  filename: string;
  relative_path: string;
  extension: string;
  size_bytes: number;
  mime_type: string;
  sha256: string;
  content_preview: string | null;
  is_duplicate: boolean;
}

// ---------------------------------------------------------------------------
// WebSocket messages
// ---------------------------------------------------------------------------

export interface WsProgressMessage {
  type: 'progress';
  percent: number;
  stage: string;
}

export interface WsCompleteMessage {
  type: 'complete';
  summary: {
    file_count: number;
    folder_count: number;
    duplicate_groups: number;
    total_size_bytes: number;
  };
}

export interface WsErrorMessage {
  type: 'error';
  detail: string;
}

export type WsMessage = WsProgressMessage | WsCompleteMessage | WsErrorMessage;

// ---------------------------------------------------------------------------
// Plan
// ---------------------------------------------------------------------------

export interface PlanItem {
  id: string;
  plan_id: string;
  file_id: string;
  source_path: string;
  destination: string;
  new_name: string | null;
  reason: string;
  task: string | null;
  priority: 'high' | 'medium' | 'low' | null;
  confidence: number;
  approved: boolean | null;
  applied: boolean;
}

export interface PlanResponse {
  plan_id: string;
  scan_id: string;
  summary: string;
  folders: string[];
  items: PlanItem[];
}

export interface PlanDetail extends PlanResponse {
  status: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Apply
// ---------------------------------------------------------------------------

export interface ApplyRequest {
  approved_items: string[];
  dry_run: boolean;
}

export interface ApplyResponse {
  moved: number;
  renamed: number;
  skipped: number;
  errors: { item_id: string; detail: string }[];
  dry_run: boolean;
}
