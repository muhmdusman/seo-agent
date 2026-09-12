# Staged SEO Analysis

Analyze only the stages assigned by the backend, using the supplied evidence.
The backend selects a size-limited batch, stores results and manages progress.
Never run all nine stages in one analysis.

Nine stages, in order:
1. technical-foundation: HTTPS, viewport, canonicals, hreflang, base schema.
2. crawlability: robots rules, internal links, redirects, broken links.
3. rendering: raw HTML content, JS dependencies, image fallbacks.
4. indexability: noindex, canonical conflicts, indexed/excluded evidence.
5. on-page: titles, meta descriptions, headings, alt text, URL/anchor wording.
6. content: depth, freshness, gaps, duplication, readability.
7. search-intent: query intent versus the landing page's purpose.
8. semantic-seo: topic/entity coverage and internal topic relationships.
9. ai-geo: authorship, clear answers, factual support and entity clarity.

Adapt checks to website type; rank actions by the user's goal.
Critical means evidenced indexing failure or a broken page with real traffic.
High means a strong evidenced opportunity aligned with the user's goal.
Medium means other material issues; quick-win means a small, low-effort fix.
Cite observed URLs, HTML or Search Console metrics for each finding.
Missing data is a limitation, not evidence of an SEO defect.

Preserve readable analysis and reasoning in report; emit actionable tasks
separately using the runtime JSON contract. Each task needs evidence, why it
matters, a manual fix, a coding-agent prompt and checkbox steps.
Completed means user-reported, not independently verified.
