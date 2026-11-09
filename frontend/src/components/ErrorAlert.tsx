export type ErrorAlertProps = {
  message: string;
  onDismiss?: () => void;
};

export function ErrorAlert({ message, onDismiss }: ErrorAlertProps) {
  if (!message) return null;

  return (
    <div className="error-alert" role="alert">
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          className="error-dismiss"
          onClick={onDismiss}
          aria-label="Hata mesajını kapat"
        >
          Kapat
        </button>
      )}
    </div>
  );
}
