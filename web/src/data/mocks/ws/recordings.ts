import type { WsMessage } from '../../ws/types'

/**
 * Grabación de ejemplo con valores ilustrativos (DEMO / SIMULADO).
 * Se reproduce con createReplayer a 1 Hz hasta el hito I2.
 */
export const normalRecording: WsMessage[] = [
  {
    seq: null,
    topic: 'telemetry',
    type: 'telemetry.tick',
    at: '2026-11-14T10:00:00Z',
    data: { zone_id: 'cabina', metric: 'ppco2_1h', value: 1.2, origin: 'SIMULATED' },
  },
  {
    seq: null,
    topic: 'telemetry',
    type: 'telemetry.tick',
    at: '2026-11-14T10:00:01Z',
    data: { zone_id: 'cabina', metric: 'pio2', value: 149.7, origin: 'SIMULATED' },
  },
  {
    seq: null,
    topic: 'telemetry',
    type: 'telemetry.tick',
    at: '2026-11-14T10:00:02Z',
    data: { zone_id: 'cuerpo', metric: 'spo2', value: 98, origin: 'SIMULATED' },
  },
]
