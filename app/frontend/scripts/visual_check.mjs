// Автопроверка вёрстки: скриншоты + поиск типичных дефектов (Playwright, Chromium).
//
// Запуск (dev-сервер уже работает на BASE_URL):
//   MOCK_API=1 node scripts/visual_check.mjs        — без бэкенда, на подменённых данных
//   node scripts/visual_check.mjs                   — против настоящего API (нужен demo-вход)
//
// Переменные: BASE_URL (по умолчанию http://127.0.0.1:5173), WIDTHS="360,390,768,1280",
// ONLY="/app,/app/products" (фильтр страниц), MOCK_REPORT_HTML (HTML отчёта для подмены),
// OUT_DIR (по умолчанию artifacts/screens). Код возврата 1, если найдены проблемы.

import { createRequire } from 'node:module'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { installMockApi } from './mock-api.mjs'

const require = createRequire(import.meta.url)
let chromium
try {
  ;({ chromium } = require('playwright'))
} catch {
  ;({ chromium } = await import('playwright'))
}

const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const WIDTHS = (process.env.WIDTHS ?? '360,390,768,1280').split(',').map(Number)
const OUT_DIR = process.env.OUT_DIR ?? 'artifacts/screens'
const MOCK = process.env.MOCK_API === '1'
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null

const PAGES = [
  { name: 'landing', url: '/', public: true },
  { name: 'login', url: '/login', public: true },
  { name: 'overview', url: '/app' },
  { name: 'products', url: '/app/products' },
  { name: 'product-new', url: '/app/products/new' },
  { name: 'product-card', url: '/app/products/p1' },
  { name: 'product-sources', url: '/app/products/p1', tab: 'Источники' },
  { name: 'product-claims', url: '/app/products/p1', tab: 'Утверждения' },
  { name: 'product-findings', url: '/app/products/p1', tab: 'Результаты' },
  { name: 'product-evidence', url: '/app/products/p1', tab: 'Доказательства' },
  { name: 'product-runs', url: '/app/products/p1', tab: 'Запуски' },
  { name: 'checks', url: '/app/checks' },
  { name: 'history', url: '/app/history' },
  { name: 'settings', url: '/app/settings' },
  { name: 'report', url: '/app/products/p1/report/r1', report: true },
  { name: 'loading-product', url: '/app/products/p1', slow: 1500, shotAfterMs: 400 },
]

const RAW_CODE_SOURCE = '\\b(?:technical_document|review_export|needs_human_review|needs_ocr|contextualizes|uncertain|contradicts|unrelated|supported_by_provided_source|conflicting_sources|insufficient_evidence|subjective_or_not_testable|direct_conflict|missing_evidence|review_signal|ambiguous_claim|document_scope_mismatch|rule_based|mock_provider|[a-z]+\\.[a-z]+_[a-z_]+)\\b'

