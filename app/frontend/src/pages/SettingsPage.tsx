import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AiSettings } from '../api/types'
import { ErrorMessage, Skeleton } from '../components/States'
import { formatBytes } from '../components/labels'
import { useAuth } from '../context/AuthContext'

export function SettingsPage() {
  const { user } = useAuth()
  const [settings, setSettings] = useState<AiSettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [seedMessage, setSeedMessage] = useState<string | null>(null)
  const [seeding, setSeeding] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      setSettings(await api.aiSettings())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить настройки')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function seedDemo() {
    setSeeding(true)
    setSeedMessage(null)
    try {
      const response = await api.seedDemo()
      setSeedMessage(`${response.message} Товар: «${response.product_name}».`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать демо-товар')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Настройки</h1>
          <div className="topbar-subtitle">Состояние системы, провайдера анализа и ограничений</div>
        </div>
        <button type="button" className="btn" onClick={() => void load()}>
          Обновить
        </button>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}
        {seedMessage && <div className="alert alert-success">{seedMessage}</div>}

        {!settings && !error && (
          <div className="card">
            <Skeleton rows={4} />
          </div>
        )}

        {settings && (
          <>
            <div className="card">
              <div className="card-header">
                <div>
                  <h2>Рабочее пространство</h2>
                  <p>Все товары, источники и находки изолированы по рабочему пространству.</p>
                </div>
              </div>
              <dl className="kv-list">
                <dt>Название</dt>
                <dd>{user?.workspace?.name}</dd>
                <dt>Пользователь</dt>
                <dd>
                  {user?.display_name} ({user?.email})
                </dd>
                <dt>Роль</dt>
                <dd>{user?.role}</dd>
                <dt>Режим</dt>
                <dd>
                  {user?.workspace?.is_demo ? 'демонстрационный' : 'рабочий'}
                </dd>
              </dl>
            </div>

            <div className="card">
              <div className="card-header">
                <div>
                  <h2>Провайдер анализа</h2>
                  <p>Приложение полностью работоспособно без внешних сервисов и платных API.</p>
                </div>
              </div>
              <dl className="kv-list">
                <dt>Провайдер</dt>
                <dd>{settings.provider.name}</dd>
                <dt>Модель / версия</dt>
                <dd>{settings.provider.model || '—'}</dd>
                <dt>Состояние</dt>
                <dd>
                  <span className={`badge ${settings.provider.available ? 'badge-success' : 'badge-medium'}`}>
                    {settings.provider.available ? 'доступен' : 'недоступен'}
                  </span>
                </dd>
                <dt>Требуется API-ключ</dt>
                <dd>{settings.provider.requires_api_key ? 'да' : 'нет'}</dd>
                <dt>Передача данных наружу</dt>
                <dd>
                  {settings.provider.external_data_transfer
                    ? 'да — текст загруженных материалов будет передан внешнему сервису'
                    : 'нет — материалы не покидают компьютер'}
                </dd>
                <dt>Резервный режим</dt>
                <dd>{settings.provider.fallback}</dd>
                <dt>Сообщение</dt>
                <dd>{settings.provider.message}</dd>
              </dl>
            </div>

            <div className="card">
              <div className="card-header">
                <div>
                  <h2>Ограничения и версии</h2>
                  <p>Значения задаются в файле .env и не изменяются из интерфейса.</p>
                </div>
              </div>
              <dl className="kv-list">
                <dt>Версия правил</dt>
                <dd>{settings.limits.rules_version}</dd>
                <dt>Версия приложения</dt>
                <dd>
                  {settings.app.version} ({settings.app.environment})
                </dd>
                <dt>Максимальный размер файла</dt>
                <dd>{formatBytes(settings.limits.max_upload_bytes)}</dd>
                <dt>Допустимые форматы</dt>
                <dd className="mono">{settings.limits.allowed_extensions.join(', ')}</dd>
                <dt>Демо-режим</dt>
                <dd>{settings.limits.demo_mode ? 'включён' : 'выключен'}</dd>
              </dl>
            </div>

            <div className="card">
              <div className="card-header">
                <div>
                  <h2>Демонстрационные данные</h2>
                  <p>
                    Синтетический пример: вымышленный товар, документы и отзывы. Используется для
                    показа работы системы без доступа к реальным карточкам.
                  </p>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => void seedDemo()}
                  disabled={seeding}
                >
                  {seeding ? 'Создаём…' : 'Добавить демо-товар'}
                </button>
                <Link className="btn" to="/products">
                  Открыть список товаров
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
