import { describe, expect, it } from 'vitest'
import { attributeLabel, categoryLabel } from '../components/labels'

describe('Подписи характеристик и категорий', () => {
  it('известные ключи характеристик переводятся с единицами', () => {
    expect(attributeLabel('weight_g')).toBe('Масса, г')
    expect(attributeLabel('battery_life_hours')).toBe('Время работы от батареи, ч')
  })

  it('неизвестный ключ не показывается с подчёркиваниями', () => {
    expect(attributeLabel('screen_refresh_rate')).toBe('Screen refresh rate')
    expect(attributeLabel('Время работы')).toBe('Время работы')
  })

  it('категория переводится по частям', () => {
    expect(categoryLabel('electronics / наушники')).toBe('Электроника / наушники')
    expect(categoryLabel('')).toBe('Категория не указана')
    expect(categoryLabel(null)).toBe('Категория не указана')
  })
})
