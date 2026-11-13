"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { MealPhoto } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";
import { MealPhotoPreview } from "./meal-photo-preview";
import { Icon } from "./icon";

export function PatientMealPhotos() {
  const [meals, setMeals] = useState<MealPhoto[]>([]);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  const session = getSession(); const token = session?.accessToken;
  useEffect(() => {
    if (!token) return; let cancelled = false;
    const refresh = () => {
      void api.me(token).then((profile) => api.meals(profile.id, token)).then((result) => { if (!cancelled) { setMeals(result); setError(""); } }).catch(() => { if (!cancelled) { setMeals([]); setError("Meal photos could not be refreshed."); } }).finally(() => { if (!cancelled) setLoading(false); });
    };
    refresh(); window.addEventListener("rpm:meals-changed", refresh);
    return () => { cancelled = true; window.removeEventListener("rpm:meals-changed", refresh); };
  }, [token]);
  if (!session) return null;
  return <section className="card" aria-labelledby="submitted-meals-heading"><div className="workspace-section-head"><div><p className="workspace-kicker">YOUR PHOTO JOURNAL</p><h2 id="submitted-meals-heading">Your submitted meal photos</h2><p>Private photos and comments from your connected physician.</p></div></div>
    {loading ? <p className="loading-copy" role="status">Loading your meal photos…</p> : error ? <p role="alert" className="form-error">{error}</p> : meals.length === 0 ? <div className="empty-state"><Icon name="meal" /><h3>A little more context</h3><p>No meal photos have been submitted. Upload a fictional meal photo to start your journal.</p></div> : <ul className="meal-gallery">{meals.map((meal) => <li className="meal-tile" key={meal.id}><div className="meal-image"><MealPhotoPreview mealId={meal.id} token={session.accessToken} /></div><div className="meal-tile-content"><p className="field-hint">Submitted {new Date(meal.uploaded_at).toLocaleString()}</p><h3>Physician comments</h3>{meal.comments.length ? <ul className="meal-comments">{meal.comments.map((comment) => <li key={comment.id}>{comment.body}<time dateTime={comment.created_at}>{new Date(comment.created_at).toLocaleString()}</time></li>)}</ul> : <p className="muted">No comment has been added.</p>}</div></li>)}</ul>}
  </section>;
}
