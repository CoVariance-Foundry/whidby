"""Prompt template for search intent classification. (Algo Spec V1.1, §4.4)"""

SYSTEM = (
    "You classify search queries by intent. Respond with valid JSON only. "
    "No commentary or explanation."
)

USER_TEMPLATE = """\
Classify the following search query's intent as exactly one of:
  - "transactional": searcher wants to hire or buy NOW
  - "commercial": searcher is evaluating options
  - "informational": searcher wants to learn something

Query: "{query}"

Respond with: {{"intent": "<transactional|commercial|informational>"}}\
"""


def build_prompt(query: str) -> str:
    return USER_TEMPLATE.format(query=query)
