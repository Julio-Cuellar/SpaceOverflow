import { describe, expect, it } from 'vitest'
import {
  acknowledge,
  addReportedTicket,
  alertFor,
  dashboardFor,
  initialState,
  normalize,
  trigger,
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

describe('trigger', () => {
  it('turns the zone to its severity and opens an automatic ticket there', () => {
    const state = trigger(initialState(), 'co2_slow', 'z-lab', NOW)

    const lab = state.zones.find((z) => z.id === 'z-lab')
    expect(lab?.status).toBe('ALERT')
    expect(state.tickets).toEqual([
      expect.objectContaining({
        code: 'INC-0001',
        title: 'High CO₂',
        severity: 'ALERT',
        zoneId: 'z-lab',
        source: 'ALERT',
        status: 'OPEN',
        valuesInRange: false,
      }),
    ])
  })

  it('numbers the tickets in order of arrival', () => {
    const state = trigger(trigger(initialState(), 'co2_slow', 'z-lab', NOW), 'heat', 'z-galley', NOW)

    expect(state.tickets.map((t) => t.code)).toEqual(['INC-0001', 'INC-0002'])
  })
})

describe('normalize', () => {
  it('returns every zone to normal and lets the automatic tickets be resolved', () => {
    const state = normalize(trigger(initialState(), 'co2_slow', 'z-lab', NOW))

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
    const state = trigger(initialState(), 'co2_slow', 'z-lab', NOW)

    expect(alertFor(state)?.actions.map((a) => a.key)).toEqual([
      'check_ventilation_and_filters',
      'measure_co2_in_local_zones',
    ])
    expect(dashboardFor(state).globalSeverity).toBe('ALERT')
  })
})

describe('acknowledge', () => {
  it('marks the alert as acknowledged, and a new trigger clears the mark', () => {
    const acknowledged = acknowledge(trigger(initialState(), 'co2_slow', 'z-lab', NOW))
    expect(acknowledged.acknowledged).toBe(true)

    const reopened = trigger(acknowledged, 'co2_slow', 'z-lab', NOW)
    expect(reopened.acknowledged).toBe(false)
  })
})

describe('activeAlertTitles', () => {
  it('names the open automatic alerts with their severity, for the assistant to mention', () => {
    const state = trigger(initialState(), 'co2_slow', 'z-lab', NOW)

    expect(activeAlertTitles(state)).toEqual(['High CO₂ (Alert)'])
  })

  it('has no active alerts in the normal scenario or once the values are back in range', () => {
    expect(activeAlertTitles(initialState())).toEqual([])
    expect(activeAlertTitles(normalize(trigger(initialState(), 'co2_slow', 'z-lab', NOW)))).toEqual([])
  })

  it('does not count manual reports as alerts', () => {
    const state = addReportedTicket(
      initialState(),
      { typeKey: 'injury', zoneId: 'z-lab', severity: 'ALERT', title: 'Injury', description: '' },
      NOW,
    )

    expect(activeAlertTitles(state)).toEqual([])
  })
})

describe('zoneSeriesFor', () => {
  it('offers the six metrics of a zone, with humidity and temperature marked as DEMO', () => {
    const series = zoneSeriesFor(initialState(), 'z-lab')

    expect(Object.keys(series)).toHaveLength(6)
    expect(series.humidity.evidenceState).toBe('DEMO')
    expect(series.temperature.evidenceState).toBe('DEMO')
  })

  it('marks the CO₂ trend as an anomaly against its 3 mmHg threshold when the zone is in alert', () => {
    const series = zoneSeriesFor(trigger(initialState(), 'co2_slow', 'z-lab', NOW), 'z-lab')

    expect(series.co2.anomaly).toBe(true)
    expect(series.co2.threshold?.value).toBe(3)
  })
})

describe('addReportedTicket', () => {
  it('adds a manual ticket with the next code and leaves the zone status alone', () => {
    const state = addReportedTicket(
      initialState(),
      { typeKey: 'burning_smell', zoneId: 'z-lab', severity: 'ALERT', title: 'Smell', description: '' },
      NOW,
    )

    expect(state.tickets).toEqual([
      expect.objectContaining({ code: 'INC-0001', source: 'MANUAL', title: 'Smell', zoneId: 'z-lab' }),
    ])
    expect(state.zones.find((z) => z.id === 'z-lab')?.status).toBe('NORMAL')
  })
})
