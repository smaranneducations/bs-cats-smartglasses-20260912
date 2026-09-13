# Domain portability contract

The engine is the product. SmartGlasses is the active replaceable domain pack and first commercial experiment, not a hard-coded system identity.

A domain pack supplies entity identity, ontology namespace, source classes, buyer jobs, content lenses, agent workflow roles, media policy, commercial paths and presentation channels. It contains no credentials and cannot expand engine permissions or budgets. Shared services retain object versioning, evidence lineage, task leases, exception routing, cost admission, dependency invalidation, admin supervision, audience interaction, rendering and publication controls.

Replacing SmartGlasses with air conditioners must create a new versioned domain pack and migration/compatibility decision, then switch `config/active-domain.json`. It must not fork the engine, create a second control plane, rename generic objects, copy secrets, or reuse smart-glasses meanings. Domain-specific extractors and definitions remain adapters behind the same contracts.

The active profile is exposed at `/v1/intelligence/domain`. This foundation does not by itself prove every existing SmartGlasses adapter is generic; remaining adapters must be moved behind the domain profile before portability is declared complete.
