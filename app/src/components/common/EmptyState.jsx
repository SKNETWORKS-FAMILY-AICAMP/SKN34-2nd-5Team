// An invitation with a clear next step, not a bare "no results" line.
function EmptyState({ title, description, actionLabel, onAction, className = "" }) {
  return (
    <div
      className={`rounded-lg border border-[#DDE4DF] bg-white px-6 py-10 text-center ${className}`}
    >
      <p className="text-sm font-medium text-[#17211D]">{title}</p>

      {description && (
        <p className="mx-auto mt-2 max-w-md text-sm text-[#626D67]">
          {description}
        </p>
      )}

      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 min-h-9 rounded-lg border border-[#137A5A] px-4 text-xs font-medium text-[#137A5A] transition hover:bg-[#E3F1EA]"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export default EmptyState;
