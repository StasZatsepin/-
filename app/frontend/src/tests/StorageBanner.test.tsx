import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { StorageBanner } from '../components/StorageBanner'
import { api } from '../api/client'

function mockSettings(store: boolean) {
  vi.spyOn(api, 'aiSettings').mockResolvedValue({
    limits: { store_original_files: store },
  } as never)
}

afterEach(() => {
  vi.restoreAllMocks()
  window.localStorage.clear()
})

describe('Баннер хранения файлов', () => {
  it('показывается, когда оригиналы не сохраняются, и закрывается', async () => {
    mockSettings(false)
    render(<StorageBanner />)
    expect(await screen.findByText(/Исходные файлы не сохраняются/)).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Скрыть уведомление'))
    await waitFor(() => expect(screen.queryByText(/Исходные файлы не сохраняются/)).toBeNull())
    expect(window.localStorage.getItem('rr.storageBannerDismissed')).toBe('1')
  })

  it('не показывается, когда файлы хранятся', async () => {
    mockSettings(true)
    render(<StorageBanner />)
    await waitFor(() => expect(api.aiSettings).toHaveBeenCalled())
    expect(screen.queryByText(/Исходные файлы не сохраняются/)).toBeNull()
  })
})
