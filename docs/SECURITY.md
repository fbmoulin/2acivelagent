# Security Guide - Sistema de Automacao Juridica

This document outlines the security measures implemented in the system and provides guidelines for maintaining a secure deployment.

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Network Security](#network-security)
4. [Data Protection](#data-protection)
5. [Input Validation](#input-validation)
6. [Security Configuration](#security-configuration)
7. [Monitoring & Auditing](#monitoring--auditing)
8. [Incident Response](#incident-response)
9. [LGPD Compliance](#lgpd-compliance)
10. [Security Checklist](#security-checklist)

---

## Security Architecture

### Defense in Depth

The system implements multiple layers of security:

```
┌──────────────────────────────────────────────────────────────────┐
│                        INTERNET                                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    FIREWALL     │  Layer 1: Network filtering
                    │   (UFW/iptables)│  - Port restrictions
                    └────────┬────────┘  - Rate limiting
                             │
                    ┌────────▼────────┐
                    │     NGINX       │  Layer 2: Reverse proxy
                    │  (SSL/TLS)      │  - SSL termination
                    │                 │  - Request filtering
                    └────────┬────────┘  - Security headers
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌─────▼─────┐      ┌─────▼─────┐
    │   N8N   │        │  Python   │      │  Grafana  │
    │  Basic  │        │   JWT     │      │  Session  │
    │  Auth   │        │   Auth    │      │   Auth    │
    └────┬────┘        └─────┬─────┘      └───────────┘
         │                   │
         └─────────┬─────────┘
                   │
    ┌──────────────▼──────────────┐
    │     INTERNAL NETWORK        │  Layer 3: Network isolation
    │  ┌──────────┐ ┌──────────┐  │  - No external exposure
    │  │PostgreSQL│ │  Redis   │  │  - Container networking
    │  │ (No Auth │ │(Password)│  │  - Encrypted connections
    │  │ external)│ └──────────┘  │
    │  └──────────┘               │
    └─────────────────────────────┘
```

### Security Principles Applied

1. **Least Privilege**: Services run with minimal required permissions
2. **Defense in Depth**: Multiple security layers protect critical assets
3. **Fail Secure**: System defaults to secure state on failure
4. **Separation of Concerns**: Authentication, validation, and business logic are separated

---

## Authentication & Authorization

### JWT Token Authentication

All API endpoints are protected with JWT (JSON Web Tokens):

```python
# Token structure
{
    "sub": "user_id",           # Subject (user identifier)
    "iat": 1699900000,          # Issued at timestamp
    "exp": 1699986400,          # Expiration timestamp
    "iss": "judicial-automation" # Issuer
}
```

### Obtaining a Token

```bash
POST /auth/token
Content-Type: application/json

{
    "api_key": "your_api_key"
}

# Response
{
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 86400,
    "token_type": "Bearer"
}
```

### Using the Token

Include the token in all API requests:

```bash
GET /api/endpoint
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Token Security Best Practices

1. **Never log tokens** - Tokens should not appear in logs
2. **Use HTTPS only** - Tokens must only be transmitted over TLS
3. **Short expiry** - Default 24 hours, configurable via `JWT_EXPIRY_HOURS`
4. **Secure storage** - Store tokens securely on client side
5. **Revocation** - Implement token blacklisting for compromised tokens

### Configuration

```bash
# .env configuration
JWT_SECRET=<64-character-hex-string>
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
API_AUTH_ENABLED=true
```

Generate a secure JWT secret:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Network Security

### Port Exposure Policy

| Port | Service | Exposed | Access Method |
|------|---------|---------|---------------|
| 443 | HTTPS (Nginx) | Yes | Public |
| 80 | HTTP (Nginx) | Yes | Redirect to 443 |
| 3000 | Grafana | Yes | Authenticated |
| 5678 | N8N | **No** | Via Nginx only |
| 5000 | Python API | **No** | Via Nginx only |
| 5432 | PostgreSQL | **No** | Internal only |
| 6379 | Redis | **No** | Internal only |
| 9090 | Prometheus | **No** | Internal only |

### Firewall Configuration

```bash
# Recommended UFW rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 3000/tcp  # Grafana (optional)
sudo ufw enable
```

### Docker Network Isolation

Services communicate through an isolated Docker network:

```yaml
# docker-compose.yml
networks:
  judicial_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### CORS Configuration

Cross-Origin Resource Sharing is restricted:

```bash
# .env
ALLOWED_ORIGINS=https://your-domain.com,https://n8n.your-domain.com
```

Only specified origins can access the API.

---

## Data Protection

### Data at Rest

1. **Database Encryption**: PostgreSQL supports TDE (Transparent Data Encryption)
2. **Volume Encryption**: Use encrypted Docker volumes or encrypted filesystem
3. **Backup Encryption**: Backups are compressed and should be encrypted

```bash
# Encrypt backup with GPG
gpg --symmetric --cipher-algo AES256 backup.tar.gz
```

### Data in Transit

1. **TLS 1.3**: All external communications use TLS 1.3
2. **Internal TLS**: Consider enabling TLS between containers for sensitive deployments

### Sensitive Data Handling

The following data types require special handling:

| Data Type | Protection |
|-----------|------------|
| API Keys | Environment variables only, never in code |
| Passwords | Hashed with bcrypt, never stored plaintext |
| JWT Secrets | Random 256-bit keys, rotated periodically |
| Personal Data (LGPD) | Encrypted, access logged, retention enforced |

### Environment Variable Security

```bash
# NEVER do this
OPENAI_API_KEY=sk-xxxxx  # In code or commits

# ALWAYS do this
# 1. Use .env file (not committed)
# 2. Use secrets management (HashiCorp Vault, AWS Secrets Manager)
# 3. Use environment-specific configuration
```

---

## Input Validation

### Prompt Injection Protection

The system detects and blocks prompt injection attempts:

```python
DANGEROUS_PATTERNS = [
    r'ignore\s+(previous|all|above)',
    r'forget\s+(previous|all|above)',
    r'disregard\s+(previous|all|above)',
    r'override\s+(previous|all|above)',
    r'new\s+instructions?:',
    r'system\s*:',
    r'assistant\s*:',
    r'<\s*script',
    r'javascript\s*:',
]
```

Detected injections return:

```json
{
    "success": false,
    "error": "Input contains potentially unsafe content",
    "error_code": "PROMPT_INJECTION_DETECTED"
}
```

### Input Size Limits

| Input Type | Maximum Size |
|------------|--------------|
| Text content | 100,000 characters |
| PDF content (base64) | 50MB |
| Query parameters | 1,000 characters |
| JSON payload | 10MB |

### SQL Injection Prevention

All database queries use parameterized queries:

```python
# SAFE - Parameterized query
cursor.execute(
    "SELECT * FROM processes WHERE id = %s",
    (process_id,)
)

# UNSAFE - String concatenation (NEVER DO THIS)
# cursor.execute(f"SELECT * FROM processes WHERE id = {process_id}")
```

### XSS Prevention

1. All output is HTML-escaped by default
2. Content-Type headers are explicitly set
3. Content-Security-Policy headers restrict script sources

---

## Security Configuration

### Nginx Security Headers

The nginx configuration includes security headers:

```nginx
# Security headers (in nginx.conf)
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### Rate Limiting

Nginx implements rate limiting:

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=3r/m;

# Apply to locations
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
}

location /auth/ {
    limit_req zone=auth_limit burst=5 nodelay;
}
```

### Error Handling

Errors are sanitized to prevent information disclosure:

```python
# Production error response (sanitized)
{
    "success": false,
    "error": "An internal error occurred",
    "error_code": "INTERNAL_ERROR",
    "request_id": "abc123"
}

# Debug error response (development only)
{
    "success": false,
    "error": "Division by zero in calculate_score()",
    "traceback": "..."  # NEVER in production
}
```

---

## Monitoring & Auditing

### Request Logging

All requests include tracking information:

```python
# Request ID header
X-Request-ID: uuid-v4-format

# Log format
{
    "timestamp": "2024-12-04T10:30:00Z",
    "request_id": "abc-123-def",
    "method": "POST",
    "path": "/api/firac-analysis",
    "user_id": "user_123",
    "ip": "192.168.1.1",
    "status": 200,
    "duration_ms": 1500
}
```

### Security Event Logging

Monitor these events:

1. **Failed authentication attempts**
2. **Prompt injection attempts**
3. **Rate limit violations**
4. **Invalid input rejections**
5. **Configuration changes**

### Grafana Alerts

Configure alerts for:

```yaml
# Security-related alerts
- name: High Failed Auth Rate
  condition: failed_auth_count > 10 in 5m
  action: notify_security_team

- name: Prompt Injection Attempt
  condition: injection_attempt_count > 0
  action: notify_security_team

- name: Unusual API Activity
  condition: request_rate > 10x normal
  action: notify_security_team
```

---

## Incident Response

### Security Incident Procedure

1. **Detect**: Monitor alerts and logs for anomalies
2. **Contain**: Isolate affected systems
3. **Investigate**: Analyze logs and determine scope
4. **Remediate**: Apply fixes and patches
5. **Recover**: Restore services from known-good state
6. **Report**: Document incident and lessons learned

### Emergency Actions

```bash
# Block all external access
sudo ufw deny from any to any port 443
sudo ufw deny from any to any port 80

# Stop all services
docker compose down

# Rotate all secrets
# 1. Generate new JWT_SECRET
# 2. Generate new database passwords
# 3. Regenerate API keys

# Review audit logs
docker compose logs --since="2024-12-04" > incident-logs.txt
```

### Contact Information

Maintain a security contact list:

- Security Team Email: security@your-domain.com
- Emergency Phone: +55 XX XXXX-XXXX
- External Security Consultant: contact info

---

## LGPD Compliance

### Data Subject Rights

The system supports LGPD (Lei Geral de Protecao de Dados) requirements:

| Right | Implementation |
|-------|----------------|
| Access | API endpoint to export user data |
| Rectification | Data update endpoints |
| Deletion | Data purge with audit trail |
| Portability | JSON export format |
| Consent | Workflow-based consent management |

### Data Retention

```bash
# .env configuration
EXECUTIONS_DATA_MAX_AGE=168  # 7 days in hours
EXECUTIONS_DATA_PRUNE=true   # Enable automatic pruning
```

### Data Minimization

Only collect and process data that is strictly necessary:

1. No unnecessary personal data collection
2. Pseudonymization of identifiers where possible
3. Aggregation of analytics data

### Audit Trail

All data access is logged:

```json
{
    "timestamp": "2024-12-04T10:30:00Z",
    "action": "DATA_ACCESS",
    "user_id": "user_123",
    "data_subject": "process_456",
    "data_type": "legal_document",
    "justification": "case_analysis"
}
```

---

## Security Checklist

### Pre-Deployment

- [ ] All default passwords changed
- [ ] JWT_SECRET generated (64+ hex characters)
- [ ] SSL certificate valid (not self-signed for production)
- [ ] Environment variables secured (not in version control)
- [ ] Database not exposed externally
- [ ] Redis password configured
- [ ] CORS restricted to specific origins
- [ ] Rate limiting configured
- [ ] Security headers enabled

### Post-Deployment

- [ ] Firewall rules verified
- [ ] Fail2ban configured
- [ ] Log rotation configured
- [ ] Backup encryption enabled
- [ ] Monitoring alerts configured
- [ ] Security scans passing in CI/CD
- [ ] Access logs being collected
- [ ] Incident response plan documented

### Periodic Review (Monthly)

- [ ] Review access logs for anomalies
- [ ] Update dependencies (security patches)
- [ ] Rotate secrets and API keys
- [ ] Test backup restoration
- [ ] Review and update firewall rules
- [ ] Verify SSL certificate expiration
- [ ] Run security scans (OWASP ZAP, etc.)
- [ ] Review user access and permissions

### Annual Security Audit

- [ ] Penetration testing
- [ ] Code security review
- [ ] Architecture security review
- [ ] Compliance verification (LGPD)
- [ ] Incident response drill
- [ ] Security training for team

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email security details to: security@your-domain.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work to address the issue promptly.

---

**Security is everyone's responsibility. When in doubt, ask!**
