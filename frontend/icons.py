"""Inline SVG icon library matching the design's <Icon name=...> component.

Each ``icon(name, size)`` returns an SVG string sized to the requested px.
Color follows ``currentColor`` so the icon adopts the parent element's color.
"""

from __future__ import annotations

# Stroke-based icons (Lucide / Feather style).
_PATHS: dict[str, str] = {
    "sparkle": (
        '<path d="M12 3l1.6 4.6L18 9.2l-4.4 1.6L12 15l-1.6-4.2L6 9.2l4.4-1.6Z"/>'
        '<path d="M19 4v3M21 5.5h-3"/>'
        '<path d="M5 17v3M3 18.5h3"/>'
    ),
    "shield": (
        '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z"/>'
    ),
    "shield-plus": (
        '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z"/>'
        '<path d="M12 8v8M8 12h8"/>'
    ),
    "doc": (
        '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 3v5h5"/>'
    ),
    "doc-check": (
        '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 3v5h5"/>'
        '<path d="M9 14l2 2 4-4"/>'
    ),
    "user": (
        '<path d="M20 21a8 8 0 0 0-16 0"/>'
        '<circle cx="12" cy="7" r="4"/>'
    ),
    "hospital": (
        '<rect x="3" y="6" width="18" height="15" rx="1"/>'
        '<path d="M12 10v6M9 13h6"/>'
        '<path d="M9 6V3h6v3"/>'
    ),
    "calendar": (
        '<rect x="3" y="5" width="18" height="16" rx="2"/>'
        '<path d="M3 10h18M8 3v4M16 3v4"/>'
    ),
    "clock": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 7v5l3 2"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="8" ry="3"/>'
        '<path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>'
        '<path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>'
    ),
    "cpu": (
        '<rect x="6" y="6" width="12" height="12" rx="1.5"/>'
        '<path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/>'
    ),
    "pulse": (
        '<path d="M3 12h4l2-7 4 14 2-7h6"/>'
    ),
    "inbox": (
        '<path d="M22 13h-6l-2 3h-4l-2-3H2"/>'
        '<path d="M5.45 4.62A2 2 0 0 1 7.27 3.5h9.46a2 2 0 0 1 1.82 1.12L22 13v5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-5z"/>'
    ),
    "archive": (
        '<rect x="3" y="3" width="18" height="5" rx="1"/>'
        '<path d="M5 8v11a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8"/>'
        '<path d="M10 12h4"/>'
    ),
    "check-circle": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M8 12l3 3 5-6"/>'
    ),
    "x-circle": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M9 9l6 6M15 9l-6 6"/>'
    ),
    "alert": (
        '<path d="M12 3 2 21h20z"/>'
        '<path d="M12 9v5M12 17v.01"/>'
    ),
    "arrow-left": (
        '<path d="M19 12H5"/>'
        '<path d="M12 19l-7-7 7-7"/>'
    ),
    "chevron-right": (
        '<path d="M9 6l6 6-6 6"/>'
    ),
    "chevron-down": (
        '<path d="M6 9l6 6 6-6"/>'
    ),
    "check": (
        '<path d="M5 12l5 5 9-11"/>'
    ),
    "x": (
        '<path d="M6 6l12 12M18 6l-12 12"/>'
    ),
    "flag": (
        '<path d="M5 21V4M5 4h12l-3 4 3 4H5"/>'
    ),
    "bell": (
        '<path d="M18 16v-5a6 6 0 0 0-12 0v5l-2 2h16z"/>'
        '<path d="M10 21h4"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="7"/>'
        '<path d="M21 21l-4.5-4.5"/>'
    ),
    "filter": (
        '<path d="M3 4h18l-7 9v6l-4-2v-4z"/>'
    ),
    "download": (
        '<path d="M12 3v12M7 11l5 5 5-5"/>'
        '<path d="M5 21h14"/>'
    ),
    "copy": (
        '<rect x="9" y="9" width="11" height="11" rx="2"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
    ),
    "play": (
        '<path d="M6 4l14 8-14 8z"/>'
    ),
    "link": (
        '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 1 0-5.7-5.7l-1 1"/>'
        '<path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 1 0 5.7 5.7l1-1"/>'
    ),
    "gear": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.5-2.4.8a7 7 0 0 0-2-1.2L14 3h-4l-.5 2.4a7 7 0 0 0-2 1.2l-2.4-.8-2 3.5 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.5 2.4-.8a7 7 0 0 0 2 1.2L10 21h4l.5-2.4a7 7 0 0 0 2-1.2l2.4.8 2-3.5-2-1.5c.1-.4.1-.8.1-1.2Z"/>'
    ),
    "logout": (
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
        '<path d="M16 17l5-5-5-5M21 12H9"/>'
    ),
    "tool": (
        '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 1 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z"/>'
    ),
    "check-shield": (
        '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z"/>'
        '<path d="M9 12l2 2 4-4"/>'
    ),
    "notion": (
        '<rect x="3" y="3" width="18" height="18" rx="2"/>'
        '<path d="M7 7v10M7 7l10 10M17 7v10"/>'
    ),
}


def icon(name: str, size: int = 16, *, color: str = "currentColor", stroke: float = 2) -> str:
    """Return an inline SVG string for the given icon name and size."""
    paths = _PATHS.get(name)
    if not paths:
        return _fallback(size, color)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="display: inline-block; vertical-align: middle; flex-shrink: 0;">'
        f'{paths}</svg>'
    )


def _fallback(size: int, color: str) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" '
        f'style="display: inline-block; vertical-align: middle; flex-shrink: 0;">'
        f'<circle cx="12" cy="12" r="9"/></svg>'
    )
