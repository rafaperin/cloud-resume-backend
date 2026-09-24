# Cloud Resume Backend

Serverless Python backend and Azure infrastructure for the Cloud Resume Challenge.

The Azure Function exposes a visitor-counter API. It uses its system-assigned managed identity to read and update the `resume` / `counter` entity in Azure Cosmos DB for Table. Bicep provisions the Function App, its dedicated backing storage, the static website storage, Cosmos DB, and required role assignments.

```text
Browser
   |
   v
Azure Function (Python)
   |
   | Managed identity
   v
Cosmos DB for Table
```

## Technology

- Python 3.13 and Azure Functions v2 programming model
- Azure Cosmos DB for Table
- Azure Storage and Azurite for local development
- Bicep infrastructure as code
- Standard-library `unittest` and Coverage.py

## Repository ownership

This repository is the single source of truth for the Cloud Resume backend:

- Python application code, tests, and backend tooling
- Azure Functions configuration and deployment packaging
- Bicep infrastructure and backend CI/CD

Frontend HTML, CSS, JavaScript, and frontend CI/CD belong in the separate `cloud-resume-frontend` repository. Do not mirror backend changes into the legacy mixed repository.

## Repository layout

```text
.
├── application/       # Use cases and ports
├── domain/            # Business models and rules
├── infrastructure/    # Azure adapters and Bicep templates
├── tests/             # Tests organized by architecture layer
├── tools/             # Local operational tools
├── function_app.py    # Azure Functions HTTP entry point
├── host.json
├── requirements.txt
└── requirements-dev.txt
```

## Local development

Use Python 3.13 to install the pinned packages:

~~~sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
~~~

Copy `local.settings.json.example` to `local.settings.json`. The local configuration uses Azurite and contains no Azure credentials.

Start Azurite, then start the Function App:

~~~sh
azurite --location /tmp/cloud-resume-azurite
func start
~~~

## Tests

~~~sh
.venv/bin/python -m coverage run -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python -m coverage report
~~~

The branch-coverage threshold is 80%.

## Infrastructure

Infrastructure templates and deployment instructions are in [infrastructure/README.md](infrastructure/README.md).

Validate the Bicep entry point before a deployment:

~~~sh
az bicep build --file infrastructure/main.bicep
~~~

The backend repository does not deploy frontend files. The frontend is maintained and deployed from its own repository.

## CI/CD

GitHub Actions runs backend tests with the 80% coverage gate and builds and lints Bicep for pull requests. A push to `main` deploys infrastructure and the Function App only after both checks pass. Azure authentication uses GitHub OIDC; no Azure client secret or publish profile is stored in the repository.

Complete the one-time [GitHub OIDC bootstrap](infrastructure/github-oidc.md) before the first deployment workflow run.
