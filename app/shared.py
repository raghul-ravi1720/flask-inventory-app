from fastapi.templating import Jinja2Templates
from datetime import datetime

templates = Jinja2Templates(directory="app/templates")

def format_currency(value):
    """Format currency values"""
    if value is None:
        return "₹0.00"
    try:
        return f"₹{float(value):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

def format_date(value, format='%Y-%m-%d'):
    """Format date values"""
    if value is None:
        return ""
    try:
        if isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m-%d')
        return value.strftime(format)
    except (ValueError, TypeError):
        return ""

# Add filters to templates
templates.env.filters["currency"] = format_currency
templates.env.filters["dateformat"] = format_date