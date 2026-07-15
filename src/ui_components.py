"""
Reusable UI helpers for Mayz Streamlit pages.
Professional Dashboard Design System.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional

import streamlit as st
from PIL import Image

from src.config import DJPB_LOGO_FILE, BASE_DIR

ICONS = {
    "layout-dashboard": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
    "download": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>',
    "users": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
    "activity": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg>',
    "check-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "check-circle-2": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>',
    "alert-triangle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>',
    "alert-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>',
    "circle-alert": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>',
    "x-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>',
    "info": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
    "database": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>',
    "file-spreadsheet": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="8" x2="16" y1="13" y2="13"/><line x1="8" x2="16" y1="17" y2="17"/></svg>',
    "file-text": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>',
    "bar-chart": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/></svg>',
    "pie-chart": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>',
    "heart": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>',
    "message-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>',
    "eye": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>',
    "send": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9Z"/><path d="M22 2 11 13"/></svg>',
    "bell": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
    "calendar": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>',
    "calendar-clock": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 22h14a2 2 0 0 0 2-2V7.5L14.5 2H5a2 2 0 0 0-2 2v4"/><path d="M5 12H2a10 10 0 0 0 20 0h-3"/><circle cx="12" cy="10" r="3"/><path d="M12 14v.01"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "history": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>',
    "refresh-cw": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>',
    "user": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "user-check": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/></svg>',
    "user-x": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 8 18 16"/><path d="m22 16-4-6 6"/></svg>',
    "plus": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
    "trash": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>',
    "edit": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 21l1-5.5Z"/><path d="m15 5 4 4"/></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
    "external-link": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>',
    "chevron-left": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>',
    "chevron-right": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>',
    "arrow-left": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>',
    "link": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    "upload": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>',
    "play": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    "pause": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="4" height="16" x="6" y="4"/><rect width="4" height="16" x="14" y="4"/></svg>',
    "filter": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
    "table": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>',
    "grid": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>',
    "list": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg>',
    "terminal": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>',
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/></svg>',
    "globe": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "server": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/></svg>',
    "zap": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
}

def icon(name: str, size: int = 20, color: str = "currentColor") -> str:
    """Get SVG icon as HTML string."""
    svg = ICONS.get(name, ICONS.get("info", ""))
    return (
        svg
        .replace('width="24"', f'width="{size}"')
        .replace('height="24"', f'height="{size}"')
        .replace("currentColor", color)
    )

# LOGO & ICON HELPERS
def load_logo() -> Optional[Image.Image]:
    """Load DJPb logo safely."""
    try:
        if DJPB_LOGO_FILE.exists():
            return Image.open(DJPB_LOGO_FILE)
    except Exception:
        return None
    return None

def logo_base64() -> Optional[str]:
    logo = load_logo()
    if not logo:
        return None
    buffer = BytesIO()
    logo.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def get_page_icon():
    """Get page icon path for st.set_page_config."""
    import os
    ico_path = BASE_DIR / "assets" / "logo" / "djpb_logo.ico"
    if ico_path.exists():
        return str(ico_path)
    if DJPB_LOGO_FILE.exists():
        return str(DJPB_LOGO_FILE)
    return "M"

PRIMARY = "#1B4B7A"
PRIMARY_LIGHT = "#2563A8"
PRIMARY_MUTED = "#E8F0F8"
SUCCESS = "#0D7A4E"
SUCCESS_LIGHT = "#E6F4ED"
WARNING = "#B45309"
WARNING_LIGHT = "#FEF3E2"
ERROR = "#B91C1C"
ERROR_LIGHT = "#FEE9E9"
INFO = "#0369A1"
INFO_LIGHT = "#E0F2FE"
NEUTRAL_50 = "#FAFAFA"
NEUTRAL_100 = "#F4F4F5"
NEUTRAL_200 = "#E4E4E7"
NEUTRAL_300 = "#D4D4D8"
NEUTRAL_400 = "#A1A1AA"
NEUTRAL_500 = "#71717A"
NEUTRAL_600 = "#52525B"
NEUTRAL_700 = "#3F3F46"
NEUTRAL_800 = "#27272A"
NEUTRAL_900 = "#18181B"
BASE_CSS = f"""
<style>
    /* Reset & Base */
    .stApp {{
        background-color: {NEUTRAL_50};
    }}
    .main .block-container {{
        padding: 1.25rem 1.5rem 2rem;
        max-width: 100%;
    }}
    #MainMenu, footer, .stDeployButton {{
        display: none !important;
    }}

    /* Page Header - Compact, professional */
    .page-header {{
        background: {PRIMARY};
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .page-header-icon {{
        width: 40px;
        height: 40px;
        background: rgba(255,255,255,0.12);
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .page-header-icon svg {{
        width: 20px;
        height: 20px;
        color: white;
    }}
    .page-header-content h1 {{
        color: white;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 2px 0;
        letter-spacing: -0.01em;
    }}
    .page-header-content p {{
        color: rgba(255,255,255,0.7);
        font-size: 0.8rem;
        margin: 0;
    }}

    /* Cards - Clean with subtle border */
    .card {{
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 8px;
        margin-bottom: 16px;
        overflow: hidden;
    }}
    .card-header {{
        background: {NEUTRAL_50};
        border-bottom: 1px solid {NEUTRAL_200};
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .card-header svg {{
        width: 16px;
        height: 16px;
        color: {PRIMARY};
        flex-shrink: 0;
    }}
    .card-header h3 {{
        font-size: 0.875rem;
        font-weight: 600;
        color: {NEUTRAL_800};
        margin: 0;
    }}
    .card-body {{
        padding: 16px;
    }}

    /* Section Heading - Minimal */
    .section-heading {{
        margin: 20px 0 10px 0;
        padding-bottom: 6px;
    }}
    .section-heading h3 {{
        font-size: 0.9rem;
        font-weight: 600;
        color: {NEUTRAL_800};
        margin: 0 0 2px 0;
    }}
    .section-heading p {{
        font-size: 0.775rem;
        color: {NEUTRAL_500};
        margin: 0;
    }}

    /* Status Cards Grid - Compact */
    .status-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin-bottom: 16px;
    }}
    .status-item {{
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 6px;
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .status-item-icon {{
        width: 32px;
        height: 32px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: {INFO_LIGHT};
        color: {PRIMARY};
        flex-shrink: 0;
    }}
    .status-item-icon svg {{
        width: 16px;
        height: 16px;
    }}
    .status-item-content {{
        flex: 1;
        min-width: 0;
    }}
    .status-item-label {{
        font-size: 0.68rem;
        color: {NEUTRAL_500};
        text-transform: uppercase;
        letter-spacing: 0.03em;
        font-weight: 500;
    }}
    .status-item-value {{
        font-size: 0.85rem;
        font-weight: 600;
        color: {NEUTRAL_800};
        margin-top: 1px;
    }}

    /* KPI Cards - Clean metrics */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin-bottom: 16px;
    }}
    .kpi-card {{
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 6px;
        padding: 12px 14px;
        text-align: center;
    }}
    .kpi-value {{
        font-size: 1.4rem;
        font-weight: 700;
        color: {PRIMARY};
        line-height: 1.2;
    }}
    .kpi-label {{
        font-size: 0.68rem;
        color: {NEUTRAL_500};
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        font-weight: 500;
    }}

    /* Stats Row */
    .stats-row {{
        display: flex;
        gap: 10px;
        margin-bottom: 16px;
    }}
    .stat-item {{
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 6px;
        padding: 10px 14px;
        flex: 1;
        text-align: center;
    }}
    .stat-value {{
        font-size: 1.1rem;
        font-weight: 700;
        color: {NEUTRAL_800};
    }}
    .stat-label {{
        font-size: 0.68rem;
        color: {NEUTRAL_500};
        margin-top: 2px;
        font-weight: 500;
    }}

    /* Badges - Subtle, professional */
    .badge {{
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        background: {NEUTRAL_100};
        color: {NEUTRAL_600};
    }}
    .badge-success {{
        background: {SUCCESS_LIGHT};
        color: {SUCCESS};
    }}
    .badge-warning {{
        background: {WARNING_LIGHT};
        color: {WARNING};
    }}
    .badge-error {{
        background: {ERROR_LIGHT};
        color: {ERROR};
    }}
    .badge-info {{
        background: {INFO_LIGHT};
        color: {INFO};
    }}

    /* Alert Boxes - Left border accent */
    .alert {{
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 10px;
        border-left: 3px solid {INFO};
        background: {INFO_LIGHT};
        font-size: 0.8rem;
    }}
    .alert-info {{
        border-left-color: {INFO};
        background: {INFO_LIGHT};
        color: {INFO};
    }}
    .alert-success {{
        border-left-color: {SUCCESS};
        background: {SUCCESS_LIGHT};
        color: {SUCCESS};
    }}
    .alert-warning {{
        border-left-color: {WARNING};
        background: {WARNING_LIGHT};
        color: {WARNING};
    }}
    .alert-error {{
        border-left-color: {ERROR};
        background: {ERROR_LIGHT};
        color: {ERROR};
    }}

    /* Pipeline - Compact flow */
    .pipeline {{
        display: flex;
        align-items: stretch;
        gap: 6px;
        overflow-x: auto;
        padding: 4px 0;
    }}
    .pipeline-node {{
        min-width: 120px;
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 6px;
        padding: 10px;
    }}
    .pipeline-node.success {{
        border-color: {SUCCESS};
        background: {SUCCESS_LIGHT};
    }}
    .pipeline-node.running {{
        border-color: {PRIMARY_LIGHT};
        background: {PRIMARY_MUTED};
    }}
    .pipeline-node.warning {{
        border-color: {WARNING};
        background: {WARNING_LIGHT};
    }}
    .pipeline-node.error, .pipeline-node.failed {{
        border-color: {ERROR};
        background: {ERROR_LIGHT};
    }}
    .pipeline-name {{
        font-size: 0.75rem;
        font-weight: 600;
        color: {NEUTRAL_800};
    }}
    .pipeline-desc {{
        font-size: 0.68rem;
        color: {NEUTRAL_500};
        margin-top: 2px;
    }}
    .pipeline-arrow {{
        display: flex;
        align-items: center;
        color: {NEUTRAL_300};
        min-width: 14px;
    }}

    /* Form Labels */
    .form-label {{
        font-size: 0.775rem;
        font-weight: 500;
        color: {NEUTRAL_700};
        margin-bottom: 4px;
        display: block;
    }}

    /* Footer - Minimal */
    .footer {{
        text-align: center;
        color: {NEUTRAL_400};
        font-size: 0.72rem;
        padding: 14px 0 6px;
        margin-top: 20px;
        border-top: 1px solid {NEUTRAL_200};
    }}

    /* Data Table Container */
    .data-table-container {{
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 8px;
        overflow: hidden;
    }}

    /* Inline Icon */
    .inline-icon {{
        display: inline-flex;
        align-items: center;
        vertical-align: middle;
        margin-right: 4px;
    }}
    .inline-icon svg {{
        width: 14px;
        height: 14px;
    }}

    /* Info Panel - For status sections */
    .info-panel {{
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 6px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }}
    .info-panel-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px solid {NEUTRAL_100};
    }}
    .info-panel-row:last-child {{
        border-bottom: none;
    }}
    .info-panel-label {{
        font-size: 0.775rem;
        color: {NEUTRAL_500};
    }}
    .info-panel-value {{
        font-size: 0.8rem;
        font-weight: 600;
        color: {NEUTRAL_800};
    }}

    /* Metric Cards - For dashboard metrics */
    .metric-card {{
        background: white;
        border: 1px solid {NEUTRAL_200};
        border-radius: 6px;
        padding: 12px;
        text-align: center;
    }}
    .metric-card-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {PRIMARY};
    }}
    .metric-card-label {{
        font-size: 0.68rem;
        color: {NEUTRAL_500};
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}

    /* Responsive */
    @media (max-width: 1100px) {{
        .status-grid, .kpi-grid {{
            grid-template-columns: repeat(2, 1fr);
        }}
    }}
    @media (max-width: 700px) {{
        .status-grid, .kpi-grid {{
            grid-template-columns: 1fr;
        }}
    }}
</style>
"""


def inject_base_css() -> None:
    """Inject base CSS into Streamlit page."""
    st.markdown(BASE_CSS, unsafe_allow_html=True)


def render_header(title: str, subtitle: str, icon_name: str = "layout-dashboard") -> None:
    """Render compact page header."""
    icon_html = icon(icon_name, size=20)
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-icon">
            {icon_html}
        </div>
        <div class="page-header-content">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_card(title: str, icon_name: str = None) -> None:
    """Render card header opening tag."""
    icon_html = icon(icon_name, size=16) if icon_name else ""
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            {icon_html}
            <h3>{title}</h3>
        </div>
        <div class="card-body">
    """, unsafe_allow_html=True)


