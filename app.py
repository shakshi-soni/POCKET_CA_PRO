import os
import json
import datetime
import ast
import streamlit as st
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from word2number import w2n

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ============================================================
# ADVANCED UI/UX STYLING OVERRIDES (Tailwind-like injection)
# ============================================================
st.set_page_config(page_title="PocketCA Pro", page_icon="⚖️", layout="wide")

# Custom CSS to inject a clean, premium dashboard interface
st.markdown("""
    <style>
    /* Main app background configuration */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    /* Style the chat bubbles beautifully */
    [data-testid="stChatMessage"] {
        background-color: #1e293b !important;
        border-radius: 12px !important;
        border: 1px solid #334155 !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    /* Style user specific input rows */
    div[data-testid="stChatMessageUser"] {
        background-color: #0284c7 !important;
        border: 1px solid #38bdf8 !important;
    }
    /* Premium button enhancements */
    .stDownloadButton>button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.75rem 2rem !important;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }
    .stDownloadButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5);
    }
    /* Custom KPI Metric Cards */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 1.25rem;
        border-radius: 10px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# DASHBOARD SIDEBAR & HEADER LAYOUT
# ============================================================
with st.sidebar:
    st.markdown("### 🏦 System Metrics")
    st.markdown("<div class='metric-card'><p style='color:#94a3b8;margin:0;'>Core Engine</p><h3 style='margin:0;color:#38bdf8;'>Llama 3.1 8B</h3></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='metric-card'><p style='color:#94a3b8;margin:0;'>Tax Regime Jurisdiction</p><h3 style='margin:0;color:#34d399;'>FY 2026-27</h3></div>", unsafe_allow_html=True)
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("🧹 Clear Conversation History", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["langchain_history"] = []
        st.rerun()

# Layout splits for Main View
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("<h1 style='margin:0;'>⚖️ PocketCA Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8;'>Enterprise AI Assistant for Indian Corporate Law & Automated GST Compliant Billing Layer</p>", unsafe_allow_html=True)

# ============================================================
# INITIALIZATION & VECTOR STORE INFRASTRUCTURE
# ============================================================
if not os.getenv("GROQ_API_KEY") and "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

@st.cache_resource
def initialize_engines():
    api_key = os.getenv("GROQ_API_KEY")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    llm = ChatGroq(api_key=api_key, model="llama-3.1-8b-instant", temperature=0.0)
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    try:
        loader = PyPDFLoader("tax_saving.pdf")
        chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(loader.load())
        vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings, collection_name="tax_saving_pdf", persist_directory="./chroma_db")
    except Exception:
        vectorstore = None

    urls = ["https://cleartax.in/s/income-tax-slabs", "https://cleartax.in/s/gst-rates"]
    try:
        link_loader = WebBaseLoader(urls)
        link_chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(link_loader.load())
        vectorstore_link = Chroma.from_documents(documents=link_chunks, embedding=embeddings, collection_name="tax_saving_web", persist_directory="./chroma_db")
    except Exception:
        vectorstore_link = None
        
    return llm, vectorstore, vectorstore_link

llm, vectorstore, vectorstore_link = initialize_engines()

# ============================================================
# CORE ENGINE: PDF REPORTLAB COMPILER
# ============================================================
def generate_invoice(invoice_no, company_name, client_name, client_phone, client_email, client_address, items, payment_method="Bank Transfer", bank_name="", bank_account=""):
    filename = f"invoice_{invoice_no}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(width - 40, height - 105, company_name)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor('#555555'))
    c.drawRightString(width - 40, height - 118, "Tax Compliant Registered Invoice")
    c.drawRightString(width - 40, height - 130, f"Tel: {client_phone}")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 38)
    c.drawString(40, height - 195, "INVOICE")
    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.setLineWidth(0.5)
    c.line(40, height - 205, width - 40, height - 205)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, height - 225, "Invoice No:")
    c.setFont("Helvetica", 9)
    c.drawString(115, height - 225, invoice_no)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(320, height - 225, "Date:")
    c.setFont("Helvetica", 9)
    c.drawString(360, height - 225, datetime.date.today().strftime("%d %B, %Y"))

    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, height - 242, "Bill to:")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor('#333333'))
    c.drawString(115, height - 242, client_name)
    c.drawString(115, height - 255, client_address)
    c.drawString(115, height - 268, client_email)

    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.line(40, height - 290, width - 40, height - 290)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40,  height - 305, "Sl No.")
    c.drawString(100, height - 305, "Description / Particulars")
    c.drawRightString(width - 130, height - 305, "Price (INR)")
    c.drawRightString(width - 40,  height - 305, "Total Amount")
    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.line(40, height - 312, width - 40, height - 312)

    subtotal = 0
    row_y = height - 330
    for idx, item in enumerate(items):
        name = item["name"]
        price = float(item["price"])
        qty = int(item.get("qty", 1))
        total = price * qty
        subtotal += total

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawString(40,  row_y, f"{idx + 1}.")
        c.drawString(100, row_y, name)
        c.drawRightString(width - 130, row_y, f"Rs.{price:,.2f}")
        c.drawRightString(width - 40,  row_y, f"Rs.{total:,.2f}")
        c.setStrokeColor(colors.HexColor('#dddddd'))
        c.setDash(1, 3)
        c.line(40, row_y - 8, width - 40, row_y - 8)
        c.setDash()
        row_y -= 22

    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.setLineWidth(0.5)
    c.line(40, row_y - 5, width - 40, row_y - 5)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 130, row_y - 22, "Grand Total:")
    c.drawRightString(width - 40,  row_y - 22, f"Rs.{subtotal:,.2f}")

    pay_y = row_y - 70
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, pay_y, "Settlement Route:")
    c.setFont("Helvetica", 9)
    c.drawString(150, pay_y, bank_name or payment_method)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, pay_y - 15, "Account Identifier:")
    c.setFont("Helvetica", 9)
    c.drawString(150, pay_y - 15, bank_account or "N/A")

    c.save()
    return filename

# ============================================================
# AGENT ACCOUNTING TOOL LAYERS
# ============================================================
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
def CAlocator(city: str) -> str:
    """Find chartered accountants in the given city."""
    return DuckDuckGoSearchRun().run(f"best chartered accountant CA firm in {city} contact details fees")

@tool
def explain_query(query: str) -> str:
    """Use this when user has received a legal notice, eviction warning, or penalty notice."""
    return DuckDuckGoSearchRun().run(query)

@tool
def CAQNS(query: str) -> str:
    """Use this tool exclusively for advanced corporate law questions."""
    search = DuckDuckGoSearchRun()
    try: return search.run(f"{query} site:in taxmann.com OR site:icai.org OR site:incometaxindia.gov.in")
    except Exception: return search.run(query)

@tool
def gst_calculator(amount: str, gst_rate: str, transction_type: str) -> str:
    """Use this tool explicitly when asked to calculate GST values."""
    clean_amt = str(amount).lower().strip().replace(",", "").replace("rupees", "").replace("rupee", "").replace("rs", "").strip()
    try: final_numeric_amount = float(clean_amt)
    except Exception:
        try: final_numeric_amount = float(w2n.word_to_num(clean_amt))
        except Exception: return "Validation Error: Could not parse configuration."

    gst_rates = {"0": 0, "3": 3, "5": 5, "12": 12, "18": 18, "28": 28}
    gst_rate = str(gst_rate).upper().strip().replace("%", "")
    rate = next((gst_rates[s] for s in gst_rates if s in gst_rate), 28)
    total_gst = (final_numeric_amount * rate) / 100
    return f"GST Calculation Summary:\nBase Amount: ₹{final_numeric_amount:,.2f}\nGST Applied Rate: {rate}%\nCalculated Tax Fraction: ₹{total_gst:,.2f}\nAccumulated Total: ₹{final_numeric_amount + total_gst:,.2f}"

@tool
def invoice_generator(invoice_no: str, company_name: str, client_name: str, client_phone: str, client_email: str, client_address: str, items: str, payment_method: str = "Bank Transfer", bank_name: str = "", bank_account: str = "") -> str:
    """Generates a perfect, tax-compliant PDF invoice file securely on disk."""
    try: raw_items = json.loads(items) if isinstance(items, str) else items
    except Exception:
        try: raw_items = ast.literal_eval(items)
        except Exception: return "Error: Failed to process item array formatting."

    sanitized_items, base_subtotal = [], 0.0
    for item in raw_items:
        name = item.get("name", "Retail Item")
        price_val = str(item.get("price")).replace(",", "").replace("Rs.", "").strip()
        try: price = float(price_val)
        except ValueError: price = 200000.0
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
    """Fallback search network."""
    return DuckDuckGoSearchRun().run(query)

# ============================================================
# AGENT BUILD & CHAT VIEWPORT INTERFACES
# ============================================================
tools = [tax_saving, legal_section, CAlocator, explain_query, CAQNS, gst_calculator, invoice_generator, standard_lookup]
SYSTEM_PROMPT = """You are the Pocket CA Agent, an expert Chartered Accountant AI assistant.
FORMAT: Answer conversational answers in clean professional bullet points in English only."""

agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "ai", "content": "Greetings. I am your automated PocketCA system. Provide transaction particulars or text-driven financial queries to evaluate taxes and structure clean digital invoices."}]
if "langchain_history" not in st.session_state:
    st.session_state["langchain_history"] = []

# Display current chat stream
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Process input submission
if user_query := st.chat_input("Enter asset tracking query or invoice requests..."):
    with st.chat_message("user"):
        st.write(user_query)
    st.session_state["messages"].append({"role": "user", "content": user_query})
    st.session_state["langchain_history"].append(HumanMessage(content=user_query))

    with st.chat_message("assistant"):
        with st.spinner("Processing ledger validation variables..."):
            try:
                response = agent.invoke({"messages": st.session_state["langchain_history"][-10:]})
                st.session_state["langchain_history"] = response["messages"]
                agent_reply = response["messages"][-1].content
                
                st.write(agent_reply)
                st.session_state["messages"].append({"role": "ai", "content": agent_reply})
                
                # Dynamic UX Trigger: Display file action cards when invoices finish rendering
                if "last_generated_pdf" in st.session_state and os.path.exists(st.session_state["last_generated_pdf"]):
                    pdf_file = st.session_state["last_generated_pdf"]
                    with open(pdf_file, "rb") as f:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.download_button(
                            label="📥 Download Tax Invoice Receipt (PDF)",
                            data=f,
                            file_name=pdf_file,
                            mime="application/pdf"
                        )
                    del st.session_state["last_generated_pdf"]
            except Exception as error:
                st.error(f"Execution Error: {error}")
