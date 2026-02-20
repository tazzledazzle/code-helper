# Code Helper

Single-user AI code helper: explain code, answer questions (with web search), suggest edits, generate/refactor code, run tests, and verify. Uses a **CrewAI** hierarchical crew (Manager → Researcher, Coder, Runner), **hybrid RAG** (persistent project index + paste/attach), and **self-hosted LLM** in Kubernetes.

**Components:** Crew API (FastAPI + CrewAI), Runner service, Ingest (K8s Job), Vector DB (Chroma), Chat UI, CLI.

**Design:** [docs/plans/2026-02-20-hierarchical-multi-agent-code-helper-design.md](../docs/plans/2026-02-20-hierarchical-multi-agent-code-helper-design.md)
