from app.core.domain_knowledge.synonyms import expand_query
from app.core.domain_knowledge.product_facts import get_architecture_facts, get_domain_knowledge_prompt
from app.core.domain_knowledge.term_mapping import get_relevant_terms_for_requirement, translate_term

__all__ = [
    "expand_query",
    "get_architecture_facts",
    "get_domain_knowledge_prompt",
    "get_relevant_terms_for_requirement",
    "translate_term",
]
