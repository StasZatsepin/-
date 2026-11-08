// Подмена REST API для визуальной проверки без бэкенда.
// Данные повторяют демонстрационный товар «беспроводные наушники X-500».
// Используется scripts/visual_check.mjs при MOCK_API=1.

import { readFileSync } from 'node:fs'

const NOW = '2026-11-02T11:30:00Z'
const MIDNIGHT = '2026-03-15T00:00:00Z'

const workspace = { id: 'w1', name: 'Демонстрационное пространство', slug: 'demo', is_demo: true }
const user = {
  id: 'u1',
  email: 'demo@local.test',
  display_name: 'Демо-пользователь',
  role: 'owner',
  workspace,
}

const product = {
  id: 'p1',
  workspace_id: 'w1',
  name: 'ДЕМО: беспроводные наушники X-500',
  category: 'Электроника',
  marketplace: 'demo',
  sku: 'DEMO-X500',
  description:
    'Лёгкий и удобный: идеально подходит для ежедневных поездок и тренировок. Время работы без подзарядки — до 48 часов. Полностью безопасен для детей.',
  attributes: { 'Время работы': '30 часов', Масса: '250 г', Защита: 'IPX4' },
  is_demo: true,
  created_at: NOW,
  updated_at: NOW,
}

const productSummary = {
  id: 'p1',
  name: product.name,
  category: product.category,
  marketplace: 'demo',
  sku: product.sku,
  is_demo: true,
  created_at: NOW,
  updated_at: NOW,
  findings_total: 14,
  findings_open: 12,
  sources_total: 4,
  last_run_at: NOW,
  last_run_status: 'completed',
}

const src = (id, type, name, extra = {}) => ({
  id,
  product_id: 'p1',
  source_type: type,
  source_name: name,
  source_date: MIDNIGHT,
  source_uri: null,
  content_hash: id.padEnd(64, 'a'),
  extraction_method: 'rule_based',
  extraction_status: 'extracted',
  extraction_note: '',
  mime_type: 'text/plain',
  size_bytes: 2048,
  uploaded_at: NOW,
  metadata: { demo: true },
  text_preview: 'Время работы без подзарядки — 30 часов.',
  text_length: 400,
  ...extra,
})

const sources = [
  src('s1', 'technical_document', 'ДЕМО-СЕРТИФИКАТ № ДЕМО-СС-001'),
  src('s2', 'technical_document', 'ДЕМО-ПАСПОРТ ИЗДЕЛИЯ № ДЕМО-ПИ-002', { source_date: '2026-06-01T00:00:00Z' }),
  src('s3', 'review_export', 'ДЕМО-ВЫГРУЗКА ОТЗЫВОВ (синтетические отзывы)', { source_date: null }),
  src('s4', 'technical_document', 'ДЕМО-СКАН СЕРТИФИКАТА', {
    extraction_status: 'needs_ocr',
    extraction_note: 'Нужно распознавание текста.',
  }),
]

const claim = (id, text, type, status, extra = {}) => ({
  id,
  product_id: 'p1',
  source_id: 's1',
  source_name: 'ДЕМО-СЕРТИФИКАТ № ДЕМО-СС-001',
  text,
  claim_type: type,
  source_excerpt: text,
  extraction_method: 'rule_based',
  model_version: null,
  confidence_label: status,
  confidence_status: status,
  user_confirmed: false,
  is_rejected: false,
  numeric_value: null,
  numeric_unit: null,
  numeric_dimension: null,
  numeric_comparator: null,
  created_at: NOW,
  ...extra,
})

const claims = [
  claim('c1', 'Время работы без подзарядки — до 48 часов.', 'numeric_performance', 'needs_human_review', {
    numeric_value: 48,
    numeric_unit: 'h',
  }),
  claim('c2', 'Лёгкий и удобный: идеально подходит для ежедневных поездок и тренировок.', 'subjective_marketing', 'subjective_or_not_testable'),
  claim('c3', 'Полностью безопасен для детей.', 'safety_or_health', 'insufficient_evidence'),
]

