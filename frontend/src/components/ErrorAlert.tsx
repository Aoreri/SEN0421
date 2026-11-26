import { useT } from "../i18n";

export type ErrorAlertProps = {
  message: string;
  onDismiss?: () => void;
};

export function ErrorAlert({ message, onDismiss }: ErrorAlertProps) {
  const t = useT();
  if (!message) return null;

  return (
    <div className="error-alert" role="alert">
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          className="error-dismiss"
          onClick={onDismiss}
          aria-label={t("Hata mesajını kapat")}
        >
          {t("Kapat")}
        </button>
      )}
    </div>
  );
}
