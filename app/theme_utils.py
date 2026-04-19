def get_theme_class():
    """Keep Vega components pinned to the light theme."""
    return "data-theme='light'"


def get_vega_imports():
    """Get the Vega component imports."""
    return """
<script type="module" src="https://unpkg.com/@heartlandone/vega@latest/dist/vega/vega.esm.js"></script>
<link rel="stylesheet" href="https://unpkg.com/@heartlandone/vega@latest/dist/vega/vega.css">
"""
