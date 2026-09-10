## Custos Data Manager
Custos Data Manager is an event-driven ETL (Extract, Transform, Load) pipeline designed for robustness, data integrity, and extensibility.

It utilizes Watchdog and APScheduler for real-time and scheduled detection of incoming CSV files. Data undergoes an initial rapid audit via Pandas, followed by strict validation using Pydantic and SQLAlchemy ORM models. Validated rows are persisted to a PostgreSQL database in atomic batches, while invalid rows are safely routed to a quarantine directory for manual review.

Out of the box, Custos is configured to process and manage Leads and FactSales in a Star Schema (with Product, Customer, and Date Dimensions), but its architecture is designed to be domain-agnostic. Additional domains can be added to registry configuration with zero or minimal changes to the pipeline handlers.

### Key Features
- **Decoupled & Agnostic Architecture:** Tools and libraries are integrated via clean abstraction layers. Domain-specific class objects, helper functions, and mapping keys are configured dynamically via a registry rather than being hard-coded, allowing for the seamless addition of new data domains.

- **Security & PII Protection**: Verifies true file MIME types prior to ingesting ostensible CSVs. Personally Identifiable Information (PII) is secured at rest using Fernet encryption.

- **Strict Idempotency:** Prevents duplicate processing by hashing and comparing incoming files against a processed registry. Batch persistence is made atomic using the Unit of Work pattern, bolstered by thorough idempotency checks across the database, identity maps, and in-memory entities before any data is committed.

<<<<<<< HEAD
- **Automated Update Management:** Safely handles field updates by storing contributions as historical "snapshots" with full context. Chronological update logic is automated to protect against stale data and ensure accurate entity states. Rollbacks of updated data to a previous clean state are automated following file failure.
=======
- **Automated Update Management:** Safely handles field updates by storing contributions as historical "snapshots" with full context. Chronological update logic is automated to protect against stale data and ensure accurate entity states.
>>>>>>> 46d0e53248b554284a4664285111317b5385cb8e

- **Resilience & Observability:** Features comprehensive event logging, custom domain exceptions, infrastructure safety wrappers, and automated alerts for system fault events.

- **Extensible Processing:** Fully compatible with message brokers and external background workers. Currently leverages APScheduler for cron jobs and includes built-in mock email alerts for system notifications.

- **Production-Ready Testing:** Backed by a comprehensive Pytest suite containing 86 unit, integration, and end-to-end tests, currently sitting at 100% passing with 89% total code coverage.

<<<<<<< HEAD
### Architecture
- **Domain-Driven Design:** Business logic handled by domains independently of ORMS. File is the primary aggregate root.
- **Message Bus:** The message bus is configured with different handling for events (errors logged) and commands (errors are permitted to raise and fail loudly.) An abstract Bus allows for upgrades and extensions with message brokers.
- **Interfaces and Adapters:** Abstract interfaces allow for flexibility as well as for the use of Fakes (largely to the exclusion of mocks) in the testing suite.


=======
>>>>>>> 46d0e53248b554284a4664285111317b5385cb8e
### Tech Stack
- **Core:** Python

- **Persistence:** PostgreSQL, SQLAlchemy (ORM)

- **Validation & Auditing:** Pydantic, Pandas

- **File Monitoring & Scheduling:** Watchdog, APScheduler

- **Testing:** Pytest, pytest-cov

<<<<<<< HEAD
- **Database Migration/Revisions:** Alembic

- **Security:** Cryptography (Fernet), pydantic-settings



### Prospective Features for Future Versions
- **Manual Review UI/UX:** This would be a graphic user interface (GUI) to permit users to correct quarantined rows.

- **Addition of Message Broker:** Kafka or Rabbit MQ will be used to manage external workers and alerts.

- **Further Flagging of Suspect FactSales:** Currently, if two Fact Sales have the same Product SKU and Transaction ID, they are treated as the same entity and rows have priority based on the time they enter the database while duplicates are ignored for idempotency. However, this allows for an edge case where a later row has the same identifying field values as an existing row (transaction ID and SKU) but differs in values for other fields. A future version will flag these for review and persist them.

- **Integration with Data Analytics Program:** A sister program for data analytics (Quaestor) is currently in development, and will be configured to work with Custos.

### Getting Started

1. **Configuration**
Before running the program, you will need to configure your environment variables. You can copy the provided example file and update the values, generating your own Fernet encryption key and hash secret string.

```bash
cp .env.example .env
```

2. **Run with Docker (Recommended)**
**Prerequisites:** 
- Linux: standard Docker Engine and Docker Compose
- Windows: WSL2 and Docker Desktop
- Mac: Docker Desktop for Mac (or an alternative set-up, such as OrbStack.)

``` bash
# To build the images and start containers
docker-compose up --build
# To run a detached background instance
docker-compose up -d
# To shut down the instance
docker-compose down
```

3. **Run locally with Poetry**

You can certainly run the code and test suite locally. This project uses [Poetry](https://python-poetry.org/) for dependency management.
Ensure you have a local instance of PostgreSQL running that matches your `.env` credentials, then install the dependencies:

```bash
# Install dependencies
poetry install

# Run database migrations to create the tables
poetry run alembic upgrade head

# Use the database seeding script to set up for MQL alerts: 
poetry run python -m src.bootstrap.seed_team

# Run the test suite (86 tests, 89% coverage)
poetry run pytest

# Start the Custos pipeline
poetry run python main.py
```
4. **Move a file into one of the "data/incoming" directories to start the pipeline.**

Create a CSV file (the tests folder contains a few scripts that can help with this) and move it into either "incoming/leads" or "incoming/sales."

### Contributions

This repo is read-only and contributions are not currently being solicited. 

### License

This code base is open-source under the MIT license, but the names "Custos" and "Custos Data Manager" are under copyright by the author.
=======
- **Security:** Cryptography (Fernet), pydantic-settings
>>>>>>> 46d0e53248b554284a4664285111317b5385cb8e