const ref = (name, excerpt, relation) => ({
  source_id: 's1',
  source_name: name,
  excerpt,
  relation,
  evidence_type: 'document_statement',
  note: '',
})

const finding = (id, type, severity, title, description, rule, refs, status = 'open') => ({
  id,
  product_id: 'p1',
  claim_id: 'c1',
  analysis_run_id: 'r1',
  finding_type: type,
  severity,
  title,
  description,
  source_evidence_ids: [],
  source_refs: refs,
  limitations: 'Вывод сделан только по предоставленным материалам. Решение остаётся за человеком.',
  recommended_action: 'Проверить формулировку и при необходимости привести описание в соответствие с документами.',
  confidence_status: 'needs_human_review',
  status,
  rule_id: rule,
  rule_version: 'rules-2024.1',
  origin: 'rules',
  archived: false,
  explanation: '',
  explanation_provider: '',
  created_at: NOW,
  updated_at: NOW,
})

const findings = [
  finding(
    'f1',
    'direct_conflict',
    'high',
    'Время работы в описании не совпадает с таблицей характеристик',
    'В описании товара указано: «Время работы без подзарядки — до 48 часов».\nВ таблице характеристик: время работы = 30 часов.\nРасхождение: 18 часов.',
    'numeric.attribute_comparison',
    [
      ref('Описание товара', '\n\n        Время работы без подзарядки — до 48 часов.\n   ', 'contradicts'),
      ref('ДЕМО-СЕРТИФИКАТ № ДЕМО-СС-001', 'Время работы без подзарядки — 30 часов.', 'contradicts'),
    ],
  ),
  finding(
    'f2',
    'review_signal',
    'low',
    'Отзыв покупателя упоминает другое значение параметра',
    'В отзыве указано: «Батарея держится 20 часов, а не 48 как обещано в описании».\nВ описании товара: «Время работы без подзарядки — до 48 часов».',
    'reviews.numeric_mismatch',
    [ref('ДЕМО-ВЫГРУЗКА ОТЗЫВОВ (синтетические отзывы)', 'Батарея держится 20 часов, а не 48 как обещано в описании.', 'uncertain')],
  ),
  finding(
    'f3',
    'ambiguous_claim',
    'info',
    'Обещание сформулировано неопределённо',
    'В тексте найдена формулировка «идеально»: «Лёгкий и удобный: идеально подходит для ежедневных поездок и тренировок».\nТакое утверждение не имеет объективного критерия проверки, поэтому подтвердить или опровергнуть его по предоставленным данным нельзя.',
    'claims.ambiguous_promise',
    [ref('Описание товара', 'Лёгкий и удобный: идеально подходит для ежедневных поездок.', 'contextualizes')],
  ),
  finding(
    'f4',
    'missing_evidence',
    'medium',
    'Утверждение о безопасности требует проверки человеком',
    'В описании товара есть утверждение: «Полностью безопасен для детей».\nПодтверждающих документов по этому утверждению не предоставлено.',
    'evidence.missing_safety_confirmation',
    [],
    'in_review',
  ),
]

const run = {
  id: 'r1',
  product_id: 'p1',
  status: 'completed',
  engine_version: '1',
  rules_version: 'rules-2024.1',
  provider_name: 'mock',
  provider_status: 'ok',
  triggered_by: 'demo@local.test',
  started_at: NOW,
  finished_at: NOW,
  created_at: NOW,
  updated_at: NOW,
  summary: {},
  limitations: [],
  error_message: '',
}

const action = {
  id: 'a1',
  finding_id: 'f1',
  product_id: 'p1',
  user_id: 'u1',
  user_email: 'demo@local.test',
  action: 'status_change',
  previous_status: 'open',
  new_status: 'in_review',
  comment: 'Проверяю у поставщика',
  created_at: NOW,
}

