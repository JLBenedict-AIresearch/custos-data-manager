## Custos Data Manager
Custos Data Manager is an event-driven ETL (Extract, Transform, Load) pipeline designed for robustness, data integrity, and extensibility.

It utilizes Watchdog and APScheduler for real-time and scheduled detection of incoming CSV files. Data undergoes an initial rapid audit via Pandas, followed by strict validation using Pydantic and SQLAlchemy ORM models. Validated rows are persisted to a PostgreSQL database in atomic batches, while invalid rows are safely routed to a quarantine directory for manual review.

Out of the box, Custos is configured to process and manage Leads and FactSales in a Star Schema (with Product, Customer, and Date Dimensions), but its architecture is designed to be domain-agnostic. Additional domains can be added to registry configuration with zero or minimal changes to the pipeline handlers.

### Key Features
- **Decoupled & Agnostic Architecture:** Tools and libraries are integrated via clean abstraction layers. Domain-specific class objects, helper functions, and mapping keys are configured dynamically via a registry rather than being hard-coded, allowing for the seamless addition of new data domains.

- **Security & PII Protection**: Verifies true file MIME types prior to ingesting ostensible CSVs. Personally Identifiable Information (PII) is secured at rest using Fernet encryption.

- **Strict Idempotency:** Prevents duplicate processing by hashing and comparing incoming files against a processed registry. Batch persistence is made atomic using the Unit of Work pattern, bolstered by thorough idempotency checks across the database, identity maps, and in-memory entities before any data is committed.

- **Automated Update Management:** Safely handles field updates by storing contributions as historical "snapshots" with full context. Chronological update logic is automated to protect against stale data and ensure accurate entity states.

- **Resilience & Observability:** Features comprehensive event logging, custom domain exceptions, infrastructure safety wrappers, and automated alerts for system fault events.

- **Extensible Processing:** Fully compatible with message brokers and external background workers. Currently leverages APScheduler for cron jobs and includes built-in mock email alerts for system notifications.

- **Production-Ready Testing:** Backed by a comprehensive Pytest suite containing 86 unit, integration, and end-to-end tests, currently sitting at 100% passing with 89% total code coverage.

### Tech Stack
- **Core:** Python

- **Persistence:** PostgreSQL, SQLAlchemy (ORM)

- **Validation & Auditing:** Pydantic, Pandas

- **File Monitoring & Scheduling:** Watchdog, APScheduler

- **Testing:** Pytest, pytest-cov

- **Security:** Cryptography (Fernet), pydantic-settings
