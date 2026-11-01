import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from livekit.agents import function_tool, RunContext
import ui_state

def _resolve_target_path(filepath: str) -> Optional[str]:
    """Helper to locate a file path on the PC (handles ~ and common folders)."""
    p = os.path.expanduser(filepath.strip().strip('"').strip("'"))
    if os.path.isabs(p) and os.path.exists(p):
        return p
    if os.path.exists(p):
        return os.path.abspath(p)

    user_home = os.path.expanduser("~")
    search_dirs = [
        os.getcwd(),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "Documents")
    ]
    base_name = os.path.basename(p)
    for d in search_dirs:
        candidate = os.path.join(d, base_name)
        if os.path.exists(candidate):
            return candidate
            
    # Fuzzy match in Desktop and Downloads if user specified partial name
    for d in [os.path.join(user_home, "Desktop"), os.path.join(user_home, "Downloads")]:
        if os.path.exists(d):
            try:
                for f in os.listdir(d):
                    if base_name.lower() in f.lower():
                        return os.path.join(d, f)
            except Exception:
                pass
    return None

def extract_pdf_data(filepath: str, page_number: Optional[int] = None, max_pages: int = 15) -> Dict[str, Any]:
    """Extract text, metadata, and page contents from a PDF file using pypdf."""
    import pypdf
    result: Dict[str, Any] = {
        "success": False,
        "total_pages": 0,
        "pages": {},
        "metadata": {},
        "full_text": "",
        "error": None
    }
    try:
        reader = pypdf.PdfReader(filepath)
        total_pages = len(reader.pages)
        result["total_pages"] = total_pages

        # Extract document info metadata
        if reader.metadata:
            meta = {}
            for k, v in reader.metadata.items():
                if v:
                    clean_k = str(k).replace("/", "")
                    meta[clean_k] = str(v)
            result["metadata"] = meta

        # Extract specific page or range
        pages_to_read = []
        if page_number is not None:
            # 1-indexed for users
            target_idx = page_number - 1
            if 0 <= target_idx < total_pages:
                pages_to_read = [target_idx]
            else:
                result["error"] = f"Page {page_number} is out of range. Document has {total_pages} page(s)."
                return result
        else:
            limit = min(total_pages, max(1, max_pages))
            pages_to_read = list(range(limit))

        extracted_parts = []
        for idx in pages_to_read:
            page = reader.pages[idx]
            txt = page.extract_text() or ""
            clean_txt = "\n".join([line.strip() for line in txt.splitlines() if line.strip()])
            result["pages"][idx + 1] = clean_txt
            if clean_txt:
                extracted_parts.append(f"--- PAGE {idx + 1} of {total_pages} ---\n{clean_txt}")

        result["full_text"] = "\n\n".join(extracted_parts)
        result["success"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result

def extract_docx_data(filepath: str, max_paragraphs: int = 150) -> Dict[str, Any]:
    """Extract text from Microsoft Word (.docx) files using python-docx."""
    import docx
    result: Dict[str, Any] = {"success": False, "full_text": "", "error": None}
    try:
        doc = docx.Document(filepath)
        lines = []
        for p in doc.paragraphs:
            if p.text.strip():
                lines.append(p.text.strip())
                if len(lines) >= max_paragraphs:
                    break
        # Also extract table text if present
        for t in doc.tables:
            for row in t.rows:
                row_txt = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_txt:
                    lines.append(f"[Table Row]: {row_txt}")
        result["full_text"] = "\n\n".join(lines)
        result["success"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result

@function_tool()
async def read_pdf_document(
    context: RunContext,  # type: ignore
    filepath: str,
    page_number: Optional[int] = None,
    max_pages: int = 10,
    question: Optional[str] = None
) -> str:
    """
    Read, inspect, search, and analyze PDF documents on the user's PC (e.g. resumes, reports, research papers, invoices, manuals).
    Use this whenever the user asks to read a PDF file, check what is inside a PDF, find specific information in a PDF, or summarize a PDF.
    
    Args:
        filepath: Full path or filename of the PDF (e.g. 'resume.pdf', 'report.pdf', 'C:/Users/user/Downloads/paper.pdf').
        page_number: Optional 1-indexed specific page to read (e.g. 1 for first page).
        max_pages: Number of pages to read from start if page_number is not given (default 10).
        question: Optional specific question or topic to answer using the PDF contents (uses Gemini AI for accurate answer).
    """
    try:
        resolved = _resolve_target_path(filepath)
        if not resolved:
            return f"Could not find PDF file '{filepath}'. Please check the filename or location, Sir."

        ui_state.set_text(f"📄 Reading PDF | {os.path.basename(resolved)[:18]}...")
        data = await asyncio.to_thread(extract_pdf_data, resolved, page_number, max_pages)
        if not data["success"]:
            return f"Error reading PDF '{os.path.basename(resolved)}': {data.get('error', 'Unknown extraction failure')}"

        total_pages = data["total_pages"]
        content = data["full_text"]

        if not content.strip():
            return f"The PDF '{os.path.basename(resolved)}' ({total_pages} pages) appears to contain only scanned images or empty pages with no selectable text."

        # If user asked a specific question, synthesize answer with Gemini
        if question and question.strip():
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                try:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(api_key=api_key)
                    prompt = (
                        f"You are Zenith AI, an elite assistant. Answer the user's question accurately using ONLY the provided PDF document text.\n\n"
                        f"Document Name: {os.path.basename(resolved)}\n"
                        f"Total Pages: {total_pages}\n"
                        f"User's Question: {question}\n\n"
                        f"Document Content Excerpt:\n{content[:25000]}\n\n"
                        f"Provide a clear, direct, and well-structured answer with specific details or citations to page numbers where applicable."
                    )
                    resp = await client.aio.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.2)
                    )
                    if resp and resp.text:
                        return f"PDF Analysis for '{os.path.basename(resolved)}' (Total Pages: {total_pages}):\n\n{resp.text}"
                except Exception as ai_err:
                    logging.warning(f"Gemini Q&A failed for PDF, falling back to raw excerpt: {ai_err}")

        # Return structured text
        header = f"=== Document: {os.path.basename(resolved)} (Total Pages: {total_pages}) ===\n"
        if data["metadata"]:
            meta_str = ", ".join([f"{k}: {v}" for k, v in list(data["metadata"].items())[:3]])
            header += f"Metadata: {meta_str}\n\n"
        else:
            header += "\n"

        # Truncate content to comfortable reading length for voice / display (first 3500 chars)
        if len(content) > 3500:
            preview = content[:3500] + f"\n\n[... Remaining content truncated. Total {total_pages} page(s) in document. Ask for specific pages or questions to read further.]"
        else:
            preview = content

        return f"{header}{preview}"
    except Exception as e:
        logging.error(f"Error in read_pdf_document: {e}", exc_info=True)
        return f"Failed to inspect PDF '{filepath}': {str(e)}"
