import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { LogoMark, LogoWordmark } from '../components/Logo'
import {
  IconArrowRight,
  IconChecks,
  IconChevron,
  IconConflict,
  IconFile,
  IconInfo,
  IconLayers,
  IconLink,
  IconMissing,
  IconQuote,
  IconScale,
  IconScope,
  IconShield,
  IconSpark,
} from '../components/icons'
import { useReveal } from '../hooks/useReveal'

const STEPS = [
  {
    title: 'Добавьте товар и материалы',
    text: 'Описание, характеристики, сертификаты, паспорта изделий и файлы отзывов. Всё, что есть у вас под рукой — остаётся в вашем рабочем пространстве.',
  },
  {
    title: 'Система извлечёт утверждения',
    text: 'Каждая формулировка превращается в утверждение с типом и точной цитатой из источника. Числа приводятся к единицам измерения и сравниваются между собой.',
  },
  {
    title: 'Изучите сигналы и доказательства',
    text: 'Результат показывает, что именно найдено, на каком фрагменте основан вывод, чего не хватает и какие условия измерения остались неизвестными.',
  },
  {
    title: 'Примите решение и сохраните отчёт',
    text: 'Статус рассмотрения, комментарий, история действий и HTML-отчёт с дисклеймером и перечнем источников.',
  },
]

const FEATURES = [
  {
    icon: IconFile,
    title: 'Документы и область применения',
    text: 'Загружайте TXT, CSV, XLSX и PDF. Для каждого документа сохраняются дата, хеш, срок действия и модель, к которой он относится.',
  },
  {
    icon: IconScale,
    title: 'Числовые проверки с единицами',
    text: 'Часы, килограммы, ватты, мАч и другие величины приводятся к общей единице. Разные единицы не мешают сравнению, разные величины никогда не сравниваются.',
  },
  {
    icon: IconQuote,
    title: 'Отзывы как сигналы',
    text: 'Отзывы импортируются из файла или вводятся вручную. Единичный отзыв показывается как сигнал, а не как доказательство дефекта.',
  },
  {
    icon: IconLayers,
    title: 'Шесть типов результатов',
    text: 'Прямое расхождение, отсутствие подтверждения, сигнал из отзывов, неоднозначное утверждение, несовпадение области документа и запрос на проверку человеком.',
  },
  {
    icon: IconChecks,
    title: 'История рассмотрения',
    text: 'Каждое изменение статуса сохраняется: кто, когда, какой статус и с каким комментарием. Решения не теряются между проверками.',
  },
  {
    icon: IconFile,
    title: 'Отчёт по проверке',
    text: 'HTML-отчёт с товаром, источниками, утверждениями, результатами, решениями и ограничениями анализа. Подходит для печати в PDF.',
  },
]

const PRINCIPLES = [
  {
    icon: IconLink,
    title: 'Каждый вывод связан с источником',
    text: 'Если источник доступен, результат цитирует конкретный фрагмент и называет документ, из которого он взят.',
  },
  {
    icon: IconMissing,
    title: 'Нет подтверждения ≠ утверждение ложно',
    text: 'Отсутствие документа фиксируется как недостаток данных. Это не обвинение в недобросовестности.',
  },
  {
    icon: IconQuote,
    title: 'Отзыв не приговор',
    text: 'Опыт одного покупателя — это сигнал для проверки. Мы не выдаём его за установленный факт и не считаем отзывы независимыми подтверждениями.',
  },
  {
    icon: IconScope,
    title: 'Спорные случаи решает человек',
    text: 'Неопределённость не скрывается: такие случаи получают отдельный статус и требуют проверки специалистом.',
  },
  {
    icon: IconShield,
    title: 'Ограничения всегда видны',
    text: 'Отчёт сообщает, какие материалы использовались, какие характеристики не сопоставились с единицами и почему вывод может быть иным.',
  },
]

