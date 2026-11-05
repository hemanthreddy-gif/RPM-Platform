import { expect, it } from "vitest";
import { MEAL_PHOTO_REVIEW_NOTICE } from "../lib/nutrition/safety";

it("labels the fallback as non-nutrition and non-clinical", () => {
  expect(MEAL_PHOTO_REVIEW_NOTICE).toContain("not analysed for nutrition");
  expect(MEAL_PHOTO_REVIEW_NOTICE).toContain("comments are not medical advice");
});
