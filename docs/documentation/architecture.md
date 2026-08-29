# Architecture

The source tree follows an onion-style separation:

- `accounting.domain` contains Pydantic models and accounting validation rules.
- `accounting.application` contains repository interfaces and `AccountingService`.
- `accounting.infrastructure` is present as a package but currently has no implementation.
- No presentation or CLI layer is currently configured.

The application service depends on a supplied repository object rather than a concrete database. This keeps transaction validation separate from persistence.
