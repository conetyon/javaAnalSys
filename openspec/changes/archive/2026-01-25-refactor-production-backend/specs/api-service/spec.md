# Specification: API Service Module

**Capability**: `api-service`
**Change Type**: MODIFIED
**Related Capabilities**: `performance-benchmarks`

---

## MODIFIED Requirements

### Requirement: Production-Ready API Startup

The API service SHALL support one-command startup with production-grade initialization.

**Rationale**: Current `run_api.py` handles argument parsing but lacks health checks, metrics endpoints, and standardized startup logging.

#### Scenario: Developer starts API service with default settings

**Given**: Database is configured in `config/db.yaml`
**When**: Developer runs `python run_api.py`
**Then**:
- API server starts on `http://0.0.0.0:5000`
- Startup logs show:
  - Database connection pool initialized (success/failure)
  - Available routes registered
  - Server ready message with URL
- Health check endpoint `/api/health` is accessible

#### Scenario: Production deployment with custom port

**Given**: Production environment requires port 8080
**When**: Operator runs `python run_api.py --port 8080 --host 0.0.0.0`
**Then**:
- API server starts on specified port
- All existing endpoints remain functional
- No breaking changes to existing API contracts

---

### Requirement: Health Check and Metrics Endpoints

The API SHALL expose operational endpoints for monitoring.

**Rationale**: Production deployments require health checks for load balancers and metrics for observability.

#### Scenario: Load balancer checks service health

**Given**: API service is running
**When**: Health check endpoint `GET /api/health` is called
**Then**: Response includes:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-01-24T12:00:00Z"
}
```
**And**: HTTP status code is 200

#### Scenario: Monitoring system retrieves runtime metrics

**Given**: API has processed multiple requests
**When**: Metrics endpoint `GET /api/metrics` is called
**Then**: Response includes:
```json
{
  "uptime_seconds": 3600,
  "requests_total": 1523,
  "requests_by_endpoint": {
    "/api/match": 1200,
    "/api/knowledge/tree": 323
  },
  "avg_response_time_ms": 23.5
}
```
**And**: Metrics are computed since server start

---

### Requirement: Graceful Error Handling for Missing Configuration

The API SHALL fail fast with clear error messages when configuration is invalid.

**Rationale**: Current behavior may silently fail or show cryptic database errors.

#### Scenario: Database configuration file is missing

**Given**: `config/db.yaml` does not exist
**When**: Developer runs `python run_api.py`
**Then**:
- Server startup fails immediately
- Error message shows: "Configuration file not found: config/db.yaml"
- Exit code is non-zero

#### Scenario: Database connection fails during startup

**Given**: Database credentials in `config/db.yaml` are incorrect
**When**: Operator starts API service
**Then**:
- Startup logs show connection attempt details
- Error message includes: "Failed to connect to database: [specific error]"
- Server does not start (fail-fast principle)
- Exit code is non-zero

---

### Requirement: Bulk Import API Endpoint

The API SHALL support asynchronous bulk code repository import.

**Rationale**: Code parsing and feature extraction are slow operations (5-30 minutes for large repos). Async is necessary for responsive API and good user experience. Users can test in Apifox and poll for progress.

**Related Capability**: `bulk-code-import`

#### Scenario: User initiates bulk import via API (Apifox)

**Given**: Java projects are placed in `code_repos/` directory
**When**: User posts to `POST /api/bulk-import` from Apifox:
```json
{
  "repo_path": "code_repos/spring-boot"
}
```
**Then**: Response returns immediately (<100ms):
```json
{
  "job_id": "import-20260124-abc123",
  "status": "queued",
  "message": "Import job started"
}
```
**And**: Job is processed asynchronously in background thread
**And**: API remains responsive for other requests

#### Scenario: User polls for import progress

**Given**: Bulk import job is running
**When**: User calls `GET /api/bulk-import/import-20260124-abc123` from Apifox
**Then**: Response shows real-time progress:
```json
{
  "job_id": "import-20260124-abc123",
  "status": "running",
  "progress": 450,
  "total_files": 1000,
  "snippets_imported": 2340,
  "current_file": "src/main/java/com/example/Controller.java",
  "errors": []
}
```

#### Scenario: Bulk import job completes successfully

**Given**: All files in repository are processed
**When**: User checks job status
**Then**: Response shows:
```json
{
  "job_id": "import-20260124-abc123",
  "status": "completed",
  "progress": 1000,
  "total_files": 1000,
  "snippets_imported": 5230,
  "errors": []
}
```

#### Scenario: Import job fails with partial completion

**Given**: Some files have syntax errors
**When**: Import completes with errors
**Then**: Response includes error details:
```json
{
  "job_id": "import-20260124-abc123",
  "status": "completed",
  "progress": 1000,
  "total_files": 1000,
  "snippets_imported": 4950,
  "errors": [
    {
      "file": "src/gen/Generated.java",
      "error": "Syntax error at line 42"
    }
  ]
}
```

---

## ADDED Requirements

### Requirement: API Request Logging

All API requests SHALL be logged for debugging and auditing.

**Rationale**: Production systems require request logs for troubleshooting and monitoring.

#### Scenario: API request is logged with key details

**Given**: API service is running
**When**: Any endpoint receives a request
**Then**: Log entry includes:
- Timestamp
- HTTP method and path
- Request source IP
- Response status code
- Response time in milliseconds

#### Scenario: Failed requests are logged with error details

**Given**: API request fails due to invalid input
**When**: Request validation fails
**Then**: Log entry includes:
- Full request payload (sanitized, no sensitive data)
- Validation error message
- Stack trace (if internal error)

---

## Implementation Notes

### Unchanged Behavior
- All existing API endpoints (`/api/match`, `/api/knowledge/*`) remain unchanged
- Current request/response schemas preserved (backward compatible)
- Service layer (`src/services/`) remains the business logic source

### New Dependencies
- None required (use existing Flask middleware capabilities)

### Configuration Changes
- Add optional `[api]` section to `config/api.yaml`:
```yaml
api:
  host: 0.0.0.0
  port: 5000
  debug: false
  request_logging: true
  worker_threads: 1  # Background job workers
```

### Testing Requirements
- Integration tests for `/api/health` and `/api/metrics` endpoints
- Integration tests for bulk import endpoints:
  - Start job via API
  - Poll for status
  - Verify job completion
  - Test error handling
- Request logging verification (check log files contain expected entries)
