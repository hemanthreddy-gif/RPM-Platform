import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest { return { name: "RPM Platform synthetic demo", short_name: "RPM demo", display: "standalone", start_url: "/login", background_color: "#f8fafc", theme_color: "#0f766e" }; }
