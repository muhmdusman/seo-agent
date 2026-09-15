"""The canonical nine-stage SEO framework and its supporting review lenses."""

from typing import Final


SEO_STAGES: Final[tuple[str, ...]] = (
    "technical-foundation", "crawlability", "rendering", "indexability",
    "on-page", "content", "search-intent", "semantic-seo", "ai-geo",
)

STAGE_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "A": SEO_STAGES[:4],
    "B": SEO_STAGES[4:6],
    "C": SEO_STAGES[6:8],
    "D": SEO_STAGES[8:],
}

# These are lenses inside the nine stages, not additional workflow stages.
STAGE_FRAMEWORKS: Final[dict[str, tuple[str, ...]]] = {
    "technical-foundation": (
        "HTTPS, status and security headers, viewport, canonical basics",
        "local-seo: LocalBusiness schema, NAP consistency and service-area signals",
        "ecommerce: product, offer and organization fundamentals",
        "international-seo: language/region ownership and hreflang prerequisites",
    ),
    "crawlability": (
        "robots.txt, XML sitemaps, redirect chains, broken links and orphan-page evidence",
        "internal-linking: discoverability, hierarchy and important-page paths",
        "ecommerce: faceted navigation, pagination and parameter traps",
        "international-seo: locale paths and crawlable alternate-language routes",
    ),
    "rendering": (
        "raw HTML versus rendered or user-visible content, JavaScript dependencies and mobile layout",
        "ecommerce: client-rendered product, price and availability content",
        "internal-linking: links present in the delivered HTML, not only after interaction",
    ),
    "indexability": (
        "noindex, x-robots-tag, canonical conflicts, duplicate parameters and sitemap/index gaps",
        "international-seo: hreflang reciprocity and canonical alignment across locales",
        "ecommerce: variant, filter and duplicate product URL policy",
    ),
    "on-page": (
        "titles, meta descriptions, heading hierarchy, alt text, URLs, anchors and OG tags",
        "local-seo: location/service wording, contact details and local entity signals",
        "ecommerce: product/category attributes, price, availability and structured page copy",
        "international-seo: language quality and locale-specific metadata",
    ),
    "content": (
        "depth, freshness, useful coverage, thin/duplicate content and scannability",
        "competitor-analysis: compare only fetched competitor evidence, never inferred weaknesses",
        "competitor-research: identify evidence-backed content gaps and worthwhile research tasks",
        "local-seo and ecommerce: service-area, category, product and buyer-decision coverage",
    ),
    "search-intent": (
        "query/page alignment, striking-distance opportunities, high-impression low-CTR pages and conversion intent",
        "competitor-analysis: compare query intent only where competitor pages were fetched",
        "local-seo: local query modifiers, service-area intent and visitor action",
    ),
    "semantic-seo": (
        "entities, topical coverage, pillar/supporting-page relationships and sameAs signals",
        "internal-linking: contextual anchors and authority paths between related pages",
        "competitor-research: evidence-backed entity and topic gaps",
        "ecommerce and international-seo: product taxonomy and locale entity consistency",
    ),
    "ai-geo": (
        "clear answers, E-E-A-T signals, citable density, brand clarity, FAQ/HowTo suitability and AI crawler access",
        "competitor-analysis: compare answer clarity and evidence only from fetched pages",
        "opportunities: additional visibility experiments after the nine-stage framework is covered",
    ),
}

STAGE_CAPS: Final[dict[str, int]] = {
    "1-10": 4,
    "11-30": 3,
    "31-100": 2,
    "101-300": 1,
    "301+": 1,
}


def next_stage_bundle(covered: set[str], website_size: str) -> list[str]:
    """Return the next sequential core stages for a bounded framework run."""
    remaining = [stage for stage in SEO_STAGES if stage not in covered]
    return remaining[:STAGE_CAPS[website_size]]


def stage_group(stage: str) -> str:
    for group, stages in STAGE_GROUPS.items():
        if stage in stages:
            return group
    raise ValueError(f"Unknown SEO framework stage: {stage}")
