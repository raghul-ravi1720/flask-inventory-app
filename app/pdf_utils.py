from xhtml2pdf import pisa
from io import BytesIO
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from datetime import datetime

# Create a dedicated templates instance for PDF generation
pdf_templates = Jinja2Templates(directory="app/templates")

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

def default_filter(value, default_val='', boolean=False):
    """
    Custom default filter that mimics Jinja2's built-in default filter
    If boolean is True, only use default value if value is undefined
    """
    if boolean:
        # If boolean is True, only use default if value is undefined (None in our case)
        return value if value is not None else default_val
    else:
        # If boolean is False, use default if value is falsy (None, empty string, etc.)
        return value if value else default_val

def truncate_text(value, max_length=50, ellipsis='...'):
    """Truncate text to specified length"""
    if not value:
        return ""
    if len(value) <= max_length:
        return value
    return value[:max_length] + ellipsis

# Add filters to the PDF templates environment
pdf_templates.env.filters["currency"] = format_currency
pdf_templates.env.filters["dateformat"] = format_date
pdf_templates.env.filters["default"] = default_filter
pdf_templates.env.filters["truncate"] = truncate_text

def generate_pdf(html_content: str):
    """Generate PDF from HTML content with improved settings"""
    try:
        pdf_buffer = BytesIO()
        
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if pisa_status.err:
            print(f"PDF generation error: {pisa_status.err}")
            print(f"Error details: {pisa_status.log}")
            return None
        
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        print(f"Error in generate_pdf: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_pdf_response(pdf_buffer, filename: str):
    """Create a PDF response for download"""
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def render_pdf_template(template_name: str, context: dict):
    """Render a template with the PDF-specific environment"""
    template = pdf_templates.get_template(template_name)
    return template.render(context)