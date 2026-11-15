interface ConsentToggleProps {
  shared: boolean
  onChange: (shared: boolean) => void
}

/** Consent category "tasks", inside "Link and privacy" (plan, F10.4). */
export function ConsentToggle({ shared, onChange }: ConsentToggleProps) {
  return (
    <fieldset aria-label="Link and privacy" role="group">
      <legend>Link and privacy</legend>
      <label>
        <input type="checkbox" checked={shared} onChange={(event) => onChange(event.target.checked)} />
        Share the status of my tasks with Ground
      </label>
      {!shared && <p>Ground will not see the status of your tasks. Tasks keep working the same on the ship.</p>}
    </fieldset>
  )
}
