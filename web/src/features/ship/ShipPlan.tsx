import { severityMeta } from '../../shared/lib/severity'
import type { Ticket, Zone } from './model'

interface ShipPlanProps {
  zones: readonly Zone[]
  tickets: readonly Ticket[]
  onSelectZone: (zoneId: string) => void
}

/** Plano de la nave. Las zonas salen de `zone.layout`: cambiar los datos cambia el plano. */
export function ShipPlan({ zones, tickets, onSelectZone }: ShipPlanProps) {
  const viewBox = zones.reduce(
    (box, z) => ({
      w: Math.max(box.w, z.layout.x + z.layout.w),
      h: Math.max(box.h, z.layout.y + z.layout.h),
    }),
    { w: 0, h: 0 },
  )

  return (
    <div className="ship-plan">
      <svg
        role="group"
        aria-label="Plano de la nave"
        viewBox={`0 0 ${viewBox.w} ${viewBox.h}`}
        width="100%"
      >
        {zones.map((zone) => {
          const meta = severityMeta(zone.status)
          const zoneTickets = tickets.filter((t) => t.zoneId === zone.id && t.status !== 'RESUELTO')
          const pin =
            zoneTickets.length === 0
              ? null
              : zoneTickets.length === 1
                ? zoneTickets[0].code
                : `${zoneTickets[0].code} +${zoneTickets.length - 1}`

          return (
            <g
              key={zone.id}
              role="button"
              tabIndex={0}
              aria-label={`${zone.name}, ${meta.label}`}
              onClick={() => onSelectZone(zone.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') onSelectZone(zone.id)
              }}
            >
              <rect
                x={zone.layout.x}
                y={zone.layout.y}
                width={zone.layout.w}
                height={zone.layout.h}
                fill="none"
                stroke={`var(${meta.token})`}
                strokeWidth={zone.status === 'CRITICO' ? 3 : 2}
                strokeDasharray={zone.status === 'CRITICO' ? '6 4' : undefined}
              />
              <text x={zone.layout.x + 6} y={zone.layout.y + 16} fill={`var(${meta.token})`}>
                {meta.symbol} {zone.name}
              </text>
              {pin && (
                <text x={zone.layout.x + 6} y={zone.layout.y + zone.layout.h - 8} fill="var(--fg)">
                  {pin}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
