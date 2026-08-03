const PARKING_LABELS = {
  garage: "차고 주차",
  lot: "전용 주차장",
  street: "노상 주차",
  valet: "발레파킹",
  validated: "주차 확인",
};

const ALCOHOL_LABELS = {
  full_bar: "주류·바",
  beer_and_wine: "맥주·와인",
};

function compactAddress(attributes) {
  return [attributes.address, attributes.postalCode].filter(Boolean).join(" · ");
}

function buildBadges(attributes) {
  const badges = [];
  if (attributes.priceRange) badges.push("$".repeat(attributes.priceRange));
  if (attributes.takeout === true) badges.push("포장");
  if (attributes.delivery === true) badges.push("배달");
  if (attributes.reservations === true) badges.push("예약");
  if (attributes.outdoorSeating === true) badges.push("야외 좌석");
  if (attributes.wifi === "free") badges.push("무료 Wi-Fi");
  if (attributes.wifi === "paid") badges.push("유료 Wi-Fi");
  if (attributes.wheelchairAccessible === true) badges.push("휠체어 접근");
  if (attributes.alcohol && ALCOHOL_LABELS[attributes.alcohol]) {
    badges.push(ALCOHOL_LABELS[attributes.alcohol]);
  }
  if (Array.isArray(attributes.parking) && attributes.parking.length) {
    const parking = attributes.parking
      .map((value) => PARKING_LABELS[value])
      .filter(Boolean);
    badges.push(parking.length === 1 ? parking[0] : "주차 정보");
  }
  return badges;
}

function BusinessAttributeBadges({
  attributes,
  compact = false,
  showAddress = false,
  showHours = false,
}) {
  if (!attributes) return null;

  const badges = buildBadges(attributes);
  const address = compactAddress(attributes);
  const hours = attributes.hours && typeof attributes.hours === "object"
    ? Object.entries(attributes.hours)
    : [];
  return (
    <div className={compact ? "space-y-1.5" : "space-y-2.5"}>
      <div className="flex flex-wrap gap-1.5">
        {badges.map((badge) => (
          <span key={badge} className={`rounded-full border border-[#DDE4DF] bg-white px-2 py-0.5 font-semibold text-[#4F5D56] ${compact ? "text-[9px]" : "text-[10px]"}`}>
            {badge}
          </span>
        ))}
      </div>

      {showAddress && address && (
        <p className={compact ? "text-[9px] leading-4 text-[#718078]" : "text-[10px] leading-4 text-[#718078]"}>
          {address}
        </p>
      )}

      {showHours && hours.length > 0 && (
        <details className="rounded-lg border border-[#E2E7E3] bg-[#FAFBFA] px-3 py-2 text-[10px] text-[#4F5D56]">
          <summary className="cursor-pointer font-bold text-[#075C45]">데이터셋 기준 영업시간</summary>
          <dl className="mt-2 grid grid-cols-[52px_1fr] gap-x-2 gap-y-1">
            {hours.map(([day, value]) => (
              <div key={day} className="contents">
                <dt className="font-semibold">{day}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </div>
  );
}

export default BusinessAttributeBadges;