/** Проверки выполняются внутри страницы (или iframe-фрейма отчёта). */
function inPageChecks({ width, scrollY, rawSource, overlapMode }) {
  const problems = []
  const doc = document
  const view = doc.defaultView
  const label = (el) => {
    const id = el.id ? `#${el.id}` : ''
    const cls = typeof el.className === 'string' && el.className ? `.${el.className.trim().split(/\s+/).slice(0, 2).join('.')}` : ''
    return `${el.tagName.toLowerCase()}${id}${cls}`
  }
  const visible = (el) => {
    const style = view.getComputedStyle(el)
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return false
    const rect = el.getBoundingClientRect()
    return rect.width > 0 && rect.height > 0
  }
  const ownText = (el) =>
    Array.from(el.childNodes)
      .filter((node) => node.nodeType === 3)
      .map((node) => node.textContent.trim())
      .join(' ')
      .trim()

  // 1. Горизонтальная прокрутка страницы
  if (doc.documentElement.scrollWidth > view.innerWidth + 1) {
    problems.push({ kind: 'hscroll', where: 'html', note: `scrollWidth ${doc.documentElement.scrollWidth} > ${view.innerWidth}` })
  }

  const all = Array.from(doc.body.querySelectorAll('*')).filter(visible)

  // 2. Обрезанный текст
  for (const el of all) {
    const text = ownText(el)
    if (!text) continue
    if (el.closest('[data-truncate]')) continue
    const style = view.getComputedStyle(el)
    if (['hidden', 'clip'].includes(style.overflowX) && el.scrollWidth > el.clientWidth + 1) {
      problems.push({ kind: 'clipped', where: label(el), note: `«${text.slice(0, 40)}» шире своей области (${el.scrollWidth}>${el.clientWidth})` })
      continue
    }
    const rect = el.getBoundingClientRect()
    for (let anc = el.parentElement; anc && anc !== doc.body; anc = anc.parentElement) {
      const ancStyle = view.getComputedStyle(anc)
      if (['auto', 'scroll'].includes(ancStyle.overflowX)) break // осознанная прокрутка
      if (['hidden', 'clip'].includes(ancStyle.overflowX)) {
        const box = anc.getBoundingClientRect()
        if (box.width <= 2 || box.height <= 2) break // визуально скрытый элемент (для скринридеров)
        if (rect.left < box.left - 1 || rect.right > box.right + 1) {
          problems.push({ kind: 'clipped', where: label(el), note: `«${text.slice(0, 40)}» выходит за ${label(anc)}` })
        }
        break
      }
    }
  }

  // 3. Наложения: fixed/sticky элементы поверх текста
  const floating = all.filter((el) => ['fixed', 'sticky'].includes(view.getComputedStyle(el).position))
  for (const fl of floating) {
    const flHead = fl.closest('thead')
    if (flHead) { const hr = flHead.getBoundingClientRect(); if (hr.width <= 2 || hr.height <= 2) continue }
    const box = fl.getBoundingClientRect()
    if (box.width < 4 || box.height < 4) continue
    // «bottom»: после прокрутки в конец проверяем только панели, прижатые к низу экрана
    if (overlapMode === 'bottom' && box.top < view.innerHeight / 2) continue
    for (const el of all) {
      if (!ownText(el)) continue
      if (fl.contains(el) || el.contains(fl)) continue
      if (floating.some((other) => other !== fl && other.contains(el))) continue
      const rect = el.getBoundingClientRect()
      if (rect.width <= 2 || rect.height <= 2) continue // визуально скрытые элементы
      const hiddenHead = el.closest('thead')
      if (hiddenHead) { const hr = hiddenHead.getBoundingClientRect(); if (hr.width <= 2 || hr.height <= 2) continue }
      const overlapW = Math.min(box.right, rect.right) - Math.max(box.left, rect.left)
      const overlapH = Math.min(box.bottom, rect.bottom) - Math.max(box.top, rect.top)
      if (overlapW > 4 && overlapH > 4 && rect.bottom > 0 && rect.top < view.innerHeight) {
        // элемент под панелью, но панель сама по себе фон-подложка — допустимо только для backdrop
        if (fl.classList.contains('sidebar-backdrop')) continue
        // нижняя навигация закрывает контент, пока страница не прокручена до конца: в режиме rest это нормально
        if (fl.classList.contains('bottom-nav') && overlapMode === 'rest') continue
        // открытый мобильный sidebar перекрывает контент намеренно (overlay)
        if (fl.classList.contains('sidebar') && fl.classList.contains('is-open')) continue
        problems.push({ kind: 'overlap', where: label(fl), note: `перекрывает «${ownText(el).slice(0, 40)}» (${label(el)})` })
        break
      }
    }
  }

  // 4. Цели касания на узких экранах
  if (width <= 480) {
    const targets = all.filter((el) => el.matches('button, a[href], input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea, [role=tab], [role=button]'))
    for (const el of targets) {
      const style = view.getComputedStyle(el)
      if (style.display === 'inline' && el.tagName === 'A') continue // ссылка внутри текста
      const rect = el.getBoundingClientRect()
      if (rect.width < 40 || rect.height < 40) {
        problems.push({ kind: 'tap-target', where: label(el), note: `${Math.round(rect.width)}×${Math.round(rect.height)} px: «${(el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 30)}»` })
      }
    }
  }

  // 5. Сырые коды и разделитель « · » в видимом тексте
  const text = (doc.body.innerText || '').replace(/ /g, ' ')
  const raw = text.match(new RegExp(rawSource, 'g'))
  if (raw) problems.push({ kind: 'raw-code', where: 'text', note: [...new Set(raw)].join(', ') })
  if (text.includes(' · ')) problems.push({ kind: 'dot-separator', where: 'text', note: 'найден « · » в видимом тексте' })

  return problems.map((problem) => ({ ...problem, scrollY }))
}

async function runChecks(target, width) {
  const first = await target.evaluate(inPageChecks, { width, scrollY: 0, rawSource: RAW_CODE_SOURCE, overlapMode: 'rest' })
  await target.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  const second = await target.evaluate(inPageChecks, { width, scrollY: -1, rawSource: RAW_CODE_SOURCE, overlapMode: 'bottom' })
  await target.evaluate(() => window.scrollTo(0, 0))
  // после прокрутки в конец интересуют только наложения нижних панелей на последний контент
  return [...first, ...second.filter((item) => item.kind === 'overlap')]
}

