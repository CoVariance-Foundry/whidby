interface AssistantFallbackStateProps {
  message: string;
}

export default function AssistantFallbackState({ message }: AssistantFallbackStateProps) {
  return (
    <div className="rounded-md border border-[var(--color-negative)]/40 bg-[var(--color-dark)] p-3 text-sm text-[var(--color-negative)]">
      {message}
    </div>
  );
}
