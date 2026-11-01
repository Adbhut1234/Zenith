import os
import re
import json
import logging
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any, List
from livekit.agents import function_tool, RunContext
import ui_state

# Browser user agent for reliable web page scraping
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def _clean_slug(text: str) -> str:
    """Generate safe filename slug from topic."""
    s = re.sub(r'[^a-zA-Z0-9_\-\s]', '', text).strip()
    return re.sub(r'\s+', '_', s)[:40] or "Research_Report"

def _fetch_webpage_text(url: str, max_chars: int = 4000) -> str:
    """Fetch and scrape clean article text from a URL using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" in content_type:
                return "[PDF Document - Use read_pdf_document to view]"
            html = response.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")

            # Remove boilerplate and noise
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form"]):
                tag.extract()

            # Prefer main article container if present
            main = soup.find("article") or soup.find("main") or soup.find("div", {"class": re.compile(r"content|article|body|post", re.I)}) or soup.body
            if not main:
                return ""

            paragraphs = [p.get_text(strip=True) for p in main.find_all(["p", "h1", "h2", "h3", "li"])]
            text = "\n\n".join([p for p in paragraphs if len(p) > 20])
            return text[:max_chars].strip()
    except Exception as e:
        logging.debug(f"Failed to scrape webpage '{url}': {e}")
        return ""

def _fetch_wikipedia_summary(topic: str) -> Optional[Dict[str, str]]:
    """Fetch verified encyclopedic summary from Wikipedia API."""
    try:
        slug = urllib.parse.quote(topic.strip().replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
        req = urllib.request.Request(url, headers={"User-Agent": "ZenithResearch/2.0 (contact@zenith.ai)"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data and "extract" in data and data["extract"]:
                return {
                    "title": data.get("title", topic),
                    "extract": data.get("extract", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{slug}")
                }
    except Exception as e:
        logging.debug(f"Wikipedia lookup notice for '{topic}': {e}")
    return None

def _fetch_arxiv_papers_sync(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Query Arxiv API for academic and scientific research papers."""
    import xml.etree.ElementTree as ET
    results = []
    try:
        clean_q = urllib.parse.quote(query.strip())
        url = f"http://export.arxiv.org/api/query?search_query=all:{clean_q}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"
        req = urllib.request.Request(url, headers={"User-Agent": "ZenithResearch/2.0"})
        with urllib.request.urlopen(req, timeout=6) as response:
            xml_data = response.read().decode("utf-8")
            root = ET.fromstring(xml_data)
            atom_ns = "{http://www.w3.org/2005/Atom}"
            for entry in root.findall(f"{atom_ns}entry"):
                title_elem = entry.find(f"{atom_ns}title")
                summary_elem = entry.find(f"{atom_ns}summary")
                published_elem = entry.find(f"{atom_ns}published")
                authors = [a.find(f"{atom_ns}name").text for a in entry.findall(f"{atom_ns}author") if a.find(f"{atom_ns}name") is not None]

                pdf_url = ""
                for link in entry.findall(f"{atom_ns}link"):
                    if link.attrib.get("title") == "pdf":
                        pdf_url = link.attrib.get("href", "")
                    elif not pdf_url and "arxiv.org/abs" in link.attrib.get("href", ""):
                        pdf_url = link.attrib.get("href", "").replace("/abs/", "/pdf/") + ".pdf"

                title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else "Untitled"
                summary = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None and summary_elem.text else ""
                published = published_elem.text[:10] if published_elem is not None and published_elem.text else ""

                results.append({
                    "title": title,
                    "authors": ", ".join(authors[:3]),
                    "published": published,
                    "abstract": summary[:400] + ("..." if len(summary) > 400 else ""),
                    "pdf_url": pdf_url
                })
    except Exception as e:
        logging.warning(f"Arxiv query error: {e}")
    return results

