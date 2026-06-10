"""
Shared styling utilities to mirror ExampleReport look-and-feel.
"""

EXAMPLE_COLORS = {
    "primary": "#2b3e50",
    "accent1": "#4CAF50",
    "accent2": "#2196F3",
    "accent3": "#FF9800",
    "text": "#1f1f1f",
    "bg": "#ffffff",
}

STRIKE_ZONE = {
    "width": 17.0,
    "height": 30.0,  # taller zone to match ExampleReport proportions
    "bottom": -1.5,
    "top": 28.5,
}

TITLE_FONT = {"fontsize": 18, "fontweight": "bold", "color": EXAMPLE_COLORS["primary"]}
SECTION_FONT = {"fontsize": 14, "fontweight": "bold", "color": EXAMPLE_COLORS["primary"]}
LABEL_FONT = {"fontsize": 10, "color": EXAMPLE_COLORS["text"]}
