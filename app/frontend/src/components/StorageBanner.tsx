import { useEffect, useState } from 'react'
import { api } from '../api/client'

const STORAGE_KEY = 'rr.storageBannerDismissed'

function readDismissed(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function writeDismissed() {
  try {
    window.localStorage.setItem(STORAGE_KEY, '1')
  } catch {
    /* хранилище недоступно: баннер просто появится снова */
  }
}

/** Предупреждает, что оригиналы загруженных файлов на сервере не хранятся. */
export function StorageBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (readDismissed()) return undefined
    let cancelled = false
    api
      .aiSettings()
      .then((settings) => {
        if (!cancelled && settings.limits.store_original_files === false) setVisible(true)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [])

  if (!visible) return null

  return (
    <div className="storage-banner" role="status">
      <span>
        Исходные файлы не сохраняются на сервере: текст извлекается и хранится в базе, оригинал после
        загрузки недоступен.
      </span>
      <button
        type="button"
        className="storage-banner-close"
        aria-label="Скрыть уведомление"
        onClick={() => {
          writeDismissed()
          setVisible(false)
        }}
      >
        ×
      </button>
    </div>
  )
}
