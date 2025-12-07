// MAStyle token palette stub for C++/JUCE or other consumers.
// Generated from the Swift tokens; values here are placeholders—replace with actual
// exported JSON (e.g., from scripts/export_tokens.swift) or parse /tmp/ma_theme.json.

#pragma once

namespace ma {
struct Colors {
    const char* background = "#0A0C14";
    const char* panel      = "#111527";
    const char* border     = "rgba(255,255,255,0.12)";
    const char* primary    = "#29C7BA";
    const char* success    = "#61E89A";
    const char* warning    = "#F5B45B";
    const char* danger     = "#E84F76";
    const char* info       = "#7AB0F5";
    const char* muted      = "rgba(255,255,255,0.82)";
    const char* metricBG   = "rgba(255,255,255,0.08)";
};

struct Spacing {
    int xs = 4, sm = 8, md = 12, lg = 16, xl = 20, xxl = 28;
};

struct Radius {
    int sm = 6, md = 10, lg = 14, pill = 999;
};

struct Tokens {
    Colors colors;
    Spacing spacing;
    Radius radius;
};
} // namespace ma
