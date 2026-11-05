"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { MealPhoto } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";
import { MealPhotoPreview } from "./meal-photo-preview";

export function PatientMealPhotos() {
  const [meals, setMeals] = useState<MealPhoto[]>([]); const [error, setError] = useState(""); const session = getSession(); const token = session?.accessToken;
  useEffect(() => { if (!token) return; void api.me(token).then((profile) => api.meals(profile.id, token)).then(setMeals).catch(() => setError("Meal photos could not be refreshed.")); }, [token]);
  if (!session) return null;
  return <section className="card" aria-labelledby="submitted-meals-heading"><h2 id="submitted-meals-heading" className="text-xl font-semibold">Your submitted meal photos</h2>{error && <p role="alert">{error}</p>}
    {meals.length === 0 ? <p className="muted">No meal photos have been submitted.</p> : <ul className="grid gap-4 md:grid-cols-2">{meals.map((meal) => <li key={meal.id}><MealPhotoPreview mealId={meal.id} token={session.accessToken} /><p className="muted">Submitted {new Date(meal.uploaded_at).toLocaleString()}.</p><h3 className="font-semibold">Physician comments</h3>{meal.comments.length ? <ul>{meal.comments.map((comment) => <li key={comment.id}>{comment.body}</li>)}</ul> : <p className="muted">No comment has been added.</p>}</li>)}</ul>}</section>;
}
