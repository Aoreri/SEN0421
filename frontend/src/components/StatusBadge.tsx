export type StatusBadgeProps = {
  text: string;
};

export function StatusBadge({ text }: StatusBadgeProps) {
  const variant = text.trim().replace(/\s+/g, "-").toLowerCase();
  return <span className={`badge ${variant}`}>{text}</span>;
}