def _search_ddg_multi(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Multi-backend search using direct ddgs, duckduckgo_search, or langchain fallback."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        pass

    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        pass
    return []

@function_tool()
async def deep_research(
    context: RunContext,  # type: ignore
    topic: str,
    focus: Optional[str] = None,
    save_report: bool = True
) -> str:
    """
    Perform deep AI-powered multi-source research on any topic, technology, market trend, person, or scientific question.
    Gathers real web articles, Wikipedia verified facts, extracts full page contents, synthesizes an executive research dossier using Gemini,
    and automatically saves a formatted Markdown research report to the user's Desktop.
    
    Use this when the user asks to 'research X', 'deep dive into X', 'investigate X', 'compile a report on X', or asks for thorough analysis.
    
    Args:
        topic: The research subject (e.g. 'Solid state battery breakthrough', 'Quantum supremacy 2026', 'Agentic AI frameworks comparison').
        focus: Optional specific perspective or angle (e.g. 'commercial viability', 'security implications', 'market leaders').
        save_report: If True (default), writes the complete research paper to ~/Desktop/Zenith_Research/<topic>.md.
    """
    ui_state.set_text(f"🌐 Deep Research | {topic[:20]}...")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Google API key is required to synthesize deep research briefings, Sir."

    # Step 1: Collect encyclopedic summary
    wiki_info = await asyncio.to_thread(_fetch_wikipedia_summary, topic)

    # Step 2: Query multiple search angles
    search_queries = [topic]
    if focus:
        search_queries.append(f"{topic} {focus}")
    else:
        search_queries.append(f"{topic} latest developments analysis")

    raw_results = []
    for q in search_queries:
        res = await asyncio.to_thread(_search_ddg_multi, q, 4)
        raw_results.extend(res)

    # Deduplicate results by URL
    seen_urls = set()
    unique_sources = []
    for r in raw_results:
        u = r.get("href") or r.get("link") or ""
        if u and u not in seen_urls and not u.endswith(".pdf"):
            seen_urls.add(u)
            unique_sources.append(r)

    # Step 3: Scrape full text from top 3 web pages asynchronously
    urls_to_scrape = [s.get("href") or s.get("link") for s in unique_sources[:3] if s.get("href") or s.get("link")]
    scraped_texts = await asyncio.gather(*[
        asyncio.to_thread(_fetch_webpage_text, u, 2500) for u in urls_to_scrape
    ], return_exceptions=True)

    # Build context package for Gemini
    collected_dossier = []
    if wiki_info:
        collected_dossier.append(
            f"--- WIKIPEDIA OVERVIEW ---\nTitle: {wiki_info['title']}\n{wiki_info['extract']}\nSource: {wiki_info['url']}"
        )

    for i, s in enumerate(unique_sources[:4]):
        u = s.get("href") or s.get("link") or ""
        t = s.get("title", "Source")
        snippet = s.get("body") or s.get("snippet") or ""
        page_body = ""
        if i < len(scraped_texts) and isinstance(scraped_texts[i], str) and scraped_texts[i].strip():
            page_body = f"\nExtracted Article Excerpt:\n{scraped_texts[i][:1800]}"
        collected_dossier.append(
            f"--- SOURCE {i+1}: {t} ---\nURL: {u}\nSnippet: {snippet}{page_body}"
        )

    context_str = "\n\n".join(collected_dossier)
    if not context_str.strip():
        return f"Unable to locate sufficient primary sources on '{topic}' at this time, Sir."

    # Step 4: Synthesize deep research dossier with Gemini
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)

        prompt = (
            f"You are Zenith's Deep Research Intelligence Engine. Conduct an exhaustive, high-level intelligence synthesis on:\n"
            f"TOPIC: {topic}\n"
            f"FOCUS: {focus or 'Comprehensive multi-dimensional analysis'}\n\n"
            f"SOURCE DOSSIER COLLECTED FROM LIVE WEB & ENCYCLOPEDIA:\n{context_str}\n\n"
            f"Create a professional, publication-grade research briefing formatted in Markdown:\n"
            f"1. **Executive Summary**: 2-3 crisp sentences capturing the core reality and importance.\n"
            f"2. **Key Findings & Breakthroughs**: 4-6 high-impact factual takeaways with concrete numbers/dates.\n"
            f"3. **In-Depth Analytical Breakdown**: Rigorous explanation of mechanisms, dynamics, challenges, and competing viewpoints.\n"
            f"4. **Strategic Outlook & Next Horizon**: What happens next, timeline, predictions.\n"
            f"5. **Verified Sources & Citations**: List of relevant source URLs from the dossier.\n\n"
            f"Maintain an authoritative, precise, and sophisticated tone. Avoid generic fluff."
        )

        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.35)
        )
        report_text = resp.text.strip() if resp and resp.text else ""
        if not report_text:
            return f"Failed to synthesize research dossier for '{topic}'."

        # Step 5: Save report to user's Desktop
        saved_path_msg = ""
        if save_report:
            try:
                user_home = os.path.expanduser("~")
                out_dir = os.path.join(user_home, "Desktop", "Zenith_Research")
                os.makedirs(out_dir, exist_ok=True)
                slug = _clean_slug(topic)
                stamp = datetime.now().strftime("%Y%m%d_%H%M")
                report_file = os.path.join(out_dir, f"{slug}_{stamp}.md")

                file_header = (
                    f"# Zenith Deep Research Intelligence Report\n"
                    f"**Topic**: {topic}\n"
                    f"**Generated**: {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}\n"
                    f"**Synthesized By**: Zenith AI Deep Research Engine\n"
                    f"---\n\n"
                )
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(file_header + report_text)
                saved_path_msg = f"\n\n📁 Complete research document archived to: Desktop/Zenith_Research/{os.path.basename(report_file)}"
                logging.info(f"Deep research saved to {report_file}")
            except Exception as save_err:
                logging.warning(f"Failed to auto-save research report to Desktop: {save_err}")

        # Provide a crisp executive summary for voice playback, referencing saved report
        ui_state.set_text(f"🌐 Research Complete | {topic[:18]}")
        return f"=== ZENITH DEEP RESEARCH: {topic.upper()} ===\n\n{report_text}{saved_path_msg}"

    except Exception as e:
        logging.error(f"Error during deep_research synthesis: {e}", exc_info=True)
        return f"Deep research failed due to an error: {str(e)}"

@function_tool()
async def search_academic_papers(
    context: RunContext,  # type: ignore
    query: str,
    max_results: int = 5
) -> str:
    """
    Search Arxiv for published scientific, computer science, physics, mathematics, and AI research papers.
    Returns paper titles, primary authors, publication date, abstract summary, and direct PDF download links.
    
    Args:
        query: Academic topic or paper title (e.g. 'Transformer reasoning architecture', 'Quantum error correction', 'Diffusion models').
        max_results: Number of papers to retrieve (default 5).
    """
    ui_state.set_text(f"📚 Arxiv Papers | {query[:20]}...")
    papers = await asyncio.to_thread(_fetch_arxiv_papers_sync, query, min(max_results, 8))
    if not papers:
        return f"No academic papers found on Arxiv matching '{query}', Sir."

    formatted = [f"=== Academic Research Papers on '{query}' (via Arxiv) ===\n"]
    for i, p in enumerate(papers, 1):
        formatted.append(
            f"{i}. **{p['title']}**\n"
            f"   - Authors: {p['authors']} | Date: {p['published']}\n"
            f"   - Abstract: {p['abstract']}\n"
            f"   - PDF: {p['pdf_url']}\n"
        )
    return "\n".join(formatted)
