# web · interfaz del monitor de salud

Interfaz de la tripulación (SPA). **Prototipo de apoyo a la decisión: no es un dispositivo médico.** Todo valor sin fuente verificada se rotula `DEMO`, y los datos del cuerpo llevan además la marca «simulado».

## Estado

Funciona con **datos de demostración**: no hay backend conectado todavía (GraphQL y `/ws` llegan en el hito I2 con Dev A). Vistas: **Cabina**, **Nave** y **Asistente**.

## Comandos

```bash
npm run dev            # servidor de desarrollo
npm test               # pruebas (Vitest, jsdom)
npm run test:coverage  # cobertura, umbral del 80 %
npm run lint           # ESLint
npm run typecheck      # TypeScript sin emitir
npm run codegen        # tipos desde ../contracts/schema.graphql
npm run build          # build de producción
```

## Estructura

- `src/app/`: estado puro de la demo (`scenario.ts`).
- `src/features/cabin`, `ship`, `assistant`, `charts`: paneles por funcionalidad.
- `src/shared/`: componentes base (`SevPill`, `EvidenceBadge`, `Banner`) y tokens de color.
- `src/data/`: mocks (MSW, fixtures, grabaciones WS) y cola de mensajes `/ws`.

## Reglas que cumple

- El color nunca va solo: cada estado lleva símbolo y texto (● Normal, ▲ Atención, ◆ Alerta, ■ Crítico).
- La interfaz muestra lo que calcula el backend y no lo recalcula (por ejemplo PIO₂).
- El asistente puede nombrar una alerta activa y nunca la cambia.

## Pendiente

Hook `useWs` y mutaciones GraphQL reales (I2), catálogo completo de 61 tipos de incidencia, silueta SVG del cuerpo, estados de error de red. El contrato `../contracts/schema.graphql` es un **borrador** pendiente de revisión de Dev A.
