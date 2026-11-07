import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fetchReportHtml } from '../api/client'
import { ErrorMessage, Loading } from '../components/States'
import { formatDate } from '../components/labels'
import { IconInfo, IconPrint } from '../components/icons'

export function ReportPage() {
  const { productId = '', runId = '' } = useParams()
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [run, setRun] = useState<Awaited<ReturnType<typeof api.getRun>> | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [reportHtml, runDetail] = await Promise.all([
        fetchReportHtml(productId, runId),
        api.getRun(runId),
      ])
      setHtml(reportHtml)
      setRun(runDetail)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить отчёт')
    }
  }, [productId, runId])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <>
      <header className="topbar">
        <div className="topbar-titles">
          <h1>Отчёт по проверке</h1>
          <div className="topbar-subtitle">
            {run
              ? `${run.product_name}, ${formatDate(run.finished_at ?? run.created_at)}`
              : 'Загрузка…'}
          </div>
        </div>
        <div className="topbar-actions">
          <Link className="btn" to={`/app/products/${productId}`}>
            К товару
          </Link>
          <button type="button" className="btn" onClick={() => window.print()}>
            <IconPrint size={16} />
            Печать / PDF
          </button>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}
        {!html && !error && <Loading label="Формируем отчёт…" />}

        {html && (
          <>
            <div className="alert alert-info">
              <span className="alert-icon">
                <IconInfo size={16} />
              </span>
              <div>
                Автоматический анализ помогает выявлять возможные несоответствия и не является
                юридическим заключением или независимым испытанием товара.
              </div>
            </div>
            <iframe
              className="report-frame"
              title="Отчёт по проверке"
              srcDoc={html}
              sandbox="allow-same-origin"
            />
          </>
        )}
      </div>
    </>
  )
}
