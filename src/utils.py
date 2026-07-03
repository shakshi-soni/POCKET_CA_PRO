import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

def generate_invoice(invoice_no, company_name, client_name, client_phone, client_email, client_address, items, payment_method="Bank Transfer", bank_name="", bank_account=""):
    filename = f"invoice_{invoice_no}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    
    c.setFillColor(colors.HexColor('#0f172a'))
    c.rect(0, 0, 30, height, fill=1, stroke=0)
    
    c.setFillColor(colors.HexColor('#0f172a'))
    c.setFont("Helvetica-Bold", 28)
    c.drawString(60, height - 70, "INVOICE")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 50, height - 55, company_name)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor('#64748b'))
    c.drawRightString(width - 50, height - 72, f"Date Issued: {datetime.date.today().strftime('%d %B, %Y')}")
    c.drawRightString(width - 50, height - 86, f"Contact: {client_phone}")

    c.setStrokeColor(colors.HexColor('#cbd5e1'))
    c.setLineWidth(1)
    c.line(60, height - 110, width - 50, height - 110)

    c.setFillColor(colors.HexColor('#0f172a'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 145, "BILL TO:")
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 162, client_name)
    c.drawString(60, height - 177, client_address)
    c.drawString(60, height - 192, client_email)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 50, height - 145, f"Invoice Ref: {invoice_no}")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor('#64748b'))
    c.drawRightString(width - 50, height - 162, "Status: Regulated Invoice Generated")

    table_top = height - 240
    c.setFillColor(colors.HexColor('#0f172a'))
    c.rect(60, table_top, width - 110, 24, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(75, table_top + 7, "ID")
    c.drawString(130, table_top + 7, "Product/Particular Description")
    c.drawRightString(width - 160, table_top + 7, "Rate")
    c.drawRightString(width - 65, table_top + 7, "Amount")

    subtotal = 0
    row_y = table_top - 22
    
    for idx, item in enumerate(items):
        name = item["name"]
        price = float(item["price"])
        qty = int(item.get("qty", 1))
        total = price * qty
        if "GST" not in name:
            subtotal += total

        c.setFillColor(colors.HexColor('#334155'))
        c.setFont("Helvetica", 9.5)
        c.drawString(75, row_y, f"{idx + 1:02d}")
        c.drawString(130, row_y, name)
        c.drawRightString(width - 160, row_y, f"Rs.{price:,.2f}")
        c.drawRightString(width - 65, row_y, f"Rs.{total:,.2f}")
        
        c.setStrokeColor(colors.HexColor('#f1f5f9'))
        c.setLineWidth(0.5)
        c.line(60, row_y - 6, width - 50, row_y - 6)
        row_y -= 22

    row_y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor('#0f172a'))
    c.drawRightString(width - 160, row_y, "Total Aggregate:")
    
    final_aggregate = sum(f["price"] * f["qty"] for f in items)
    c.drawRightString(width - 65, row_y, f"Rs.{final_aggregate:,.2f}")

    pay_y = row_y - 70
    c.setFillColor(colors.HexColor('#f8fafc'))
    c.rect(60, pay_y - 35, width - 110, 50, fill=1, stroke=0)
    
    c.setFillColor(colors.HexColor('#1e293b'))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(75, pay_y, f"Settlement Channel: {bank_name or payment_method}")
    c.drawString(75, pay_y - 15, f"Account Routing ID: {bank_account or 'N/A'}")

    c.setFillColor(colors.HexColor('#94a3b8'))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(60, 45, "AUTHORIZED COMPLIANT CORE SIGNATURE GENERATED ELECTRONICALLY.")

    c.save()
    return filename
