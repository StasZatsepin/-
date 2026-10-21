import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LandingPage } from '../pages/LandingPage'

describe('Публичная главная страница', () => {
  it('показывает основной заголовок и призыв к действию', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Обещания товара. Проверка фактами.',
    )
    expect(screen.getAllByRole('link', { name: /Попробовать демо/ }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: /Как это работает/ }).length).toBeGreaterThan(0)
  })

  it('объясняет назначение продукта', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByText(/Сопоставляйте заявления продавцов с характеристиками/),
    ).toBeInTheDocument()
  })

  it('показывает четыре шага работы системы', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Четыре шага от карточки до отчёта')).toBeInTheDocument()
    expect(screen.getByText('Добавьте товар и материалы')).toBeInTheDocument()
    expect(screen.getByText('Система извлечёт утверждения')).toBeInTheDocument()
    expect(screen.getByText('Изучите сигналы и доказательства')).toBeInTheDocument()
    expect(screen.getByText('Примите решение и сохраните отчёт')).toBeInTheDocument()
  })

  it('объявляет принципы достоверности', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Правила, которые нельзя нарушить')).toBeInTheDocument()
    expect(screen.getByText(/Нет подтверждения ≠ утверждение ложно/)).toBeInTheDocument()
  })

  it('помечает демонстрационные данные как синтетические', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByText(/синтетических данных/i)).toBeInTheDocument()
    expect(screen.getByText('ДЕМО')).toBeInTheDocument()
  })

  it('не обещает несуществующие метрики и отзывы', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    const text = document.body.textContent ?? ''
    expect(text).not.toMatch(/\d+\s*%\s*точн/i)
    expect(text).not.toMatch(/\d+\s*(тыс\.|млн)/i)
    expect(text).not.toMatch(/насчитыва|довольн(ы|ых) клиент/i)
  })
})
