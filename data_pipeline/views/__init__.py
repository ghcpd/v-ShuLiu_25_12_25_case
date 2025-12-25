"""Views package"""
from .plot import handle_plot
from .download import handle_download
from .parse_view import handle_parse

__all__ = ["handle_plot", "handle_download", "handle_parse"]
