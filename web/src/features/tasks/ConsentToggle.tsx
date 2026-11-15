interface ConsentToggleProps {
  shared: boolean
  onChange: (shared: boolean) => void
}

/** Categoría de consentimiento «tareas», dentro de «Enlace y privacidad» (plan, F10.4). */
export function ConsentToggle({ shared, onChange }: ConsentToggleProps) {
  return (
    <fieldset aria-label="Enlace y privacidad" role="group">
      <legend>Enlace y privacidad</legend>
      <label>
        <input type="checkbox" checked={shared} onChange={(event) => onChange(event.target.checked)} />
        Compartir el estado de mis tareas con Tierra
      </label>
      {!shared && <p>Tierra no verá el estado de tus tareas. Las tareas siguen funcionando igual en la nave.</p>}
    </fieldset>
  )
}
