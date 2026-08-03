import { useState } from "react";


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function photoUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE_URL}${path}`;
}

function BusinessPhoto({ photos, alt, className = "h-28 w-full", compact = false, fit = "cover" }) {
  const photo = photos?.[0] ?? null;
  const [failedPhotoId, setFailedPhotoId] = useState(null);
  const failed = photo?.photoId === failedPhotoId;

  if (!photo || failed) {
    return (
      <div className={`${className} grid place-items-center overflow-hidden rounded-lg bg-[linear-gradient(135deg,#EEF3EF,#DDE7E1)] text-[#718078]`}>
        <span className={compact ? "text-[9px] font-bold" : "text-[10px] font-bold"}>사진 없음</span>
      </div>
    );
  }

  return (
    <figure className={`${className} relative overflow-hidden rounded-lg bg-[#EEF3EF]`}>
      <img
        src={photoUrl(photo.path)}
        alt={alt}
        loading="lazy"
        decoding="async"
        onError={() => setFailedPhotoId(photo.photoId)}
        className={`h-full w-full transition duration-300 hover:scale-[1.02] ${fit === "contain" ? "object-contain bg-[#202722]" : "object-cover"}`}
      />
      {!compact && (
        <figcaption className="absolute bottom-1.5 left-1.5 rounded bg-black/65 px-1.5 py-0.5 text-[8px] font-semibold text-white">
          Yelp Open Dataset · {photo.label}
        </figcaption>
      )}
    </figure>
  );
}

export default BusinessPhoto;
