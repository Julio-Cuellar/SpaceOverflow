export interface Point {
  /** Segundos desde el inicio de la serie. */
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

/** Lecturas de los últimos `windowSeconds` segundos hasta `now`. */
export function windowSeries(points: readonly Point[], now: number, windowSeconds: number): Point[] {
  const start = now - windowSeconds
  return points.filter((p) => p.t >= start && p.t <= now)
}

/** Puntos SVG del trazo. El valor más alto queda más cerca de la parte superior. */
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
