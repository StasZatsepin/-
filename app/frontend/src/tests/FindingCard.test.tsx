import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { FindingCard } from '../components/FindingCard'
import type { Finding } from '../api/types'

const finding: Finding = {
  id: 'finding-1',
  product_id: 'product-1',
  claim_id: 'claim-1',
  analysis_run_id: 'run-1',
  finding_type: 'direct_conflict',
  severity: 'medium',
  title: 'Числовое расхождение между описанием и характеристиками',
  description: 'В описании указано 48 часов, в характеристиках — 30 часов.',
  source_evidence_ids: ['evidence-1'],
  source_refs: [
    {
      source_id: 'source-1',
      source_name: 'Описание товара',
      excerpt: 'До 48 часов работы без подзарядки.',
      relation: 'contradicts',
      evidence_type: 'description_text',
      note: '',
    },
    {
      source_id: 'source-2',
      source_name: 'Таблица характеристик',
      excerpt: 'battery_life_hours: 30',
      relation: 'contradicts',
      evidence_type: 'attribute_value',
      note: 'Значение расходится с таблицей характеристик.',
    },
  ],
  limitations: 'Условия измерения не указаны.',
  recommended_action: 'Привести описание в соответствие с характеристиками.',
  confidence_status: 'conflicting_sources',
  status: 'open',
  rule_id: 'numeric.attribute_comparison',
  rule_version: 'rules-2024.1',
  origin: 'rules',
  archived: false,
  created_at: '2026-01-01T10:00:00Z',
  updated_at: '2026-01-01T10:00:00Z',
}

describe('Карточка результата проверки', () => {
  it('показывает объяснение, основание, ограничение и рекомендацию', () => {
    render(
      <MemoryRouter>
        <FindingCard finding={finding} />
      </MemoryRouter>,
    )

    expect(screen.getByText(finding.title)).toBeInTheDocument()
    expect(screen.getByText(/В описании указано 48 часов/)).toBeInTheDocument()

    // Основание вывода с фрагментом и источником
    expect(screen.getByText('Основание вывода')).toBeInTheDocument()
    expect(screen.getByText('До 48 часов работы без подзарядки.')).toBeInTheDocument()
    expect(screen.getByText('battery_life_hours: 30')).toBeInTheDocument()
    expect(screen.getByText('Описание товара')).toBeInTheDocument()

    // Ограничение и рекомендация
    expect(screen.getByText('Ограничение вывода')).toBeInTheDocument()
    expect(screen.getByText(/Условия измерения не указаны/)).toBeInTheDocument()
    expect(screen.getByText('Рекомендуемое действие')).toBeInTheDocument()
    expect(screen.getByText(/Привести описание в соответствие/)).toBeInTheDocument()
  })

  it('подписывает тип сигнала, серьёзность и статус', () => {
    render(
      <MemoryRouter>
        <FindingCard finding={finding} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Прямое расхождение')).toBeInTheDocument()
    expect(screen.getByText('Средняя')).toBeInTheDocument()
    // Статус отображается и значком, и в списке выбора.
    expect(screen.getAllByText('Открыта').length).toBeGreaterThan(0)
  })

  it('позволяет выбрать другой статус рассмотрения', () => {
    render(
      <MemoryRouter>
        <FindingCard finding={finding} />
      </MemoryRouter>,
    )

    const select = screen.getByLabelText('Статус рассмотрения') as HTMLSelectElement
    expect(select.value).toBe('open')
    expect(screen.getByRole('option', { name: 'Решена' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Недостаточно данных' })).toBeInTheDocument()
  })

  it('не содержит обвинительных формулировок', () => {
    render(
      <MemoryRouter>
        <FindingCard finding={finding} />
      </MemoryRouter>,
    )

    const text = document.body.textContent?.toLowerCase() ?? ''
    expect(text).not.toContain('мошенник')
    expect(text).not.toContain('недобросовестн')
    expect(text).not.toContain('подделк')
  })
})
