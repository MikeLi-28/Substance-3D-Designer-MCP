"""Designer plugin entry points required by the official plugin lifecycle."""

from .plugin import initialize_plugin, uninitialize_plugin


def initializeSDPlugin() -> None:
    """Initialize the authenticated bridge when Designer loads the plugin."""

    initialize_plugin()


def uninitializeSDPlugin() -> None:
    """Stop this plugin's bridge and clean up its owned session."""

    uninitialize_plugin()
