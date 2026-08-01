// Occupies only the section that failed, not the whole page — the rest of
// the screen (and app navigation) stays usable.
function ErrorState({ message, onRetry, className = "" }) {
  return (
    <div
      className={`rounded-lg border border-[#F0D9D4] bg-[#FBF1EF] px-6 py-8 text-center ${className}`}
    >
      <p className="text-sm font-medium text-[#8A3B2E]">
        데이터를 불러오지 못했습니다
      </p>

      {message && (
        <p className="mx-auto mt-2 max-w-md text-sm text-[#8A3B2E]/80">
          {message}
        </p>
      )}

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 min-h-9 rounded-lg border border-[#8A3B2E]/40 px-4 text-xs font-medium text-[#8A3B2E] transition hover:bg-white"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}

export default ErrorState;
