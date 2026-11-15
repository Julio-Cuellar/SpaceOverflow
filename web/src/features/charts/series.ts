export interface Point {
  /** Seconds since the start of the series. */
  t: number
  v: number
}

export interface Box {
  w: number
  h: number
}

export interface Domain {
  min: number
  max: number
}

/** Readings from the last `windowSeconds` seconds up to `now`. */
export function windowSeries(points: readonly Point[], now: number, windowSeconds: number): Point[] {
  const start = now - windowSeconds
  return points.filter((p) => p.t >= start && p.t <= now)
}

/** SVG points of the stroke. The higher value ends up nearer the top. */
export function toPolyline(points: readonly Point[], box: Box, domain: Domain): string {
  if (points.length === 0) return ''
  const tMin = points[0].t
  const tMax = points[points.length - 1].t
  const tSpan = tMax - tMin || 1
  const vSpan = domain.max - domain.min || 1

  return points
    .map((p) => {
      const x = ((p.t - tMin) / tSpan) * box.w
      const y = box.h - ((p.v - domain.min) / vSpan) * box.h
      return `${x},${y}`
    })
    .join(' ')
}