const browser = await chromium.launch()
const failures = []
let shots = 0

for (const width of WIDTHS) {
  const mobile = width <= 768
  const context = await browser.newContext({
    viewport: { width, height: mobile ? 800 : 900 },
    isMobile: width <= 480,
    hasTouch: mobile,
    deviceScaleFactor: 1,
    locale: 'ru-RU',
  })
  await context.addInitScript(() => {
    try {
      localStorage.setItem('opr.token', 'mock-token')
      localStorage.setItem('opr.mode-banner-dismissed', '0')
    } catch {
      /* без хранилища страница должна работать */
    }
  })

  for (const spec of PAGES) {
    if (ONLY && !ONLY.includes(spec.url) && !ONLY.includes(spec.name)) continue
    if (MOCK) await installMockApi(context, { delay: spec.slow ?? 0, reportHtmlPath: process.env.MOCK_REPORT_HTML })
    const page = await context.newPage()
    const consoleErrors = []
    page.on('pageerror', (error) => consoleErrors.push(error.message))
    try {
      await page.goto(BASE_URL + spec.url, { waitUntil: 'domcontentloaded' })
      if (spec.shotAfterMs) await page.waitForTimeout(spec.shotAfterMs)
      else await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
      if (spec.tab) {
        await page.getByRole('button', { name: spec.tab, exact: true }).click()
        await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {})
      }
      await page.waitForTimeout(spec.shotAfterMs ? 0 : 350)

      const dir = path.join(OUT_DIR, String(width))
      mkdirSync(dir, { recursive: true })
      await page.screenshot({ path: path.join(dir, `${spec.name}.png`), fullPage: true })
      shots += 1

      if (!spec.slow) {
        const problems = await runChecks(page, width)
        if (spec.report) {
          const frame = page.frames().find((candidate) => candidate !== page.mainFrame())
          if (frame) {
            const inner = await frame.evaluate(inPageChecks, { width, scrollY: 0, rawSource: RAW_CODE_SOURCE, overlapMode: 'rest' })
            problems.push(...inner.map((item) => ({ ...item, where: `iframe: ${item.where}` })))
          }
        }
        for (const problem of problems) failures.push({ page: spec.name, width, ...problem })
      }
      if (consoleErrors.length) failures.push({ page: spec.name, width, kind: 'js-error', where: 'page', note: consoleErrors[0].slice(0, 120) })

      // состояние: открытое мобильное меню
      if (spec.name === 'overview' && width <= 960) {
        const toggle = page.locator('.mobile-nav-toggle')
        if (await toggle.count()) {
          await toggle.first().click()
          await page.waitForTimeout(350)
          await page.screenshot({ path: path.join(dir, 'menu-open.png'), fullPage: false })
          shots += 1
          const menuProblems = await page.evaluate(inPageChecks, { width, scrollY: 0, rawSource: RAW_CODE_SOURCE, overlapMode: 'rest' })
          for (const problem of menuProblems.filter((item) => item.kind !== 'hscroll'))
            failures.push({ page: 'menu-open', width, ...problem })
        }
      }
    } catch (error) {
      failures.push({ page: spec.name, width, kind: 'script-error', where: 'playwright', note: String(error.message).split('\n')[0].slice(0, 160) })
    } finally {
      await page.close()
      if (MOCK) await context.unroute('**/api/v1/**').catch(() => {})
    }
  }
  await context.close()
}
await browser.close()

// Сводка: одинаковые проблемы сворачиваем
const seen = new Set()
const unique = failures.filter((item) => {
  const key = `${item.page}|${item.width}|${item.kind}|${item.where}|${item.note}`
  if (seen.has(key)) return false
  seen.add(key)
  return true
})
const lines = unique.map((item) => `${String(item.width).padStart(4)}px  ${item.page.padEnd(17)} ${item.kind.padEnd(14)} ${item.where} — ${item.note}`)
const summary = `Скриншотов: ${shots}. Проблем: ${unique.length}.`
mkdirSync(OUT_DIR, { recursive: true })
writeFileSync(path.join(OUT_DIR, 'report.txt'), [summary, ...lines].join('\n'), 'utf-8')
console.log(lines.join('\n'))
console.log(summary)
process.exit(unique.length ? 1 : 0)
