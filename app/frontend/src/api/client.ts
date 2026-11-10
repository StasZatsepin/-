/** Клиент REST API: единая обработка ошибок и авторизации. */

import type {
  AiSettings,
  AnalysisRun,
  AnalysisRunDetail,
  ApiErrorBody,
  Claim,
  Evidence,
  Finding,
  FindingStatus,
  OverviewStats,
  Product,
  ProductSummary,
  ReviewAction,
  Source,
  TokenResponse,
  User,
} from './types'

const TOKEN_KEY = 'opr.token'

// В продакшене (Render Static Site) API может быть на другом домене.
// VITE_API_URL задаётся при сборке: например, https://backend.onrender.com/api
// В разработке Vite проксирует /api на localhost:8000.
const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const API_PREFIX = API_BASE_URL ? `${API_BASE_URL}/api/v1` : '/api/v1'

export class ApiError extends Error {
  code: string
  status: number
  details: Array<{ field?: string | null; message: string; type?: string }>

  constructor(status: number, code: string, message: string, details: ApiErrorBody['error']['details'] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  /** Человекочитаемый текст для показа пользователю. */
  get userMessage(): string {
    if (this.details.length > 0) {
      const detail = this.details
        .map((item) => (item.field ? `${item.field}: ${item.message}` : item.message))
        .join('; ')
      return `${this.message} (${detail})`
    }
    return this.message
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  isForm?: boolean
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  let body: BodyInit | undefined
  if (options.body !== undefined) {
    if (options.isForm) {
      body = options.body as BodyInit
    } else {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(options.body)
    }
  }

  let response: Response
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body,
    })
  } catch {
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      'Нет связи с сервером. Проверьте, запущен ли backend на порту 8000.',
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const errorBody = payload as ApiErrorBody | null
    throw new ApiError(
      response.status,
      errorBody?.error?.code ?? 'UNKNOWN_ERROR',
      errorBody?.error?.message ?? `Ошибка запроса (${response.status})`,
      errorBody?.error?.details ?? [],
    )
  }

  return payload as T
}

export const api = {
  quickCheck: (payload: import('./types').QuickCheckPayload) =>
    request<import('./types').QuickCheckResult>('/public/quick-check', { method: 'POST', body: payload }),
  // --- авторизация ---
  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body: { email, password } }),
  register: (email: string, password: string, displayName: string, workspaceName: string) =>
    request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: {
        email,
        password,
        display_name: displayName,
        workspace_name: workspaceName,
      },
    }),
  demoLogin: () => request<TokenResponse>('/auth/demo', { method: 'POST' }),
  me: () => request<User>('/auth/me'),

  // --- сводка и настройки ---
  overview: () => request<OverviewStats>('/overview'),
  aiSettings: () => request<AiSettings>('/settings/ai'),
  seedDemo: () => request<{ message: string; product_id: string; product_name: string }>('/demo/seed', {
    method: 'POST',
  }),

  // --- товары ---
  listProducts: (search = '') =>
    request<ProductSummary[]>(`/products${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  createProduct: (payload: Partial<Product>) =>
    request<Product>('/products', { method: 'POST', body: payload }),
  getProduct: (id: string) => request<Product>(`/products/${id}`),
  updateProduct: (id: string, payload: Partial<Product>) =>
    request<Product>(`/products/${id}`, { method: 'PATCH', body: payload }),
  deleteProduct: (id: string) => request<void>(`/products/${id}`, { method: 'DELETE' }),

  // --- источники ---
  listSources: (productId: string) => request<Source[]>(`/products/${productId}/sources`),
  uploadSource: (productId: string, file: File, form: Record<string, string> = {}) => {
    const data = new FormData()
    data.append('file', file)
    Object.entries(form).forEach(([key, value]) => {
      if (value) data.append(key, value)
    })
    return request<Source>(`/products/${productId}/sources`, { method: 'POST', body: data, isForm: true })
  },
  createManualSource: (
    productId: string,
    payload: {
      source_name: string
      source_type: string
      text: string
      source_date?: string | null
      applies_to_model?: string | null
      document_number?: string | null
      document_type?: string | null
      valid_until?: string | null
      scope_note?: string | null
    },
  ) => request<Source>(`/products/${productId}/sources/manual`, { method: 'POST', body: payload }),
  deleteSource: (id: string) => request<void>(`/sources/${id}`, { method: 'DELETE' }),

  // --- анализ ---
  runAnalysis: (productId: string) =>
    request<AnalysisRun>(`/products/${productId}/analysis-runs`, { method: 'POST' }),
  listRuns: (productId: string) => request<AnalysisRun[]>(`/products/${productId}/analysis-runs`),
  getRun: (runId: string) => request<AnalysisRunDetail>(`/analysis-runs/${runId}`),
  listClaims: (productId: string) => request<Claim[]>(`/products/${productId}/claims`),
  updateClaim: (
    claimId: string,
    payload: { text?: string; claim_type?: string; user_confirmed?: boolean; is_rejected?: boolean },
  ) => request<Claim>(`/claims/${claimId}`, { method: 'PATCH', body: payload }),
  createClaim: (productId: string, payload: { text: string; claim_type?: string }) =>
    request<Claim>(`/products/${productId}/claims`, { method: 'POST', body: payload }),
  deleteClaim: (claimId: string) => request<void>(`/claims/${claimId}`, { method: 'DELETE' }),
  listEvidence: (productId: string) => request<Evidence[]>(`/products/${productId}/evidence`),

  // --- находки ---
  listFindings: (productId: string, params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params).toString()
    return request<Finding[]>(`/products/${productId}/findings${query ? `?${query}` : ''}`)
  },
  getFinding: (id: string) => request<Finding>(`/findings/${id}`),
  updateFinding: (id: string, payload: { status?: FindingStatus; comment?: string }) =>
    request<Finding>(`/findings/${id}`, { method: 'PATCH', body: payload }),
  findingHistory: (id: string) => request<ReviewAction[]>(`/findings/${id}/history`),
  workspaceHistory: (limit = 100) => request<ReviewAction[]>(`/reviews/history?limit=${limit}`),

  // --- отчёты ---
  reportUrl: (productId: string, runId: string) =>
    `${API_PREFIX}/products/${productId}/reports/${runId}`,
}

export async function fetchReportHtml(productId: string, runId: string): Promise<string> {
  const token = getToken()
  const response = await fetch(api.reportUrl(productId, runId), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new ApiError(response.status, 'REPORT_ERROR', 'Не удалось загрузить отчёт.')
  }
  return response.text()
}
