"""
Icon Helper - Phase 8C
Helper function for rendering SVG icons in Jinja2 templates with accessibility support.
Uses Heroicons (MIT licensed) - consistent, professional SVG icons.
"""

from typing import Optional, Literal

# Icon size types
IconSize = Literal["sm", "md", "lg"]

# Icon size mappings
ICON_SIZES = {
    "sm": 16,
    "md": 24,
    "lg": 32,
}

# Common Heroicons SVG paths (inline for simplicity)
# These are simplified versions - in production, you might want to load from files
ICON_SVG = {
    "check": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />',
    "x": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />',
    "exclamation": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />',
    "information": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />',
    "user": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />',
    "credit-card": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v7a3 3 0 003 3z" />',
    "arrow-right": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />',
    "chevron-down": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />',
    "chevron-up": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />',
}


def render_icon(
    icon_name: str,
    size: IconSize = "md",
    aria_label: Optional[str] = None,
    aria_hidden: bool = False,
    class_name: str = "",
) -> str:
    """
    Render an SVG icon with accessibility attributes.
    
    Args:
        icon_name: Name of the icon (must be in ICON_SVG)
        size: Icon size ("sm", "md", or "lg")
        aria_label: ARIA label for the icon (required if not decorative)
        aria_hidden: Whether the icon is decorative (should be hidden from screen readers)
        class_name: Additional CSS classes to apply
    
    Returns:
        HTML string for the icon SVG element
    
    Usage in Jinja2 template:
        {{ render_icon('check', 'md', 'Success') }}
        {{ render_icon('x', 'sm', aria_hidden=True) }}
    """
    if icon_name not in ICON_SVG:
        # Return empty if icon not found
        return ""
    
    icon_size = ICON_SIZES[size]
    svg_path = ICON_SVG[icon_name]
    
    # Build class attribute
    classes = f"icon icon-{size}"
    if class_name:
        classes += f" {class_name}"
    
    # Build accessibility attributes
    aria_attrs = ""
    if aria_hidden:
        aria_attrs = 'aria-hidden="true"'
    elif aria_label:
        aria_attrs = f'aria-label="{aria_label}" role="img"'
    
    # Build SVG element
    svg = f'''<svg
    class="{classes}"
    width="{icon_size}"
    height="{icon_size}"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    {aria_attrs}
    xmlns="http://www.w3.org/2000/svg">
    {svg_path}
</svg>'''
    
    return svg


def render_icon_safe(icon_name: str, **kwargs) -> str:
    """
    Safe version of render_icon that returns empty string if icon not found.
    Useful for templates where icon might not exist.
    """
    try:
        return render_icon(icon_name, **kwargs)
    except (KeyError, ValueError):
        return ""


# Make icon helper available for templates
def get_icon_helper():
    """Return the icon helper function for use in templates."""
    return {
        "render_icon": render_icon,
        "icon": render_icon_safe,  # Shorter alias
    }

