import { writeFileSync } from "node:fs";

// The backend OpenAPI endpoint is the source of truth. This deliberately keeps the generated
// surface limited to Phase 6 endpoints until later phases add their screens.
const url = process.env.OPENAPI_URL ?? "http://localhost:8000/openapi.json";
const response = await fetch(url);
if (!response.ok) throw new Error(`Unable to read OpenAPI contract: ${response.status}`);
const spec = await response.json();
const banner = `/* Generated from ${spec.info.title} ${spec.info.version}; rerun npm run api:generate. */\n`;
writeFileSync("lib/api/openapi.json", JSON.stringify(spec, null, 2));
writeFileSync("lib/api/generated-meta.ts", `${banner}export const openApiVersion = ${JSON.stringify(spec.info.version)} as const;\n`);
