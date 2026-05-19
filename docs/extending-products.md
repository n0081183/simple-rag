# Extending products in domain knowledge

Products in the UI are **dynamic** — read from `manifest.json` / LanceDB metadata after KB sync.

To improve retrieval and verification for a new Cortex product:

1. Ensure `cortex-docs-sync` merge rules map FluidTopics labels to a directory (see upstream `catalog.py`).
2. Rebuild KB including that product directory.
3. Add entries to:
   - `backend/app/core/domain_knowledge/product_facts.py` — `ARCHITECTURE_FACTS`
   - `backend/app/core/domain_knowledge/synonyms.py` — `SYNONYMS`
   - `backend/app/core/domain_knowledge/term_mapping.py` — `TERM_MAPPING`
4. Add gold-set cases in `eval/gold_set.json` and run `make eval`.

Product capsules for auto-detect are generated at index build time into `product_capsules.json`.
