# Frontend (HTMX/SSR) Architecture & AI Agents Context

This document outlines the architecture of the frontend layer within the BHub project, specifically focusing on how UI interactions are orchestrated and how AI-driven features are surfaced to the client.

## 1. Architectural Paradigm
The frontend does **not** use a Heavy-SPA framework (like React or Angular). Instead, it embraces **Hypermedia-Driven Applications (HDA)**.
- **Backend-Driven UI (FastAPI & Jinja2):** The server is the single source of truth for state and routing. UI components are generated server-side.
- **Progressive Enhancement (HTMX):** HTMX intercepts interactions (clicks, submits) and swaps out specific DOM fragments with HTML payloads returned by the server.
- **Hybrid Styling (Tailwind + CSS Variables):** Tailwind is used for structural utility classes, while semantic CSS classes and variables (`app/static/css/design-tokens.css`) manage themes and complex component states.

## 2. Dynamic Interactions & State
- **Smart Routing:** The `app/web/routes.py` dynamically checks for the `HX-Request` header. This allows the same endpoint to serve a full page layout on a direct visit or just a partial HTML modal/fragment during an HTMX request.
- **Client-Side Scripting:** Vanilla JavaScript and lightweight libraries (Anime.js for stagger animations, Marked.js for markdown rendering) are used strictly for visual enhancements and interactions that do not require server state.

## 3. Serving AI Features to the Client
The frontend seamlessly integrates the intelligent fallback orchestration (described in the backend `agents.md`) by keeping the client unaware of the AI provider complexities:
1. **Translations:** When a user requests an article translation, HTMX triggers a POST request to the translation endpoint. The server orchestrates the AI request (trying DeepSeek, then Phi-3 locally) and streams the result back as parsed HTML fragments.
2. **Markdown Parsing:** AI outputs are often markdown. The UI handles this via `marked.js` on the client or pre-parsing on the server, injecting the result into heavily styled Prose components.
3. **Graceful Degradation:** If the AI layer fails or is processing, the frontend uses HTMX indicators (`hx-indicator`) to show loaders, preventing UI blocking.

## 4. Development Guidelines
- **No Inline Scripts:** Avoid writing JavaScript directly inside Jinja templates. Place interaction logic in `app/static/js/`.
- **Declarative HTMX:** Always prefer declarative HTMX attributes (`hx-get`, `hx-target`) over writing manual `htmx.ajax` calls in JavaScript.
- **Design Tokens:** Follow the established design system variables for colors and spacing instead of hardcoding arbitrary Tailwind values.
- **Iconography:** Standardize on Lucide icons via backend helpers rather than pasting raw SVGs into templates.