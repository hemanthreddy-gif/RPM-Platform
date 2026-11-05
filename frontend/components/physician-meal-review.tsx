"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { MealPhoto } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";
import { MEAL_PHOTO_REVIEW_NOTICE } from "../lib/nutrition/safety";
import { MealPhotoPreview } from "./meal-photo-preview";

export function PhysicianMealReview({ patientId }: { patientId: string }) {
  const [meals, setMeals] = useState<MealPhoto[]>([]); const [message, setMessage] = useState(""); const session = getSession();
  const refresh = () => { if (session) void api.meals(patientId, session.accessToken).then(setMeals).catch(() => setMessage("Meal photos could not be refreshed.")); };
  useEffect(refresh, [patientId, session]);
  if (!session) return null;
  const comment = async (event: React.FormEvent<HTMLFormElement>, mealId: string) => {
    event.preventDefault(); const input = event.currentTarget.elements.namedItem("comment") as HTMLTextAreaElement;
    try { await api.addMealComment(mealId, input.value, session.accessToken); input.value = ""; setMessage("Comment added."); refresh(); } catch (error) { setMessage(error instanceof Error ? error.message : "Comment could not be added."); }
  };
  return <section id="meal-photos" className="card" aria-labelledby="meal-review-heading"><h2 id="meal-review-heading" className="text-xl font-semibold">Meal-photo review</h2><p className="muted">{MEAL_PHOTO_REVIEW_NOTICE}</p>{message && <p role="status">{message}</p>}
    {meals.length === 0 ? <p className="muted">No submitted meal photos.</p> : <ul className="grid gap-6">{meals.map((meal) => <li key={meal.id}><MealPhotoPreview mealId={meal.id} token={session.accessToken} /><p className="muted">Submitted {new Date(meal.uploaded_at).toLocaleString()}.</p>{meal.comments.length > 0 && <ul aria-label="Existing comments">{meal.comments.map((item) => <li key={item.id}>{item.body}</li>)}</ul>}<form className="mt-3 grid gap-2" onSubmit={(event) => void comment(event, meal.id)}><label htmlFor={`comment-${meal.id}`}>Add a non-clinical comment</label><textarea id={`comment-${meal.id}`} name="comment" required maxLength={1000} /><button className="touch-button" type="submit">Add comment</button></form></li>)}</ul>}
  </section>;
}
