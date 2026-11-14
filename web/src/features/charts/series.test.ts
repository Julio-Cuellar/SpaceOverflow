import { describe, expect, it } from 'vitest'
import { toPolyline, windowSeries, type Point } from './series'

describe('windowSeries', () => {
  it('keeps only the readings of the last 90 seconds', () => {
    const points: Point[] = [
      { t: 0, v: 1 },
      { t: 109, v: 2 },
      { t: 110, v: 3 },
      { t: 200, v: 4 },
    ]

    expect(windowSeries(points, 200, 90).map((p) => p.v)).toEqual([3, 4])
  })
})

describe('toPolyline', () => {
  it('draws the higher value nearer the top of the box', () => {
    const line = toPolyline(
      [
        { t: 0, v: 0 },
        { t: 10, v: 10 },
      ],
      { w: 100, h: 50 },
      { min: 0, max: 10 },
    )

    expect(line).toBe('0,50 100,0')
  })

  it('returns an empty line when there are no points', () => {
    expect(toPolyline([], { w: 100, h: 50 }, { min: 0, max: 10 })).toBe('')
  })
})
