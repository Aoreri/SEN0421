import { ReactNode } from "react";

export type FormFieldProps = {
  id: string;
  label: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
};

export function FormField({ id, label, error, required, children }: FormFieldProps) {
  return (
    <div className={`form-field${error ? " has-error" : ""}`}>
      <label htmlFor={id}>
        {label}
        {required && <span className="required-mark" aria-hidden="true"> *</span>}
      </label>
      {children}
      {error && (
        <span id={`${id}-error`} className="field-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
