import { describe, expect, it, vi, beforeEach } from 'vitest'
import { ApiError, api, getToken, setToken } from '../api/client'

describe('Клиент API', () => {
  beforeEach(() => {
    setToken(null)
  })

  it('сохраняет и читает токен', () => {
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken(null)
    expect(getToken()).toBeNull()
  })

  it('формирует понятное сообщение об ошибке валидации', () => {
    const error = new ApiError(422, 'VALIDATION_ERROR', 'Проверьте заполненные поля', [
      { field: 'name', message: 'Название товара обязательно' },
    ])
    expect(error.userMessage).toContain('Проверьте заполненные поля')
    expect(error.userMessage).toContain('Название товара обязательно')
  })

  it('преобразует ответ API с ошибкой в ApiError', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            error: {
              code: 'NOT_FOUND',
              message: 'Товар не найден.',
              details: [],
            },
          }),
          { status: 404, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.getProduct('missing')).rejects.toBeInstanceOf(ApiError)
    await expect(api.getProduct('missing')).rejects.toMatchObject({
      code: 'NOT_FOUND',
      status: 404,
    })
  })

  it('сообщает о недоступности сервера', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await expect(api.listProducts()).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })

  it('добавляет заголовок авторизации, если токен есть', async () => {
    setToken('test-token')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.listProducts()
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer test-token')
  })

  it('не добавляет заголовок авторизации без токена', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.listProducts()
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBeUndefined()
  })
})
