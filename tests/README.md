# Zenith Diagnostic & Verification Test Suite

This directory contains standalone diagnostic test harnesses, hardware validation tools, and cognitive verification suites for Zenith.

## 📋 Available Tests

| Test Script | npm Script | Description |
|---|---|---|
| [`test_browser_agent.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_browser_agent.py) | `npm run test:browser`<br>`npm run login:browser` | Tests the autonomous web agent. Use `--login` mode to sign in to persistent browser sessions (Google, GitHub, etc.). |
| [`test_mic.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_mic.py) | `npm run test:mic` | Audio input device diagnostic. Tests recording levels with a live volume meter. |
| [`test_code_phasing.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_code_phasing.py) | `npm run test:phasing` | Validates AST code scanning and symbol indexing. |
| [`test_deep_thinker.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_deep_thinker.py) | `npm run test:thinker` | Tests multi-perspective cognitive reasoning and decision trees. |
| [`test_council_and_dream.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_council_and_dream.py) | `npm run test:council` | Tests dialectical Council of Overlays and idle Dream Cycle synthesis. |
| [`test_procedural_memory.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_procedural_memory.py) | `npm run test:procedural` | Verifies procedural memory playbooks and reflection logs. |
| [`test_phase1_vision.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_phase1_vision.py) | `npm run test:vision` | Verifies native desktop screen streaming via DesktopCapturer. |
| [`test_phase2_som.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_phase2_som.py) | `npm run test:som` | Verifies Set-of-Marks (SoM) visual badge detection & coordinate snapping. |
| [`test_phase3_swarm.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_phase3_swarm.py) | `npm run test:swarm` | Verifies background worker swarm and parallel task dispatch. |
| [`test_phase4_ambient.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_phase4_ambient.py) | `npm run test:ambient` | Verifies clipboard error watchers and process completion monitoring. |
| [`test_phase5_shell.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_phase5_shell.py) | `npm run test:shell` | Verifies persistent PowerShell session & self-healing action loops. |
| [`test_phase6_rag.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_phase6_rag.py) | `npm run test:rag` | Verifies local semantic graph memory, dual-engine embeddings & RRF RAG. |
| [`test_vision_cognitive_suite.py`](file:///d:/Projects/friday_jarvis2-main/tests/test_vision_cognitive_suite.py) | `.\venv\Scripts\python tests\test_vision_cognitive_suite.py` | Full integrated suite for all cognitive architecture modules. |

## 🚀 Running Tests

You can run any test from the root directory via npm:

```bash
npm run test:mic
npm run test:browser
npm run test:phasing
```

Or run directly with the virtual environment Python:

```powershell
.\venv\Scripts\python tests\test_code_phasing.py
```
