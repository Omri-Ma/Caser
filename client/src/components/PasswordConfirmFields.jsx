import { FormField, FormError } from './Form'

// Reused everywhere a new password is typed (self-service change-password,
// reset-password, registration) — a re-type-to-confirm field catches typos
// before submission. passwordsValid() is exported too, so each page's
// submit button can be gated on the same "long enough and matches" check
// this component renders inline.
export function passwordsValid(password, confirmPassword) {
  return password.length >= 8 && password === confirmPassword
}

export default function PasswordConfirmFields({
  password,
  onPasswordChange,
  confirmPassword,
  onConfirmPasswordChange,
  passwordLabel = 'סיסמה חדשה',
  autoFocus = false,
}) {
  const showMismatch = confirmPassword.length > 0 && password !== confirmPassword

  return (
    <>
      <FormField label={passwordLabel}>
        <input
          type="password"
          value={password}
          onChange={onPasswordChange}
          minLength={8}
          required
          autoFocus={autoFocus}
        />
      </FormField>
      <FormField label="אימות סיסמה">
        <input type="password" value={confirmPassword} onChange={onConfirmPasswordChange} minLength={8} required />
      </FormField>
      <FormError message={showMismatch ? 'הסיסמאות אינן תואמות' : null} />
    </>
  )
}
