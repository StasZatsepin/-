import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AiSettings } from '../api/types'
import { ErrorMessage, Skeleton } from '../components/States'
import { formatBytes, PROVIDER_LABELS, labelOf } from '../components/labels'
import { IconInfo, IconProducts, IconQuote, IconShield, IconSpark } from '../components/icons'
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
        <div className="topbar-titles">
          <h1>Настройки</h1>
          <div className="topbar-subtitle">Состояние системы, провайдера анализа и ограничений</div>
        </div>
        <div className="topbar-actions">
          <button type="button" className="btn" onClick={() => void load()}>
            Обновить
          </button>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}
        {seedMessage && (
          <div className="alert alert-success">
            <span className="alert-icon">
              <IconInfo size={16} />
            </span>
            <div>{seedMessage}</div>
          </div>
        )}

        {!settings && !error && (
          <div className="panel">
            <div className="panel-body">
              <Skeleton rows={4} />
            </div>
          </div>
        )}

        {settings && (
          <div className="stack">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Рабочее пространство</h2>
                  <p>Все товары, источники и результаты изолированы по рабочему пространству</p>
                </div>
              </div>
              <div className="panel-body">
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
                    <span className="badge badge-neutral">
                      {user?.workspace?.is_demo ? 'демонстрационный' : 'рабочий'}
                    </span>
                  </dd>
                </dl>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Провайдер анализа</h2>
                  <p>Приложение полностью работоспособно без внешних сервисов и платных API</p>
                </div>
              </div>
              <div className="panel-body">
                <dl className="kv-list">
                  <dt>Провайдер</dt>
                  <dd>{labelOf(PROVIDER_LABELS, settings.provider.name)}</dd>
                  <dt>Модель / версия</dt>
                  <dd>{settings.provider.model || '—'}</dd>
                  <dt>Состояние</dt>
                  <dd>
                    <span
                      className={`badge ${settings.provider.available ? 'badge-teal' : 'badge-warn'}`}
                    >
                      {settings.provider.available ? 'доступен' : 'недоступен'}
                    </span>
                  </dd>
                  <dt>Режим работы</dt>
                  <dd>
                    <span className={`badge ${settings.provider.name === 'mock' ? 'badge-info' : settings.provider.name === 'ollama' ? 'badge-warn' : 'badge-accent'}`}>
                      {settings.provider.name === 'mock' ? 'Демо-режим: детерминированные правила, ИИ отключена'
                        : settings.provider.name === 'ollama' ? 'Локальный Ollama (CPU, медленно)'
                        : 'Внешний API'}
                    </span>
                  </dd>
                  <dt>Передача данных наружу</dt>
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

                <div style={{ marginTop: 'var(--sp-5)' }}>
                  <div className="small muted" style={{ marginBottom: 8 }}>
                    Доступные провайдеры — переключаются переменной LLM_PROVIDER в файле .env:
                  </div>
                  <div className="chip-row">
                    {settings.available_providers
                      .filter((item) => !(settings.provider.name === 'mock' && item.name === 'ollama'))
                      .map((item) => (
                        <span
                          key={item.name}
                          className={
                            item.name === settings.provider.name
                              ? 'badge badge-accent'
                              : 'badge badge-neutral'
                          }
                          title={item.hint}
                        >
                          {item.label}
                          {item.requires_api_key && (
                            <span className="badge badge-neutral" style={{ fontSize: 11, marginLeft: 6 }}>
                              нужен ключ
                            </span>
                          )}
                        </span>
                      ))}
                    </div>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Ограничения и версии</h2>
                  <p>Значения задаются в файле .env и не изменяются из интерфейса</p>
                </div>
              </div>
              <div className="panel-body">
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
                  <dt>Исходные файлы</dt>
                  <dd>
                    {settings.limits.store_original_files === false
                      ? 'не сохраняются, хранится только извлечённый текст'
                      : 'сохраняются на сервере'}
                  </dd>
                </dl>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Демонстрационные данные</h2>
                  <p>
                    Синтетический пример: вымышленный товар, документы и отзывы. Используется для
                    показа работы системы без доступа к реальным карточкам.
                  </p>
                </div>
              </div>
              <div className="panel-body">
                <div style={{ display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => void seedDemo()}
                    disabled={seeding}
                  >
                    <IconQuote size={16} />
                    {seeding ? 'Создаём…' : 'Добавить демо-товар'}
                  </button>
                  <Link className="btn" to="/app/products">
                    <IconProducts size={16} />
                    Открыть список товаров
                  </Link>
                  <Link className="btn" to="/">
                    <IconShield size={16} />
                    На публичную страницу
                  </Link>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Что делает модель, а что — правила</h2>
                  <p>Ответственность разделена: числа, единицы, даты и модели проверяют правила</p>
                </div>
              </div>
              <div className="panel-body">
                <dl className="kv-list">
                  <dt>Детерминированные правила</dt>
                  <dd>
                    Числовые расхождения, нормализация единиц измерения, даты документов, область
                    применения, типы сигналов и их серьёзность.
                  </dd>
                  <dt>Модель</dt>
                  <dd>
                    Дополнительные формулировки утверждений, уточнение типа, пояснение к
                    находке. Модель не может объявить факт доказанным: без дословного фрагмента
                    источника её вывод отбрасывается.
                  </dd>
                  <dt>Если модель недоступна</dt>
                  <dd>
                    Анализ выполняется локальной эвристикой, в отчёте фиксируется, что внешний
                    провайдер не использовался.
                  </dd>
                </dl>
                <div className="alert alert-info" style={{ marginTop: 'var(--sp-4)', marginBottom: 0 }}>
                  <span className="alert-icon">
                    <IconSpark size={16} />
                  </span>
                  <div>
                    Сравнить провайдеры на фиксированном наборе можно командой
                    <span className="mono"> scripts\compare_providers.py</span>, а проверить
                    доступность бесплатных моделей — командой
                    <span className="mono"> scripts\check_openrouter_models.py</span>.
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </>
  )
}