const overview = {
  products_total: 1,
  findings_open: 12,
  findings_total: 14,
  sources_total: 4,
  reviews_total: 12,
  runs_total: 1,
  findings_by_severity: { high: 1, medium: 4, low: 5, info: 4 },
  findings_by_type: { direct_conflict: 1, missing_evidence: 3, review_signal: 5, ambiguous_claim: 4, needs_human_review: 1 },
  findings_by_status: { open: 12, in_review: 2 },
  recent_runs: [run],
  demo_products: 1,
}

const aiSettings = {
  provider: {
    name: 'mock',
    model: 'rules-2024.1',
    available: true,
    message: 'Работает без сети.',
    requires_api_key: false,
    external_data_transfer: false,
    fallback: 'mock',
  },
  available_providers: [
    { name: 'mock', label: 'Локальная эвристика', requires_api_key: false, hint: 'Работает без сети.' },
    { name: 'ollama', label: 'Ollama (локальные модели)', requires_api_key: false, hint: 'Нужен запущенный сервис Ollama.' },
  ],
  limits: {
    max_upload_bytes: 5242880,
    allowed_extensions: ['.txt', '.csv', '.pdf', '.docx', '.xlsx'],
    rules_version: 'rules-2024.1',
    demo_mode: true,
    store_original_files: false,
  },
  app: { name: 'Обещание против реальности', version: '0.1.0', environment: 'demo' },
}

const evidence = [
  {
    id: 'e1',
    product_id: 'p1',
    source_id: 's1',
    source_name: sources[0].source_name,
    claim_id: 'c1',
    evidence_type: 'document_statement',
    excerpt: 'Время работы без подзарядки — 30 часов.',
    relation: 'contradicts',
    relevance_note: '',
    date: MIDNIGHT,
    created_at: NOW,
  },
]

/**
 * Подключает подмену API к контексту браузера.
 * options.delay — задержка ответов в мс (для проверки состояний загрузки);
 * options.reportHtmlPath — файл с готовым HTML-отчётом.
 */
export async function installMockApi(context, options = {}) {
  const delay = options.delay ?? 0
  const reportHtml = options.reportHtmlPath
    ? readFileSync(options.reportHtmlPath, 'utf-8')
    : '<!doctype html><meta charset="utf-8"><body><p>Отчёт недоступен в подмене API.</p></body>'

  await context.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace(/^.*\/api\/v1/, '')
    const method = request.method()
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })

    if (delay && !path.startsWith('/auth')) await new Promise((resolve) => setTimeout(resolve, delay))

    if (path === '/auth/me') return json(user)
    if (path === '/auth/demo' && method === 'POST')
      return json({ access_token: 'mock-token', token_type: 'bearer', expires_in: 3600, user })
    if (path === '/overview') return json(overview)
    if (path === '/settings/ai') return json(aiSettings)
    if (path === '/products' && method === 'GET') return json([productSummary])
    if (path === '/products/p1' && method === 'GET') return json(product)
    if (path === '/products/p1/sources') return json(sources)
    if (path === '/products/p1/claims') return json(claims)
    if (path === '/products/p1/evidence') return json(evidence)
    if (path === '/products/p1/findings') return json(findings)
    if (path === '/products/p1/analysis-runs') return json([run])
    if (path === '/analysis-runs/r1')
      return json({ ...run, product_name: product.name, findings, claims_count: 3, sources_count: 4 })
    if (path === '/reviews/history') return json([action])
    if (path.startsWith('/findings/') && path.endsWith('/history')) return json([action])
    if (path.startsWith('/findings/')) return json(findings[0])
    if (path === '/products/p1/reports/r1')
      return route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: reportHtml })

    return json({ error: { code: 'NOT_FOUND', message: `Нет подмены для ${method} ${path}`, details: [] } }, 404)
  })
}
