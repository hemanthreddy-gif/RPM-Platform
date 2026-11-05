"use client";

import { useState } from "react";
import { api } from "../lib/api/client";
import { getSession } from "../lib/auth/session";
import { MEAL_PHOTO_REVIEW_NOTICE } from "../lib/nutrition/safety";

export function MealPhotoUpload() {
  const [file, setFile] = useState<File>(); const [status, setStatus] = useState("");
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = event.currentTarget; const session = getSession();
    if (!file || !session) { setStatus("Choose a JPEG or PNG meal photo before uploading."); return; }
    setStatus("Uploading private meal photo…");
    try {
      await api.uploadMeal(file, new Date().toISOString(), session.accessToken);
      setStatus("Meal photo submitted for optional physician review.");
      setFile(undefined); (form.elements.namedItem("meal-photo") as HTMLInputElement).value = "";
    } catch (error) { setStatus(error instanceof Error ? error.message : "Meal photo upload failed."); }
  };
  return <section className="card" aria-labelledby="meal-photo-heading"><h2 id="meal-photo-heading" className="text-xl font-semibold">Share a meal photo</h2>
    <p className="muted">{MEAL_PHOTO_REVIEW_NOTICE}</p>
    <form onSubmit={submit} className="mt-3 grid gap-3"><label htmlFor="meal-photo">Meal photo (JPEG or PNG)</label><input id="meal-photo" name="meal-photo" type="file" accept="image/jpeg,image/png" capture="environment" onChange={(event) => setFile(event.target.files?.[0])} />
      <button className="touch-button" type="submit">Upload for review</button></form>{status && <p role="status" className="mt-3">{status}</p>}
  </section>;
}
