import json
import ast
import streamlit as st
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults
from src.utils import generate_invoice

# Note: Vector stores will be assigned dynamically from app.py during boot
vectorstore = None
vectorstore_link = None

@tool
def tax_saving(query: str) -> str:
    """Use this when user asks how to save tax, deductions, 80C, 80D, HRA, NPS."""
    if not vectorstore: return "Tax saving database not initialized."
    results = vectorstore.as_retriever(search_kwargs={"k": 3}).invoke(query)
    return "\n\n".join([r.page_content for r in results]) if results else "No specific matches found."

@tool
def legal_section(query: str) -> str:
    """Use this when user asks about tax rules, GST rules, or legal provisions."""
    if not vectorstore_link: return "Web policy data layers are not loaded."
    results = vectorstore_link.as_retriever(search_kwargs={"k": 3}).invoke(query)
    return "\n\n".join([r.page_content for r in results]) if results else "No legal clauses located."

@tool
def gst_calculator(amount: str, gst_rate: str, transction_type: str) -> str:
    """Use this tool explicitly when asked to calculate GST values."""
    clean_amt = str(amount).lower().strip().replace(",", "").replace("rs", "").strip()
    try: final_numeric_amount = float(clean_amt)
    except Exception: return "Validation Error: Could not parse configuration."

    rate = next((int(s) for s in ["0", "3", "5", "12", "18", "28"] if s in str(gst_rate)), 18)
    total_gst = (final_numeric_amount * rate) / 100
    return f"GST Summary:\nBase: ₹{final_numeric_amount:,.2f}\nRate: {rate}%\nTax Fraction: ₹{total_gst:,.2f}\nAccumulated Total: ₹{final_numeric_amount + total_gst:,.2f}"

@tool
def invoice_generator(invoice_no: str, company_name: str, client_name: str, client_phone: str, client_email: str, client_address: str, items: str, payment_method: str = "Bank Transfer", bank_name: str = "", bank_account: str = "") -> str:
    """Generates a perfect, tax-compliant PDF invoice file securely on disk."""
    try: raw_items = json.loads(items) if isinstance(items, str) else items
    except Exception:
        try: raw_items = ast.literal_eval(items)
        except Exception: return "Error: Failed to process item formatting."

    sanitized_items, base_subtotal = [], 0.0
    for item in raw_items:
        name = item.get("name", "Retail Item")
        price = float(str(item.get("price")).replace(",", "").replace("Rs.", "").strip())
        qty = int(item.get("qty", 1))
        sanitized_items.append({"name": name, "price": price, "qty": qty})
        base_subtotal += (price * qty)

    total_gst = (base_subtotal * 18.0) / 100
    sanitized_items.append({"name": "CGST (9.0%)", "price": total_gst / 2, "qty": 1})
    sanitized_items.append({"name": "SGST (9.0%)", "price": total_gst / 2, "qty": 1})

    filename = generate_invoice(invoice_no=invoice_no, company_name=company_name, client_name=client_name, client_phone=client_phone, client_email=client_email, client_address=client_address, items=sanitized_items, payment_method=payment_method, bank_name=bank_name, bank_account=bank_account)
    
    st.session_state["last_generated_pdf"] = filename
    return f"SUCCESS: Invoice compiled perfectly as '{filename}'."

@tool
def standard_lookup(query: str) -> str:
    """Fallback fallback search network."""
    try:
        search = DuckDuckGoSearchResults()
        return search.run(query)
    except Exception:
        return "Search network currently resolving alternative routing."