function RevealBlock({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useReveal<HTMLDivElement>()
  return (
    <div ref={ref} className="reveal" style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  )
}

export function LandingPage() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="landing">
      <header className={scrolled ? 'landing-header is-scrolled' : 'landing-header'}>
        <div className="landing-header-inner">
          <Link to="/" className="sidebar-brand" style={{ padding: 0 }}>
            <LogoMark size={34} variant="dark" />
            <LogoWordmark variant="dark" compact />
          </Link>

          <nav className="landing-nav" aria-label="Разделы страницы">
            <a href="#how">Как это работает</a>
            <a href="#features">Возможности</a>
            <a href="#principles">Достоверность</a>
          </nav>

          <div className="landing-header-actions">
            <Link to="/login" className="btn btn-inverse btn-sm">
              Войти
            </Link>
            <Link to="/login?demo=1" className="btn btn-primary btn-sm">
              Попробовать демо
            </Link>
          </div>
        </div>
      </header>

      {/* ---------------- Первый экран ---------------- */}
      <section className="hero">
        <div className="hero-inner">
          <div>
            <span className="eyebrow">
              <IconSpark size={14} />
              Система доказательной проверки карточек
            </span>
            <h1>Обещания товара. Проверка фактами.</h1>
            <p className="hero-lead">
              Сопоставляйте заявления продавцов с характеристиками, документами и отзывами.
              Находите противоречия и видите, на каких источниках основан каждый вывод.
            </p>
            <div className="hero-actions">
              <Link to="/login?demo=1" className="btn btn-primary btn-lg">
                Попробовать демо
                <IconArrowRight size={17} />
              </Link>
              <a href="#how" className="btn btn-inverse btn-lg">
                Как это работает
              </a>
            </div>
            <p className="hero-note">
              <IconInfo size={15} />
              Демо работает на синтетических данных. Внешние сервисы и платные API не нужны.
            </p>
          </div>

          <div className="demo-panel" aria-label="Демонстрация результата проверки">
            <div className="demo-panel-bar">
              <span className="demo-panel-dots" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
              <span className="demo-panel-title">Результат проверки: демонстрационный товар</span>
            </div>
            <div className="demo-panel-body">
              <div className="demo-product">
                <div className="demo-product-top">
                  <div>
                    <h3>ДЕМО: беспроводные наушники X-500</h3>
                    <div className="demo-product-meta">Синтетические данные, версия правил rules-2024.1</div>
                  </div>
                  <span className="badge badge-violet">ДЕМО</span>
                </div>

                <div className="demo-tabs" aria-hidden="true">
                  <span className="demo-tab">Карточка</span>
                  <span className="demo-tab">Источники</span>
                  <span className="demo-tab is-active">Находки</span>
                  <span className="demo-tab">Доказательства</span>
                </div>

                <div className="demo-finding">
                  <div className="demo-finding-body">
                    <span className="demo-finding-accent" aria-hidden="true" />
                    <div>
                      <h4>Числовое расхождение между описанием и характеристиками</h4>
                      <div className="demo-finding-meta">
                        <span className="badge badge-danger">
                          <span className="badge-dot" />
                          Средняя
                        </span>
                        <span className="badge">Прямое расхождение</span>
                        <span className="badge badge-accent">Открыта</span>
                      </div>
                      <p className="demo-finding-text">
                        В описании товара указано: «до 48 часов» (Описание товара).
                        {'\n'}В таблице характеристик: battery_life_hours = 30 часов.
                        {'\n'}Расхождение: 18 часов (значение обещания выше).
                      </p>

                      <div className="finding-section">
                        <div className="finding-section-label">Основание вывода</div>
                        <div className="evidence-list">
                          <div className="evidence-item">
                            <span className="evidence-icon">
                              <IconFile size={15} />
                            </span>
                            <div>
                              <div className="evidence-source">
                                Описание товара
                                <span className="badge badge-danger">противоречит</span>
                              </div>
                              <div className="evidence-excerpt">
                                До 48 часов работы без подзарядки.
                              </div>
                            </div>
                          </div>
                          <div className="evidence-item">
                            <span className="evidence-icon">
                              <IconScale size={15} />
                            </span>
                            <div>
                              <div className="evidence-source">
                                Таблица характеристик
                                <span className="badge badge-danger">противоречит</span>
                              </div>
                              <div className="evidence-excerpt">battery_life_hours: 30</div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="finding-section">
                        <div className="callout callout-limit">
                          <span className="callout-icon">
                            <IconInfo size={16} />
                          </span>
                          <div>
                            <strong>Ограничение вывода</strong>
                            Условия измерения в источниках не указаны: расхождение может объясняться
                            разными режимами работы. Решение остаётся за человеком.
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="demo-metrics">
                  <div className="demo-metric">
                    <span>Утверждений</span>
                    <strong>50</strong>
                  </div>
                  <div className="demo-metric">
                    <span>Источников</span>
                    <strong>5</strong>
                  </div>
                  <div className="demo-metric">
                    <span>Находок</span>
                    <strong>14</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- Как это работает ---------------- */}
      <section className="landing-section" id="how">
        <div className="landing-container">
          <RevealBlock>
            <span className="eyebrow">Процесс</span>
            <h2 className="section-title">Четыре шага от карточки до отчёта</h2>
            <p className="section-lead">
              Работа строится на детерминированных правилах: одинаковые материалы дают одинаковый
              результат. Внешняя языковая модель не обязательна — она лишь уточняет типы утверждений.
            </p>
          </RevealBlock>

          <div className="steps-grid">
            {STEPS.map((step, index) => (
              <RevealBlock key={step.title} delay={index * 70}>
                <article className="step-card">
                  <div className="step-card-num">{index + 1}</div>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </article>
              </RevealBlock>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- Возможности ---------------- */}
      <section className="landing-section is-muted" id="features">
        <div className="landing-container">
          <RevealBlock>
            <span className="eyebrow">Возможности</span>
            <h2 className="section-title">Что умеет система</h2>
            <p className="section-lead">
              Набор инструментов закрывает весь цикл работы с карточкой: от подготовки материалов до
              зафиксированного решения по каждому найденному сигналу.
            </p>
          </RevealBlock>

          <div className="feature-grid">
            {FEATURES.map((feature, index) => {
              const Icon = feature.icon
              return (
                <RevealBlock key={feature.title} delay={index * 50}>
                  <article className="feature-cell">
                    <div className="feature-icon">
                      <Icon size={19} />
                    </div>
                    <h3>{feature.title}</h3>
                    <p>{feature.text}</p>
                  </article>
                </RevealBlock>
              )
            })}
          </div>
        </div>
      </section>

      {/* ---------------- Принципы достоверности ---------------- */}
      <section className="landing-section is-dark" id="principles">
        <div className="landing-container">
          <RevealBlock>
            <span className="eyebrow">Достоверность</span>
            <h2 className="section-title">Правила, которые нельзя нарушить</h2>
            <p className="section-lead">
              Инструмент помогает находить несоответствия, но не выносит вердикт. Эти ограничения
              зафиксированы в правилах проверки, а не только в интерфейсе.
            </p>
          </RevealBlock>

          <div className="principles">
            {PRINCIPLES.map((principle, index) => {
              const Icon = principle.icon
              return (
                <RevealBlock key={principle.title} delay={index * 60}>
                  <article className="principle">
                    <div className="principle-icon">
                      <Icon size={18} />
                    </div>
                    <h3>{principle.title}</h3>
                    <p>{principle.text}</p>
                  </article>
                </RevealBlock>
              )
            })}
          </div>
        </div>
      </section>

      {/* ---------------- Финал ---------------- */}
      <section className="finale">
        <div className="finale-inner reveal is-visible">
          <h2>Проверьте первую карточку сегодня</h2>
          <p>
            Демо-пространство уже содержит синтетический товар с документами и отзывами. Можно
            сразу посмотреть, как система формирует находки и объясняет их основание.
          </p>
          <div className="finale-actions">
            <Link to="/login?demo=1" className="btn btn-primary btn-lg">
              Открыть демо
              <IconArrowRight size={17} />
            </Link>
            <Link to="/login" className="btn btn-inverse btn-lg">
              Создать рабочее пространство
            </Link>
          </div>
          <p className="finale-note">
            <IconConflict size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: 6 }} />
            Автоматический анализ не является юридическим заключением или независимым испытанием товара.
          </p>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <span>«Обещание против реальности» — система доказательной проверки товарных утверждений.</span>
          <span className="chip-row">
            <span className="badge badge-neutral">
              <IconChevron size={12} />
              Работает локально
            </span>
            <span className="badge badge-neutral">Без внешних API</span>
          </span>
        </div>
      </footer>
    </div>
  )
}
