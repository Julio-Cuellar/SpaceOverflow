import { describe, expect, it } from 'vitest'
import {
  acknowledge,
  addReportedTicket,
  alertFor,
  dashboardFor,
  initialState,
  normalize,
  provoke,
  zoneSeriesFor,
  activeAlertTitles,
} from './scenario'

const NOW = '2026-11-14T10:00:00Z'

describe('initialState', () => {
  it('starts with every zone normal, no tickets and the normal scenario', () => {
    const state = initialState()

    expect(state.zones.every((z) => z.status === 'NORMAL')).toBe(true)
    expect(state.tickets).toHaveLength(0)
    expect(state.scenario).toBe('normal')
  })
})

describe('provoke', () => {
  it('turns the zone to its severity and opens an automatic ticket there', () => {
    const state = provoke(initialState(), 'co2-alto', 'z-lab', NOW)

    const lab = state.zones.find((z) => z.id === 'z-lab')
    expect(lab?.status).toBe('ALERTA')
    expect(state.tickets).toEqual([
      expect.objectContaining({
        code: 'INC-0001',
        title: 'CO₂ alto',
        severity: 'ALERTA',
        zoneId: 'z-lab',
        source: 'ALERTA',
        status: 'ABIERTO',
        valuesInRange: false,
      }),
    ])
  })

  it('numbers the tickets in order of arrival', () => {
    const state = provoke(provoke(initialState(), 'co2-alto', 'z-lab', NOW), 'calor', 'z-cocina', NOW)

    expect(state.tickets.map((t) => t.code)).toEqual(['INC-0001', 'INC-0002'])
  })
})

describe('normalize', () => {
  it('returns every zone to normal and lets the automatic tickets be resolved', () => {
    const state = normalize(provoke(initialState(), 'co2-alto', 'z-lab', NOW))

    expect(state.zones.every((z) => z.status === 'NORMAL')).toBe(true)
    expect(state.tickets[0].valuesInRange).toBe(true)
    expect(state.scenario).toBe('normal')
  })
})

describe('alertFor and dashboardFor', () => {
  it('shows no alert and a normal dashboard in the normal scenario', () => {
    const state = initialState()

    expect(alertFor(state)).toBeNull()
    expect(dashboardFor(state).globalSeverity).toBe('NORMAL')
  })

  it('shows the CO₂ alert with its actions in order, and the red cabin status', () => {
    const state = provoke(initialState(), 'co2-alto', 'z-lab', NOW)

    expect(alertFor(state)?.actions.map((a) => a.key)).toEqual([
      'revisar_ventilacion_y_filtros',
      'medir_co2_en_zonas_locales',
    ])
    expect(dashboardFor(state).globalSeverity).toBe('ALERTA')
  })
})

describe('acknowledge', () => {
  it('marks the alert as acknowledged, and a new provocation clears the mark', () => {
    const acknowledged = acknowledge(provoke(initialState(), 'co2-alto', 'z-lab', NOW))
    expect(acknowledged.acknowledged).toBe(true)

    const reopened = provoke(acknowledged, 'co2-alto', 'z-lab', NOW)
    expect(reopened.acknowledged).toBe(false)
  })
})

describe('activeAlertTitles', () => {
  it('names the open automatic alerts with their severity, for the assistant to mention', () => {
    const state = provoke(initialState(), 'co2-alto', 'z-lab', NOW)

    expect(activeAlertTitles(state)).toEqual(['CO₂ alto (Alerta)'])
  })

  it('has no active alerts in the normal scenario or once the values are back in range', () => {
    expect(activeAlertTitles(initialState())).toEqual([])
    expect(activeAlertTitles(normalize(provoke(initialState(), 'co2-alto', 'z-lab', NOW)))).toEqual([])
  })

  it('does not count manual reports as alerts', () => {
    const state = addReportedTicket(
      initialState(),
      { typeKey: 'injury', zoneId: 'z-lab', severity: 'ALERTA', title: 'Lesión', description: '' },
      NOW,
    )

    expect(activeAlertTitles(state)).toEqual([])
  })
})

describe('zoneSeriesFor', () => {
  it('offers the six metrics of a zone, with humidity and temperature marked as DEMO', () => {
    const series = zoneSeriesFor(initialState(), 'z-lab')

    expect(Object.keys(series)).toHaveLength(6)
    expect(series.humedad.evidenceState).toBe('DEMO')
    expect(series.temperatura.evidenceState).toBe('DEMO')
  })

  it('marks the CO₂ trend as an anomaly against its 3 mmHg threshold when the zone is in alert', () => {
    const series = zoneSeriesFor(provoke(initialState(), 'co2-alto', 'z-lab', NOW), 'z-lab')

    expect(series.co2.anomaly).toBe(true)
    expect(series.co2.threshold?.value).toBe(3)
  })
})

describe('addReportedTicket', () => {
  it('adds a manual ticket with the next code and leaves the zone status alone', () => {
    const state = addReportedTicket(
      initialState(),
      { typeKey: 'burning_smell', zoneId: 'z-lab', severity: 'ALERTA', title: 'Olor', description: '' },
      NOW,
    )

    expect(state.tickets).toEqual([
      expect.objectContaining({ code: 'INC-0001', source: 'MANUAL', title: 'Olor', zoneId: 'z-lab' }),
    ])
    expect(state.zones.find((z) => z.id === 'z-lab')?.status).toBe('NORMAL')
  })
})
