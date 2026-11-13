"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { MealPhoto } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";
import { MEAL_PHOTO_REVIEW_NOTICE } from "../lib/nutrition/safety";
import { MealPhotoPreview } from "./meal-photo-preview";
import { Icon } from "./icon";

export function PhysicianMealReview({ patientId }: { patientId: string }) {
  const [meals, setMeals] = useState<MealPhoto[]>([]);
  const [message, setMessage] = useState(""); const [error, setError] = useState("");
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState("");
  const [revision, setRevision] = useState(0);
  const token = getSession()?.accessToken;
  useEffect(() => {
    if (!token) return; let cancelled = false;
    void api.meals(patientId, token).then((result) => {
      if (!cancelled) { setMeals(result); setError(""); }
    }).catch(() => {
      if (!cancelled) { setMeals([]); setError("Meal photos could not be refreshed. Active monitoring consent is required."); }
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [patientId, token, revision]);
  if (!token) return null;
  async function comment(event: React.FormEvent<HTMLFormElement>, mealId: string) {
    event.preventDefault(); if (!token) return;
    const input = event.currentTarget.elements.namedItem("comment") as HTMLTextAreaElement;
    setBusy(mealId); setError(""); setMessage("");
    try { await api.addMealComment(mealId, input.value, token); input.value = ""; setMessage("Comment added."); setRevision((value) => value + 1); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Comment could not be added."); }
    finally { setBusy(""); }
  }
  return <section id="meal-photos" className="card" aria-labelledby="meal-review-heading"><div className="record-section-heading"><span><Icon name="meal" /></span><div><h2 id="meal-review-heading">Meal-photo review</h2><p>{MEAL_PHOTO_REVIEW_NOTICE}</p></div></div>{message && <p className="success-notice" role="status">{message}</p>}{error && <p className="form-error" role="alert">{error}</p>}
    {loading ? <p className="loading-copy">Loading authorized meal photos…</p> : meals.length === 0 && !error ? <div className="empty-state"><Icon name="meal" /><h3>No submitted meal photos</h3><p>Patient-uploaded photos will appear here for optional review.</p></div> : <ul className="meal-gallery">{meals.map((meal) => <li className="meal-tile" key={meal.id}><div className="meal-image"><MealPhotoPreview mealId={meal.id} token={token} /></div><div className="meal-tile-content"><p className="field-hint">Submitted {new Date(meal.uploaded_at).toLocaleString()}</p>{meal.comments.length > 0 && <ul className="meal-comments" aria-label="Existing comments">{meal.comments.map((item) => <li key={item.id}>{item.body}</li>)}</ul>}<form onSubmit={(event) => void comment(event, meal.id)}><label htmlFor={`comment-${meal.id}`}>Add a non-clinical comment</label><textarea id={`comment-${meal.id}`} name="comment" required maxLength={1000} rows={3} /><button className="touch-button" style={{ marginTop: 12 }} disabled={!!busy} type="submit">{busy === meal.id ? "Adding…" : "Add comment"}</button></form></div></li>)}</ul>}
  </section>;
}
