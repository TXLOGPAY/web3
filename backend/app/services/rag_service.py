"""RAG service using LlamaIndex + Anthropic to extract trade data from invoices."""
import io
import re
import json
from pathlib import Path
from typing import Optional

import structlog
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings as LISettings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.config import settings
from app.services.merkle_tree import build_trade_merkle_tree

log = structlog.get_logger()

# LlamaIndex global settings
LISettings.llm = Anthropic(
    model="claude-sonnet-4-6",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=4096,
)
LISettings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
LISettings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)

# ─── Extraction prompt ────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """
You are an expert in international trade documentation (Brazilian Siscomex, invoices, BL).
Extract the following fields from the provided document and return a valid JSON object:

{
  "invoice_number": "string or null",
  "bill_of_lading": "string or null",
  "exporter": "company name or null",
  "importer": "company name or null",
  "incoterm": "EXW|FCA|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP or null",
  "product_description": "string or null",
  "hs_code": "NCM/HS code or null",
  "quantity": number or null,
  "unit": "KG|TON|UN|M3|etc or null",
  "unit_price_usd": number or null,
  "total_value_usd": number or null,
  "currency": "USD|EUR|BRL|CNY|etc",
  "origin_country": "ISO country code or name",
  "dest_country": "ISO country code or name",
  "siscomex_id": "string or null"
}

Rules:
- Return ONLY the JSON object, no explanations.
- Use null for missing fields.
- Convert values to numeric types where applicable.
- For hs_code, extract the NCM/HS code if present.

Document content:
{document_text}
"""


async def extract_invoice_data(file_bytes: bytes, filename: str) -> dict:
    """
    Process an uploaded invoice (PDF/DOCX/TXT) through RAG pipeline.
    Returns extracted trade data + Merkle root.
    """
    log.info("rag_extraction_start", filename=filename)

    # Save to temp file for LlamaIndex reader
    import tempfile
    import os

    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # Load document
        reader = SimpleDirectoryReader(input_files=[tmp_path])
        docs = reader.load_data()
        full_text = "\n\n".join(doc.text for doc in docs)

        # Build index for RAG
        index = VectorStoreIndex.from_documents(docs)
        query_engine = index.as_query_engine()

        # Use LLM to extract structured data
        llm = Anthropic(
            model="claude-sonnet-4-6",
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=4096,
        )

        prompt = EXTRACTION_PROMPT.replace("{document_text}", full_text[:8000])
        response = llm.complete(prompt)
        raw_json = response.text.strip()

        # Parse JSON from response
        json_match = re.search(r"\{.*\}", raw_json, re.DOTALL)
        if not json_match:
            raise ValueError("LLM did not return valid JSON")

        extracted: dict = json.loads(json_match.group())
        extracted["raw_text"] = full_text[:2000]

        # Build Merkle tree from extracted data
        trade_payload = {k: v for k, v in extracted.items() if k != "raw_text" and v is not None}
        tree = build_trade_merkle_tree(trade_payload)
        extracted["merkle_root"] = tree.root_hex
        extracted["merkle_leaves"] = tree.leaves_raw

        log.info("rag_extraction_done", invoice=extracted.get("invoice_number"), merkle=tree.root_hex)
        return extracted

    finally:
        os.unlink(tmp_path)


async def extract_invoice_text_only(file_bytes: bytes, filename: str) -> str:
    """Extract raw text from a document without LLM processing."""
    import tempfile
    import os

    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        reader = SimpleDirectoryReader(input_files=[tmp_path])
        docs = reader.load_data()
        return "\n\n".join(doc.text for doc in docs)
    finally:
        os.unlink(tmp_path)
