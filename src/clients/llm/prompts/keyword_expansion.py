"""Prompt template for keyword expansion. (Algo Spec V1.1, §4.2)"""

SYSTEM = (
    "You are a local SEO keyword research expert. You help rank-and-rent "
    "practitioners find the keywords that real customers use to find local "
    "service businesses. Output valid JSON only — no commentary."
)

USER_TEMPLATE = """\
Given the local service niche '{niche}', generate:
  a) 3-5 core service terms (the primary things customers search for)
  b) 3-5 high-intent modifiers (emergency, 24 hour, affordable, best, near me)
  c) 3-5 specific sub-services (the most commonly needed jobs)

For each keyword, classify the search intent as one of:
  - transactional: searcher wants to hire/buy NOW (e.g., 'emergency plumber near me')
  - commercial: searcher is evaluating options (e.g., 'best plumber in phoenix')
  - informational: searcher wants to learn (e.g., 'how to fix a leaky faucet')

EXCLUDE informational queries — they are vulnerable to AI Overviews
and do not generate leads for rank-and-rent sites.

Assign each keyword a tier:
  - 1 (Head): generic niche term, niche + near me, niche + city
  - 2 (Service): sub-service or modifier + niche
  - 3 (Long-tail): problem description, specific job

Assign aio_risk: "low" for transactional, "moderate" for commercial, "high" for informational.

Output as JSON matching this schema:
{{
  "niche": "{niche}",
  "expanded_keywords": [
    {{"keyword": "...", "tier": 1, "intent": "transactional", "source": "llm", "aio_risk": "low"}}
  ],
  "total_keywords": <int>,
  "actionable_keywords": <int>,
  "informational_keywords_excluded": <int>,
  "expansion_confidence": "high" | "medium" | "low"
}}

Only include terms a real customer would search.
Do not include business-side terms (franchise, training, certification).\
"""


def build_prompt(niche: str) -> str:
    return USER_TEMPLATE.format(niche=niche)
