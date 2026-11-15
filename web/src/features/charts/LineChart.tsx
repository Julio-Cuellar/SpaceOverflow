import { toPolyline, type Point } from './series'

interface Threshold {
  value: number
  label: string
}

interface LineChartProps {
  label: string
  unit: string
  points: readonly Point[]
  threshold?: Threshold
  anomaly?: boolean
}

const WIDTH = 300
const HEIGHT = 120

/**
 * Gráfica de tendencia en SVG. Las marcas (umbral, anomalía) llevan texto, no solo color.
 * uPlot dibuja en canvas y no se puede probar en jsdom; por eso la gráfica es SVG.
 */
export function LineChart({ label, unit, points, threshold, anomaly = false }: LineChartProps) {
  if (points.length === 0) {
    return <p>Esperando lecturas del simulador</p>
  }

  const values = points.map((p) => p.v)
  const domain = {
    min: Math.min(...values, threshold?.value ?? Infinity),
    max: Math.max(...values, threshold?.value ?? -Infinity),
  }
  const last = points[points.length - 1].v

  const thresholdY =
    threshold === undefined
      ? null
      : HEIGHT - ((threshold.value - domain.min) / (domain.max - domain.min || 1)) * HEIGHT

  return (
    <figure>
      <svg
        role="img"
        aria-label={`${label}, último valor ${last} ${unit}`}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        width="100%"
      >
        <polyline
          points={toPolyline(points, { w: WIDTH, h: HEIGHT }, domain)}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        />
        {threshold && thresholdY !== null && (
          <g>
            <line x1={0} x2={WIDTH} y1={thresholdY} y2={thresholdY} strokeDasharray="4 4" />
            <text x={4} y={thresholdY - 4}>
              {threshold.label}
            </text>
          </g>
        )}
      </svg>
      {anomaly && <figcaption>ANOMALÍA</figcaption>}
    </figure>
  )
}