def render_card_end() -> None:
    """Close card body."""
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_status_grid(items: list) -> None:
    """Render status cards grid.

    Args:
        items: List of dicts with keys: icon, label, value, color (optional)
    """
    cols = st.columns(len(items))
    for i, item in enumerate(items):
        with cols[i]:
            color = item.get("color", "info")
            color_map = {
                "info": INFO_LIGHT,
                "success": SUCCESS_LIGHT,
                "warning": WARNING_LIGHT,
                "error": ERROR_LIGHT,
            }
            bg = color_map.get(color, INFO_LIGHT)
            icon_color = {"info": INFO, "success": SUCCESS, "warning": WARNING, "error": ERROR}.get(color, INFO)

            st.markdown(f"""
            <div class="status-item">
                <div class="status-item-icon" style="background: {bg};">
                    {icon(item.get("icon", "info"), size=16, color=icon_color)}
                </div>
                <div class="status-item-content">
                    <div class="status-item-label">{item.get("label", "")}</div>
                    <div class="status-item-value">{item.get("value", "-")}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_kpi_grid(items: list) -> None:
    """Render KPI cards grid.

    Args:
        items: List of dicts with keys: value, label
    """
    cols = st.columns(len(items))
    for i, item in enumerate(items):
        with cols[i]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{item.get("value", "-")}</div>
                <div class="kpi-label">{item.get("label", "")}</div>
            </div>
            """, unsafe_allow_html=True)


