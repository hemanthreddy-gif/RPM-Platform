"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";

export function MealPhotoPreview({ mealId, token }: { mealId: string; token: string }) {
  const [url, setUrl] = useState<string>();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true; let objectUrl = "";
    void api.mealImage(mealId, token).then((blob) => {
      objectUrl = URL.createObjectURL(blob);
      if (active) setUrl(objectUrl);
    }).catch(() => { if (active) setError("The private meal photo could not be loaded."); });
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [mealId, token]);
  if (error) return <p role="alert" className="muted">{error}</p>;
  if (!url) return <p className="muted">Loading private meal photo…</p>;
  // The image is an authenticated, short-lived in-memory blob URL, which Next's image optimizer
  // cannot fetch without bypassing the API authorization and audit boundary.
  // eslint-disable-next-line @next/next/no-img-element
  return <img className="max-h-80 w-full rounded object-contain" src={url} alt="Submitted meal plate" />;
}
