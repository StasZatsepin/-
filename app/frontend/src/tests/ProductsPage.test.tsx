import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProductsPage } from '../pages/ProductsPage'
import { api } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: {
      listProducts: vi.fn(),
      deleteProduct: vi.fn(),
    },
  }
})

const product = {
  id: 'product-1',
  name: 'Беспроводные наушники X-500',
  category: 'электроника',
  marketplace: 'ozon',
  sku: 'SKU-1',
  is_demo: false,
  created_at: '2026-01-01T10:00:00Z',
  updated_at: '2026-01-02T10:00:00Z',
  findings_total: 4,
  findings_open: 2,
  sources_total: 3,
  last_run_at: '2026-01-02T12:00:00Z',
  last_run_status: 'completed',
}

describe('Список товаров', () => {
  it('показывает товары рабочего пространства', async () => {
    vi.mocked(api.listProducts).mockResolvedValue([product])

    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Беспроводные наушники X-500')).toBeInTheDocument()
    expect(screen.getByText(/2 открыто/)).toBeInTheDocument()
    expect(screen.getByText('Ozon')).toBeInTheDocument()
  })

  it('показывает пустое состояние, когда товаров нет', async () => {
    vi.mocked(api.listProducts).mockResolvedValue([])

    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Товаров пока нет')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Создать товар' })).toBeInTheDocument()
  })

  it('сообщает об ошибке загрузки', async () => {
    vi.mocked(api.listProducts).mockRejectedValue(new Error('Сервер недоступен'))

    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/Сервер недоступен/)).toBeInTheDocument()
    })
  })
})
