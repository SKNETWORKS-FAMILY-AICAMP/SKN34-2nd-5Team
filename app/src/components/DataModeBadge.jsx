import { useOperationsSummary } from "../context/OperationsContext";

// PROJECT (real data) is the expected, unremarkable state, so it reads as
// plain text. DEMO/HYBRID (synthetic or mixed data) gets the strong pill
// treatment instead, so an operator can't mistake it for real operational
// numbers — the distinction that matters is "is this real", not "which
// state am I in", so only the non-default state needs to stand out.
function DataModeBadge() {
  const { dataMode, dataModeLabel } = useOperationsSummary();

  if (dataMode === "project") {
    return (
      <span className="text-xs font-bold text-[#626D67]">
        {dataModeLabel}
      </span>
    );
  }

  return (
    <span className="inline-flex rounded-full bg-[#17211D] px-3 py-1 text-xs font-bold text-white">
      {dataModeLabel}
    </span>
  );
}

export default DataModeBadge;
