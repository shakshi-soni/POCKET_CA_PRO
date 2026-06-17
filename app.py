# IMPORT

import json
import requests
import os
import chromadb
from groq import Groq
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, messages_from_dict, messages_to_dict

# API key 
GROQ_API_KEY = ""  

#LLM
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0.6
)

# MEMORY
MEMORY_FILE = "tax.memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return messages_from_dict(json.load(f))
    except:
        return []

def save_memory(chat_history):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(messages_to_dict(chat_history), f)
    except Exception as e:
        print(f"Memory save error: {e}")

def trim_message(hist, max_message=10):
    if len(hist) <= max_message:
        return hist
    sys_msg = [msg for msg in hist if isinstance(msg, SystemMessage)]
    recent_msg = [msg for msg in hist if not isinstance(msg, SystemMessage)][-max_message:]
    return sys_msg + recent_msg

#RAG
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="savetax_knowledge")

TAX_KNOWLEDGE = """🛡️ Section 80C (Limit: ₹1,50,000/year):
EPF, PPF, ELSS, NSC, SSY, NPS, Life Insurance Premium,
Children Tuition Fees, Home Loan Principal, Tax-Saving FDs.

🏥 Section 80D (Medical Insurance):
Self & Family: up to ₹25,000. Parents under 60: ₹25,000.
Senior citizen parents: ₹50,000. Preventive checkup: ₹5,000.

🏠 Home & Education Loans:
Section 24(b): up to ₹2,00,000 on home loan interest.
Section 80E: full interest on education loan, no limit, 8 years.

👴 Additional Deductions:
80CCD(1B): extra ₹50,000 for NPS.
80TTA: ₹10,000 on savings account interest (₹50,000 for seniors under 80TTB).
80G: 50-100% on donations to registered NGOs.
HRA / 80GG: up to ₹60,000/year for non-salaried rent payers."""

if collection.count() == 0:
    collection.add(
        documents=[TAX_KNOWLEDGE],
        ids=["0"]
    )

# TOOLS
@tool
def CAlocator(city: str) -> str:
    """If the user has a complex tax notice or penalty, suggest a CA nearby.
    Use DuckDuckGoSearchRun immediately to find accurate CA details:
    name, qualification, fees, location."""
    return (
        f"Authorized: Search for a qualified CA in {city} using web search. "
        "Provide name, qualifications, fees, and contact details."
    )

@tool
def invoice(request: str) -> str:
    """Generate a professional GST-compliant invoice from the user's description.
    Include: invoice number, date, vendor/client details, line items,
    HSN/SAC codes, tax breakdown (CGST/SGST/IGST), and grand total.
    If HSN codes or tax rates are missing, search the web first."""
    return (
        "Authorized: Generate a complete, compliance-ready invoice. "
        "Search for HSN/SAC codes and tax rates if not provided. "
        "Present as a clean Markdown table with all totals computed correctly."
    )

@tool
def gst_calculator(base_amount: float, gst_rate_pct: float, is_inter_state: bool = False) -> str:
    """Calculates the GST breakdown for a given base amount and tax rate.
    - base_amount: taxable value
    - gst_rate_pct: GST rate (e.g. 5, 12, 18, 28)
    - is_inter_state: True = IGST applies; False = CGST + SGST split"""
    try:
        base = float(base_amount)
        rate = float(gst_rate_pct)
        total_gst = base * (rate / 100.0)
        grand_total = base + total_gst

        if is_inter_state:
            cgst, sgst, igst = 0.0, 0.0, total_gst
        else:
            cgst = sgst = total_gst / 2.0
            igst = 0.0

        result = {
            "status": "success",
            "calculations": {
                "base_amount": round(base, 2),
                "gst_rate_percentage": round(rate, 2),
                "cgst": round(cgst, 2),
                "sgst": round(sgst, 2),
                "igst": round(igst, 2),
                "total_gst_amount": round(total_gst, 2),
                "grand_total": round(grand_total, 2)
            }
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool
def save_tax(question: str) -> str:
    """Search the RAG knowledge base for Indian tax saving information.
    If not found, use DuckDuckGo to get the correct answer."""
    try:
        results = collection.query(query_texts=[question], n_results=2)
        docs = results.get("documents", [[]])
        if docs and docs[0]:
            return "\n".join(docs[0])
        return "No relevant info found in knowledge base. Please search the web."
    except Exception as e:
        return f"RAG error: {e}"

web_search = DuckDuckGoSearchRun()
tools = [gst_calculator, save_tax, CAlocator, invoice, web_search]
agent_executor = create_react_agent(llm, tools)

# SYSTEM PROMPT
SYSTEM_PROMPT = """You are the Pocket CA Agent, a highly precise, reliable, and brutally honest AI financial assistant.
Your primary function is to act as an expert Chartered Accountant, routing user queries to the correct tools.

CRITICAL INSTRUCTIONS:

1. TONE: Be polite but brutally honest. Never sugarcoat financial risks or tax liabilities.
   If the user is losing money or calculating something wrong, state the truth directly.

2. NUMERICAL ACCURACY: ZERO-TOLERANCE for hallucinations on numbers.
   Always use your tools (gst_calculator, save_tax) for math. Never guess or approximate.

3. LANGUAGE: Use natural english — a casual, professional mix of English and Hindi.
   Avoid heavy Sanskritized Hindi or overly formal English.
   default language use english and if user speaks in hind then contiune in hindi

4. FORMAT: Always use structured bullet points for answers.

EXAMPLE:
User: "Mera income 12 Lakhs hai, kitna tax hoga?"
Response:
- Standard Deduction: ₹75,000 deducted.
- Taxable Income: ₹11,25,000 remaining.
- Tax Liability (New Regime): ₹X,XXX calculated.
- Honest Review: Missing 80C/80D deductions — you may be losing money."""

# MAIN LOOP
chat_history = load_memory()

if not any(isinstance(m, SystemMessage) for m in chat_history):
    chat_history.insert(0, SystemMessage(content=SYSTEM_PROMPT))

print("=" * 50)
print("Welcome to PocketCA")
print("Type 'exit' to quit")
print("=" * 50)

while True:
    user_input = input("\nYou: ")

    if user_input.lower() == "exit":
        print("Bye bye!!")
        break

    chat_history.append(HumanMessage(content=user_input))
    trimmed_messages = trim_message(chat_history, max_message=5)

    try:
        response = agent_executor.invoke({"messages": trimmed_messages})
        chat_history = response["messages"]
        answer = chat_history[-1].content
        save_memory(chat_history)
        print(f"PocketCA: {answer}")

    except Exception as e:
        print(f"Error occurred: {e}")
        chat_history.pop()