def render_section_heading(title: str, description: str = None) -> None:
    """Render section heading."""
    desc_html = f"<p>{description}</p>" if description else ""
    st.markdown(f"""
    <div class="section-heading">
        <h3>{title}</h3>
        {desc_html}
    </div>
    """, unsafe_allow_html=True)


def render_badge(status: str) -> str:
    """Render status badge HTML."""
    status_lower = status.lower() if status else ""

    if status_lower in ("success", "healthy", "connected", "aktif", "active", "sehat"):
        cls = "success"
    elif status_lower in ("warning", "partial", "partial_success", "peringatan", "cooldown"):
        cls = "warning"
    elif status_lower in ("failed", "error", "disconnected", "nonaktif", "inactive", "gagal"):
        cls = "error"
    elif status_lower in ("running", "idle", "queued", "sedang berjalan", "dalam antrian", "siap"):
        cls = "info"
    else:
        cls = ""
    label = status.title() if status else "-"
    cls_html = f"badge-{cls}" if cls else "badge"
    return f'<span class="{cls_html}">{label}</span>'
def render_alert(message: str, alert_type: str = "info") -> None:
    """Render alert box.
    Args:
        message: Alert message
        alert_type: info, success, warning, error
    """
    st.markdown(f"""
    <div class="alert alert-{alert_type}">
        {message}
    </div>
    """, unsafe_allow_html=True)
def render_info_panel(rows: list) -> None:
    """Render info panel with key-value pairs.

    Args:
        rows: List of dicts with keys: label, value, badge (optional)
    """
    html = ['<div class="info-panel">']
    for row in rows:
        badge = render_badge(row.get("badge", "")) if row.get("badge") else ""
        value = f'<span class="info-panel-value">{row.get("value", "-")}</span>'
        display_value = badge if badge else value
        html.append(f"""
        <div class="info-panel-row">
            <span class="info-panel-label">{row.get("label", "")}</span>
            {display_value}
        </div>
        """)
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)