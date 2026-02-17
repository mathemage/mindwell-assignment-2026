# Security

## Overview

This document outlines the security measures implemented in the Mindwell AI assistant.

## Authentication & Authorization

### Authentication

**Current Implementation** (MVP):
- Simplified JWT-based authentication for development
- Email-based user identification
- Token expiration after 60 minutes (configurable)

**Production Recommendations**:
- Implement magic link authentication via email
- Add multi-factor authentication (MFA)
- Use secure session management
- Implement token refresh mechanism
- Add rate limiting on auth endpoints

### Authorization

**Role-Based Access Control (RBAC)**:
- **Regular Users**: Can chat and view own conversations
- **Admin Users**: Can upload/manage documents, reindex

**Implementation**:
- `get_current_user` dependency for authentication
- `get_current_admin_user` dependency for admin-only routes
- User roles stored in database

## Data Security

### Data at Rest

**Current**:
- Database credentials in environment variables
- User data pseudonymized from creation
- PII automatically redacted before storage

**Production Recommendations**:
- Encrypt sensitive database columns
- Use managed database with encryption at rest
- Implement database access controls (least privilege)
- Enable audit logging
- Regular automated backups with encryption

### Data in Transit

**Current**:
- HTTP in development

**Production Requirements**:
- HTTPS/TLS 1.3 for all connections
- Certificate pinning for API clients
- Secure WebSocket connections if added

### Secrets Management

**Current**:
- Environment variables (`.env` file)
- Never committed to git (in `.gitignore`)

**Production Requirements**:
- Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- Rotate secrets regularly
- Separate secrets per environment
- Implement secret access auditing

## Application Security

### Input Validation

- **Pydantic Models**: All API inputs validated
- **SQL Injection**: SQLAlchemy ORM prevents injection
- **XSS Prevention**: API-only (no HTML rendering)
- **Path Traversal**: File uploads restricted to approved types

### Safety Checks

**Crisis Detection**:
- Real-time keyword matching
- Escalation with emergency resources
- Logged for review and improvement

**Medical Advice Boundaries**:
- Refuses diagnosis/prescription requests
- Provides appropriate disclaimers
- Logs refusals for compliance

**Response Grounding**:
- Verifies responses based on retrieved content
- Prevents hallucinations
- Rejects responses without evidence

### PII Protection

**Automatic Detection**:
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers

**Redaction Layers**:
1. Input: Redacted before storage
2. Logs: Redacted in all logs
3. Errors: Never included in error messages

**Pseudonymization**:
- User IDs pseudonymized from creation
- Display names are pseudonyms
- Original email stored but never exposed in logs

## API Security

### Rate Limiting

**Current**: Not implemented (MVP)

**Production Requirements**:
- Request rate limits per user/IP
- Stricter limits for auth endpoints
- Exponential backoff for repeated failures
- WAF (Web Application Firewall) rules

### CORS

**Current**: Permissive in development
**Production**: Whitelist specific origins only

### HTTP Security Headers

**Production Requirements**:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Logging & Monitoring

### Security Logging

**What We Log**:
- Authentication attempts (success/failure)
- Authorization failures
- Safety check outcomes
- Admin actions (document uploads, reindex)
- Unusual patterns (repeated failures)

**What We DON'T Log**:
- Passwords or tokens
- Unredacted PII
- Full user messages (only pseudonymized versions)
- API keys or secrets

### Log Security

- **Format**: Structured JSON for parsing
- **Redaction**: Automatic PII redaction
- **Storage**: Should be in secure, separate system
- **Access**: Restricted to authorized personnel
- **Retention**: Follow data retention policies

### Monitoring & Alerts

**Recommended Alerts**:
- Repeated authentication failures
- Unusual API traffic patterns
- Safety escalations (crisis detected)
- System errors or downtime
- Admin actions

## Infrastructure Security

### Docker Security

**Current**:
- Non-root user in containers (recommended)
- Minimal base images

**Production Recommendations**:
- Scan images for vulnerabilities
- Use private container registry
- Implement resource limits
- Regular security updates

### Database Security

**Current**:
- Username/password authentication
- Network isolation via Docker

**Production Requirements**:
- Use managed database service
- Enable encryption at rest
- Restrict network access (VPC/private subnet)
- Regular security patches
- Automated backups

### Network Security

**Production Requirements**:
- Private VPC/subnets for backend
- Security groups/firewall rules
- DDoS protection
- API gateway with throttling
- Regular security audits

## Dependency Security

### Vulnerability Scanning

**Process**:
1. Regularly update dependencies
2. Use `pip-audit` or similar tools
3. Monitor CVE databases
4. Test updates in staging first

**Automation**:
- Dependabot/Renovate for updates
- Automated security scanning in CI
- Block deployments with critical vulnerabilities

## Incident Response

### Incident Types

1. **Security Breach**: Unauthorized access to systems/data
2. **Data Leak**: PII exposed
3. **Safety Incident**: Crisis not detected or mishandled
4. **System Outage**: Service unavailable

### Response Plan

1. **Detect**: Monitoring alerts, user reports
2. **Contain**: Isolate affected systems
3. **Investigate**: Determine scope and cause
4. **Remediate**: Fix vulnerability, restore service
5. **Document**: Incident report and lessons learned
6. **Notify**: Affected users if legally required

### Security Contacts

- Security issues: [Create GitHub security advisory]
- Urgent: [Emergency contact info]

## Compliance

### HIPAA Considerations

⚠️ **This system is NOT HIPAA-compliant** in its current state.

**For HIPAA compliance, you would need**:
- Business Associate Agreements (BAAs)
- Audit controls and access logs
- Automatic logoff after inactivity
- Encryption at rest and in transit
- Disaster recovery plan
- Regular risk assessments
- Security awareness training

### GDPR Considerations

**Current Implementation**:
- Pseudonymization of user data
- PII redaction
- Data minimization

**For Full GDPR Compliance**:
- Right to erasure (delete user data)
- Right to portability (export data)
- Privacy policy and consent
- Data processing agreements
- Data Protection Impact Assessment (DPIA)

## Security Checklist

### MVP (Current)
- [x] JWT authentication
- [x] Input validation (Pydantic)
- [x] SQL injection protection (ORM)
- [x] PII redaction
- [x] Secrets in environment variables
- [x] Safety checks
- [ ] Rate limiting
- [ ] HTTPS/TLS

### Production (Required)
- [ ] HTTPS/TLS everywhere
- [ ] Secrets manager
- [ ] Database encryption at rest
- [ ] Regular security audits
- [ ] Dependency scanning
- [ ] Rate limiting
- [ ] WAF rules
- [ ] Incident response plan
- [ ] Security monitoring/alerts
- [ ] Regular penetration testing

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public issue
2. Email security@[domain].com (or create private security advisory)
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and provide updates on remediation.

## Security Updates

This document should be reviewed and updated:
- Quarterly (at minimum)
- After security incidents
- When adding new features
- When regulations change

Last Updated: 2026-02-17
