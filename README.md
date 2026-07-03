# PocketCA Pro

**A conversational GST invoicing and bookkeeping assistant for Indian small businesses, built on a LangGraph ReAct agent.**

🔗 **Live demo:** [pocketca-f6bt3bbtuf9mhxchtsg8bb.streamlit.app](https://pocketca-f6bt3bbtuf9mhxchtsg8bb.streamlit.app/)

---

## What it does

PocketCA Pro lets a small business owner describe a sale or purchase in plain, informal language — including regional shorthand like "lakhs," "k," or common product misspellings — and turns it into a structured invoice with GST correctly calculated and split into CGST/SGST, ready to download as a PDF.

The core design decision: **the LLM never does the math.** It parses intent and extracts entities (amount, item, tax slab), then hands off to a deterministic Python calculator for the actual GST computation. This avoids the classic failure mode of language models silently getting arithmetic wrong.

**Example flow:**
> "Sold 3 units of rice at 2.5k each, 5% GST"
→ agent parses amount, quantity, tax slab → calculator computes base cost, GST split, total → PDF invoice generated → download link appears in the sidebar.

---

## Architecture

![Architecture Diagram](assets/architecture_diag.png)

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                        │
│              (custom CSS, sidebar, chat interface)            │
└───────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph ReAct Agent                        │
│                 (Groq — Llama 3.1 8B)                          │
│                                                                 │
│   Reads conversation state → decides if a tool call is        │
│   needed → invokes tool → reads tool output → responds        │
└──────┬──────────────────┬──────────────────┬─────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ GST          │  │ Chroma RAG        │  │ PDF Generator    │
│ Calculator   │  │ (policy lookup)   │  │ (ReportLab)       │
│ (tools.py)   │  │                   │  │                  │
│              │  │ tax_saving.pdf    │  │ Renders invoice  │
│ Deterministic│  │ → chunked →       │  │ to A4 canvas,    │
│ tax-bracket  │  │ HuggingFace       │  │ saves to disk,   │
│ math, no LLM │  │ embeddings        │  │ session_state    │
│ involved     │  │ (all-MiniLM-L6-v2)│  │ picks up latest  │
│              │  │ → ChromaDB        │  │ file via glob    │
└─────────────┘  └──────────────────┘  └─────────────────┘
```

**Flow notes:**
- The agent and the GST calculator are tightly coupled (calculator output drives the invoice numbers directly). The Chroma RAG layer is a **separate retrieval path** used for answering general tax/policy questions — it does not feed into or override the calculator's output.
- Once a tool call confirms an invoice was generated, the app scans the working directory for the most recent timestamped PDF, stores its path in `st.session_state`, and triggers `st.rerun()` to surface a download button in the sidebar.

---

## Tech stack

| Layer | Tool | Purpose |
|---|---|---|
| UI | Streamlit + `streamlit_option_menu` | Chat interface, custom dark-theme CSS, sidebar navigation |
| Agent orchestration | LangGraph | Cyclical ReAct loop (reason → act → observe) |
| LLM | Groq API — Llama 3.1 8B | Fast inference for entity parsing and conversational responses |
| Retrieval | ChromaDB + HuggingFace `all-MiniLM-L6-v2` (384-dim) | Semantic search over local tax policy PDFs |
| Document loading | `PyPDFLoader`, `WebBaseLoader` | Ingests local PDFs and web-sourced policy pages |
| Chunking | `RecursiveCharacterTextSplitter` | Splits documents for embedding |
| Tax computation | Custom Python (`tools.py`) | Deterministic GST slab logic (0/5/12/18/28%), CGST/SGST split |
| PDF generation | ReportLab (`Canvas`) | Renders invoice directly to a vector PDF, no HTML-to-PDF conversion |
| Fallback search | DuckDuckGo Search | Backup lookup when local retrieval has no match |

---

## Project structure

```
POCKET_CA_PRO/
├── assets/
│   └── architecture_diag.png
├── config/
│   └── ledger_settings.json      # tax slab config, invoice formatting defaults
├── data/
│   └── tax_saving.pdf            # source document for RAG ingestion
├── src/
│   ├── agent.py                  # LangGraph ReAct agent definition
│   ├── tools.py                  # GST calculator + tool-decorated functions
│   ├── utils.py                  # helper functions (parsing, formatting)
│   └── __init__.py
├── workflows/                    # LangGraph graph/state definitions
├── app.py                        # Streamlit entrypoint
├── requirements.txt
└── README.md
```

---

## Running locally

```bash
git clone https://github.com/shakshi-soni/POCKET_CA_PRO.git
cd POCKET_CA_PRO
pip install -r requirements.txt
```

Set your Groq API key as an environment variable:

```bash
export GROQ_API_KEY="your-key-here"
```

Then run:

```bash
streamlit run app.py
```

---

## Known limitations

Being upfront about scope, since this is a learning project rather than a production system:

- **Free-tier dependencies.** The app runs on Groq's free API tier and Streamlit Community Cloud, both of which are rate-limited and can idle out — expect occasional latency or timeouts, particularly after a period of inactivity.
- **RAG scope.** The Chroma retrieval layer answers general policy questions from the ingested PDF; it is not wired into the GST calculator's decision logic.
- **Entity parsing coverage.** Regional-term normalization ("lakhs," "k," informal spellings) is handled via prompt instructions to the LLM rather than a dedicated NLP pipeline, so accuracy depends on how close an input is to the patterns it's been tested against.
- **No authentication or multi-user support.** Session state is local to a single browser session; there's no persistent user accounts or invoice history across sessions yet.
- **PDF output is not encrypted.** "Secure" here refers to clean vector rendering (not rasterized/corrupted output), not access control or password protection.

---

## Roadmap

- [ ] Wire RAG retrieval into calculator context for slab verification against source documents
- [ ] Add invoice history / persistent storage (currently session-only)
- [ ] Expand regional term normalization with a tested phrase bank
- [ ] Add automated tests for the GST calculator edge cases

---

## Author

Built by [shakshi-soni](https://github.com/shakshi-soni) as part of ongoing work in agentic AI systems.
