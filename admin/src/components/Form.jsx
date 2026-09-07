import './Form.css'

// Reusable form building blocks so every future screen's forms (members,
// branding settings, plan changes, ...) share the same field/error layout
// instead of each screen inventing its own.
export function FormField({ label, children }) {
  return (
    <label className="form-field">
      <span className="form-field-label">{label}</span>
      {children}
    </label>
  )
}

export function FormError({ message }) {
  if (!message) return null
  return <div className="form-error-banner">{message}</div>
}
