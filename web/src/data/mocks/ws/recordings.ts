import type { WsMessage } from '../../ws/types'

/**
 * Example recording with illustrative values (DEMO / SIMULATED).
 * It is replayed with createReplayer at 1 Hz until milestone I2.
 */
export const normalRecording: WsMessage[] = [
  {
    seq: null,
    topic: 'telemetry',
    type: 'telemetry.tick',
    at: '2026-11-14T10:00:00Z',
    data: { zone_id: 'cabin', metric: 'ppco2_1h', value: 1.2, origin: 'SIMULATED' },
  },
  {
    seq: null,
    topic: 'telemetry',
    type: 'telemetry.tick',
    at: '2026-11-14T10:00:01Z',
    data: { zone_id: 'cabin', metric: 'pio2', value: 149.7, origin: 'SIMULATED' },
  },
  {
    seq: null,
    topic: 'telemetry',
    type: 'telemetry.tick',
    at: '2026-11-14T10:00:02Z',
    data: { zone_id: 'body', metric: 'spo2', value: 98, origin: 'SIMULATED' },
  },
]
