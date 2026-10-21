import { useEffect, useLayoutEffect, useRef } from 'react'

/**
 * Плавное появление блока при попадании в область видимости.
 *
 * Механизмы проверки дублируют друг друга намеренно:
 * IntersectionObserver, события прокрутки и резервный таймер. В некоторых
 * окружениях (фоновые вкладки, встроенные веб-витрины, автоматизированные
 * браузеры) обработчики пересечений и прокрутки не срабатывают, и без
 * таймера контент мог бы остаться невидимым.
 *
 * Базовое состояние элемента — видимое: скрипт лишь добавляет класс
 * `is-pending`, поэтому при отключённом JavaScript контент не пропадает.
 */

const pending = new Set<HTMLElement>()
let intervalId: number | null = null

function revealIfVisible(element: HTMLElement) {
  const rect = element.getBoundingClientRect()
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight
  if (rect.top > viewportHeight * 0.92 || rect.bottom < 0) return

  element.classList.add('is-visible')
  pending.delete(element)
}

function flush() {
  pending.forEach(revealIfVisible)
  if (pending.size === 0) stop()
}

function start() {
  if (intervalId !== null) return
  intervalId = window.setInterval(flush, 150)
}

function stop() {
  if (intervalId !== null) {
    window.clearInterval(intervalId)
    intervalId = null
  }
}

export function useReveal<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T | null>(null)

  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return

    const reduceMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduceMotion) {
      element.classList.add('is-visible')
      return
    }

    element.classList.add('is-pending')
    pending.add(element)

    window.addEventListener('scroll', flush, { passive: true })
    window.addEventListener('resize', flush)
    start()
    revealIfVisible(element)
  }, [])

  useEffect(() => {
    const element = ref.current
    return () => {
      if (element) pending.delete(element)
      if (pending.size === 0) stop()
    }
  }, [])

  return ref
}
