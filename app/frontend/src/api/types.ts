/** Типы данных, которые возвращает REST API. */

export type Marketplace = 'ozon' | 'wildberries' | 'demo' | 'other'

export type FindingType =
  | 'direct_conflict'
  | 'missing_evidence'
  | 'review_signal'
  | 'ambiguous_claim'
  | 'document_scope_mismatch'
  | 'needs_human_review'

export type Severity = 'info' | 'low' | 'medium' | 'high'

export type FindingStatus =
  | 'open'
  | 'in_review'
  | 'resolved'
  | 'not_an_issue'
  | 'insufficient_data'

export interface Workspace {
  id: string
  name: string
  slug: string
  is_demo: boolean
}

export interface User {
  id: string
  email: string
  display_name: string
  role: string
  workspace: Workspace
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Product {
  id: string
  workspace_id: string
  name: string
  category: string
  marketplace: string
  sku: string
  description: string
  attributes: Record<string, unknown>
  is_demo: boolean
  created_at: string
  updated_at: string
}

export interface ProductSummary {
  id: string
  name: string
  category: string
  marketplace: string
  sku: string
  is_demo: boolean
  created_at: string
  updated_at: string
  findings_total: number
  findings_open: number
  sources_total: number
  last_run_at: string | null
  last_run_status: string | null
}

export interface Source {
  id: string
  product_id: string
  source_type: string
  source_name: string
  source_date: string | null
  source_uri: string | null
  content_hash: string
  extraction_method: string
  extraction_status: string
  extraction_note: string
  mime_type: string | null
  size_bytes: number
  uploaded_at: string
  metadata: Record<string, unknown>
  text_preview: string
  text_length: number
}

export interface Claim {
  id: string
  product_id: string
  source_id: string | null
  source_name: string | null
  text: string
  claim_type: string
  source_excerpt: string
  extraction_method: string
  model_version: string | null
  confidence_label: string | null
  confidence_status: string
  user_confirmed: boolean
  is_rejected: boolean
  numeric_value: number | null
  numeric_unit: string | null
  numeric_dimension: string | null
  numeric_comparator: string | null
  created_at: string
}

export interface Evidence {
  id: string
  product_id: string
  source_id: string | null
  source_name: string | null
  claim_id: string | null
  evidence_type: string
  excerpt: string
  relation: string
  relevance_note: string
  date: string | null
  created_at: string
}

export interface SourceRef {
  source_id: string | null
  source_name: string
  excerpt: string
  relation: string
  evidence_type: string
  note: string
}

export interface Finding {
  id: string
  product_id: string
  claim_id: string | null
  analysis_run_id: string | null
  finding_type: FindingType
  severity: Severity
  title: string
  description: string
  source_evidence_ids: string[]
  source_refs: SourceRef[]
  limitations: string
  recommended_action: string
  confidence_status: string
  status: FindingStatus
  rule_id: string
  rule_version: string
  origin: string
  archived: boolean
  explanation: string
  explanation_provider: string
  suggestion?: { text: string; copy_text?: string } | null
  created_at: string
  updated_at: string
}

export interface QuickCheckPayload {
  description: string
  name?: string
  attributes_text: string
  document_text?: string
  reviews_text?: string
}

export interface QuickFinding {
  finding_type: FindingType
  severity: Severity
  title: string
  description: string
  source_refs: SourceRef[]
  limitations: string
  recommended_action: string
  rule_id: string
  suggestion?: { text: string; copy_text?: string } | null
}

export interface QuickCheckResult {
  findings: QuickFinding[]
  total: number
  by_severity: Record<string, number>
  claims_count: number
  note: string
}

export interface ReviewAction {
  id: string
  finding_id: string
  product_id: string
  user_id: string | null
  user_email: string
  action: string
  previous_status: string | null
  new_status: string | null
  comment: string
  created_at: string
}

export interface AnalysisRun {
  id: string
  product_id: string
  status: string
  engine_version: string
  rules_version: string
  provider_name: string
  provider_status: string
  triggered_by: string
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
  summary: Record<string, unknown>
  limitations: string[]
  error_message: string
}

export interface AnalysisRunDetail extends AnalysisRun {
  product_name: string
  findings: Finding[]
  claims_count: number
  sources_count: number
}

export interface OverviewStats {
  products_total: number
  findings_open: number
  findings_total: number
  sources_total: number
  reviews_total: number
  runs_total: number
  findings_by_severity: Record<string, number>
  findings_by_type: Record<string, number>
  findings_by_status: Record<string, number>
  recent_runs: AnalysisRun[]
  demo_products: number
}

export interface AiSettings {
  provider: {
    name: string
    model: string
    available: boolean
    message: string
    requires_api_key: boolean
    external_data_transfer: boolean
    fallback: string
  }
  available_providers: Array<{
    name: string
    label: string
    requires_api_key: boolean
    hint: string
  }>
  limits: {
    max_upload_bytes: number
    allowed_extensions: string[]
    rules_version: string
    demo_mode: boolean
    store_original_files?: boolean
  }
  app: {
    name: string
    version: string
    environment: string
  }
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: Array<{ field?: string | null; message: string; type?: string }>
  }
}
