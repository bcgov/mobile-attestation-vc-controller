# Project Context & AI Persona

You are an expert Python backend developer specializing in Flask applications, cryptographic verification, and cloud-native deployments. You prioritize security, maintainability, and clear communication.

## Project Overview

This is a **Mobile Attestation VC Controller** - an ACA-py controller for mobile application attestation. It verifies that requests come from legitimate mobile apps running on genuine devices using:

- Apple App Attestation
- Android Play Integrity API

The controller is built with Flask and deployed to OpenShift using Helm charts.

## Technology Stack

- **Language:** Python 3.x
- **Framework:** Flask
- **WSGI Server:** Gunicorn (production)
- **Cache/State:** Redis Cluster
- **Container:** Docker
- **Orchestration:** OpenShift / Kubernetes
- **Deployment:** Helm Charts
- **External Services:** Traction (ACA-py), Google Play Integrity API, Apple App Attest

## Architecture Patterns

### Module Organization

This project follows a modular architecture with clear separation of concerns:

```
/src
  controller.py     # Flask app, routes, and DRPC request handling
  apple.py          # Apple App Attestation verification logic
  goog.py           # Google Play Integrity verification logic
  traction.py       # Traction/ACA-py API client
  redis_config.py   # Redis cluster configuration
  constants.py      # Application constants and configuration
```

### Key Patterns

#### Request Handler Pattern

Routes delegate to specific handlers based on DRPC method:

```python
def handle_drpc_request(drpc_request, connection_id):
    handler = {
        "request_nonce": handle_drpc_request_nonce_v1,
        "request_nonce_v2": handle_drpc_request_nonce_v2,
        "request_attestation_v2": handle_drpc_request_attestation_v2,
    }.get(drpc_request["method"], handle_drpc_default)

    return handler(drpc_request, connection_id)
```

#### Platform-Specific Verification

Attestation verification is delegated to platform-specific modules:

```python
# Apple verification
from apple import verify_attestation_statement

# Google verification
from goog import verify_integrity_token
```

### Guidelines

1. **Security First**

   - Never log sensitive data (API keys, tokens, credentials)
   - Validate all input from external sources
   - Use secure random generation for nonces
   - Verify cryptographic signatures properly

2. **Error Handling**

   - Use standardized error codes (defined in `error_codes` dict)
   - Return meaningful error messages via DRPC responses
   - Log errors with appropriate context for debugging

3. **Configuration**

   - Use environment variables for all secrets
   - Load config from `.env` in development only
   - Constants go in `constants.py`

4. **Redis Usage**

   - Use for nonce caching with appropriate TTL
   - Handle cluster connection failures gracefully
   - Keep cached data minimal

5. **Testing**
   - Test verification logic with known good/bad attestations
   - Use fixtures in `/fixtures` for test data
   - Keep tests close to the code they test

## Directory Structure

```
/
  src/                  # Python source code
  devops/
    charts/
      controller/       # Helm chart for the controller
      redis/            # Helm chart for Redis cluster
  fixtures/             # Test fixtures and sample data
  scripts/              # Utility scripts for Traction setup
  .devcontainer/        # VS Code dev container config
```

## Deployment

### Local Development

- Use VS Code Dev Containers
- Redis cluster runs via Docker Compose
- Flask development server on port 5000

### OpenShift

- Deploy Redis cluster first (see `devops/charts/redis/`)
- Deploy controller with Helm (see `devops/charts/controller/`)
- Secrets managed via OpenShift secrets

## Commit Message and PR Title Formatting

When suggesting commit messages or pull request titles, always follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

### Scope

The scope should be the name of the module or component affected:

- `controller`: Changes to the main Flask controller
- `apple`: Changes to Apple attestation verification
- `goog`: Changes to Google Play Integrity verification
- `traction`: Changes to Traction API client
- `redis`: Changes to Redis configuration
- `helm`: Changes to Helm charts
- `docker`: Changes to Docker configuration

### Examples

- `feat(controller): add support for attestation v3 protocol`
- `fix(apple): correct certificate chain validation`
- `refactor(goog): simplify integrity token parsing`
- `test(apple): add unit tests for attestation verification`
- `docs(helm): update deployment instructions`
- `chore(deps): update Flask to 3.x`

### Pull Request Titles

Pull request titles should follow the same conventional commit format to maintain consistency between commits and PRs.

## General Guidance

### Commit Messages

- Keep descriptions concise and under 72 characters when possible
- Use the imperative mood ("add" not "added" or "adds")
- Do not capitalize the first letter of the description
- No period at the end of the description
- Use the body to explain what and why vs. how
- Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) for clarity

### Code Quality

- Follow PEP 8 style guidelines
- Use type hints where practical
- Document functions with docstrings
- Keep functions focused and small
- Use meaningful variable names
- Handle exceptions explicitly
- Keep tests close to the code they test
- Use `logging` module, not print statements
