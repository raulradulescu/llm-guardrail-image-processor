# Security Review Checklist (Phase 6)

## Status
- Overall: In Progress
- Owner: TBD
- Date: TBD

## Findings Summary
- Open findings: 0
- Resolved findings: 0
- Notes: Initial checklist created; review pending.

## Checklist

### Input Handling
- [ ] Validate magic bytes for image types
- [x] Enforce max file size and dimensions
- [x] Reject animated images
- [ ] Enforce file count limits on batch requests

### Output Safety
- [x] Extracted text truncation supported
- [x] Optional text suppression supported
- [ ] Marked image redaction and overlays reviewed

### Service Hardening
- [ ] Rate limiting enabled
- [ ] API key authentication enabled
- [ ] CORS policy defined
- [ ] Request timeouts enforced at web server

### Dependencies
- [x] Pin core dependencies in `requirements.txt`
- [ ] Vulnerability scan (pip/audit) completed
- [ ] OS package updates (container) verified

### Observability
- [x] Per-module latency reporting
- [ ] Centralized logging configuration
- [ ] Metrics endpoint or exporter

### Secrets
- [ ] No secrets in repo
- [ ] Env var usage documented

## Follow-up Actions
1. Add API key middleware for FastAPI.
2. Add basic rate limiting.
3. Add dependency vulnerability scan to CI.
