# API Documentation - Sistema de Automacao Juridica

## Overview

This API provides endpoints for Brazilian judicial process automation, including PDF text extraction, legal analysis (FIRAC methodology), jurisprudence search, and document generation.

**Base URL:** `http://localhost:5000` (development)

**Production URL:** `https://api.judicial-automation.com.br`

---

## Authentication

The API uses JWT (JSON Web Token) for authentication on protected endpoints.

Include the token in the `Authorization` header:

```
Authorization: Bearer <your_token>
```

---

## Endpoints

### Health Check

```http
GET /health
```

Verify API health and service status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "1.0.0",
  "services": {
    "redis": true,
    "openai": true,
    "datajud": true
  }
}
```

---

### Extract PDF Text

```http
POST /extract-pdf
Content-Type: application/json
```

Extract text content from a PDF document.

**Request Body:**
```json
{
  "pdf_content": "<base64_encoded_pdf>"
}
```

**Response:**
```json
{
  "success": true,
  "text": "Extracted text content...",
  "pages": 5,
  "metadata": {
    "extracted_at": "2024-01-15T10:30:00.000Z",
    "method": "PyPDF2"
  }
}
```

**Example (curl):**
```bash
# Encode PDF to base64
PDF_BASE64=$(base64 -w0 document.pdf)

# Send request
curl -X POST http://localhost:5000/extract-pdf \
  -H "Content-Type: application/json" \
  -d "{\"pdf_content\": \"$PDF_BASE64\"}"
```

---

### FIRAC Analysis

```http
POST /firac-analysis
Content-Type: application/json
```

Perform legal analysis using FIRAC methodology:
- **F**acts: Main facts of the case
- **I**ssues: Legal questions involved
- **R**ules: Applicable legal rules
- **A**nalysis: Application of rules to facts
- **C**onclusion: Legal conclusion

**Request Body:**
```json
{
  "text": "Legal text to analyze (minimum 50 characters)..."
}
```

**Response:**
```json
{
  "success": true,
  "firac_analysis": "{\"fatos\": \"...\", \"questoes\": \"...\", ...}",
  "analysis_type": "auto-detect",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5000/firac-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "text": "O autor alega que celebrou contrato de prestacao de servicos com a re em 01/01/2023. O valor acordado foi de R$ 10.000,00 mensais..."
  }'
```

---

### DATAJUD Search

```http
POST /datajud-search
Content-Type: application/json
```

Search jurisprudence in the DATAJUD database (CNJ official API).

**Supported Courts:**
- State Courts: `tjsp`, `tjrj`, `tjmg`, `tjrs`, `tjpr`, `tjsc`, `tjba`, `tjpe`, `tjce`, `tjgo`
- Federal Courts: `trf1`, `trf2`, `trf3`, `trf4`, `trf5`
- Superior Courts: `tst`, `stj`, `stf`

**Request Body:**
```json
{
  "tribunal": "tjsp",
  "classe_codigo": 1116,
  "orgao_julgador": "0001",
  "texto_livre": "execucao fiscal",
  "size": 50
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| tribunal | string | No | Court code (default: tjsp) |
| classe_codigo | integer | No | Procedural class code |
| orgao_julgador | string | No | Judging body code |
| texto_livre | string | No | Free text search |
| size | integer | No | Max results (default: 50, max: 100) |

**Response:**
```json
{
  "success": true,
  "data": {
    "hits": {
      "total": {"value": 150},
      "hits": [...]
    }
  },
  "tribunal": "tjsp",
  "total_results": 150
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5000/datajud-search \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal": "tjsp",
    "texto_livre": "cobranca contrato inadimplemento",
    "size": 10
  }'
```

---

### Distinguish Analysis

```http
POST /distinguish-analysis
Content-Type: application/json
```

Compare current case facts with a precedent to determine applicability (distinguish).

**Request Body:**
```json
{
  "current_facts": "Facts of the current case...",
  "precedent_data": {
    "case_number": "9876543-21.2022.8.26.0100",
    "summary": "Contract breach case...",
    "holding": "The court held that..."
  }
}
```

**Response:**
```json
{
  "success": true,
  "distinguish_analysis": "{\"applicable\": true, \"similarities\": [...], ...}",
  "applicable": true,
  "confidence": 0.85,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

### Generate Document

```http
POST /generate-document
Content-Type: application/json
```

Generate legal documents using AI.

**Supported Document Types:**
- `sentenca`: Full judicial sentence
- `despacho`: Administrative order
- `decisao`: Interlocutory decision

**Request Body:**
```json
{
  "document_type": "sentenca",
  "case_data": {
    "case_number": "1234567-89.2023.8.26.0100",
    "plaintiff": "Joao da Silva",
    "defendant": "Empresa XYZ Ltda",
    "claim_type": "Cobranca",
    "claim_amount": 30000.00,
    "facts": "Contract breach...",
    "legal_basis": "Art. 389 do Codigo Civil"
  }
}
```

**Response:**
```json
{
  "success": true,
  "document_type": "sentenca",
  "generated_text": "SENTENCA\n\nVistos.\n\nTrata-se de acao de cobranca...",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5000/generate-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "sentenca",
    "case_data": {
      "case_number": "1234567-89.2023.8.26.0100",
      "plaintiff": "Joao da Silva",
      "defendant": "Empresa XYZ Ltda",
      "claim_type": "Cobranca",
      "claim_amount": 30000
    }
  }'
```

---

## Error Handling

All errors return a JSON response with an `error` field:

```json
{
  "error": "Error message describing the problem",
  "details": "Additional details (optional)"
}
```

**HTTP Status Codes:**
| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (missing/invalid token) |
| 404 | Endpoint not found |
| 405 | Method not allowed |
| 429 | Too many requests (rate limit) |
| 500 | Internal server error |

---

## Rate Limiting

| Endpoint Type | Limit |
|---------------|-------|
| API endpoints | 10 requests/second |
| Webhooks | 5 requests/second |

Exceeding the rate limit returns HTTP 429 with a `Retry-After` header.

---

## LGPD Compliance

This API complies with Brazil's General Data Protection Law (LGPD):

- Execution data is retained for a maximum of 7 days
- Personal data is minimized and pseudonymized
- All operations are logged for audit purposes
- Data deletion requests are honored within 72 hours

---

## OpenAPI Specification

The complete OpenAPI 3.1 specification is available at:

- **YAML:** `/docs/api/openapi.yaml`
- **Swagger UI:** `http://localhost:5000/api/docs` (when enabled)

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "http://localhost:5000"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# FIRAC Analysis
response = requests.post(
    f"{BASE_URL}/firac-analysis",
    json={"text": "Legal text to analyze..."}
)
print(response.json())
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:5000';

// Health check
axios.get(`${BASE_URL}/health`)
  .then(response => console.log(response.data));

// FIRAC Analysis
axios.post(`${BASE_URL}/firac-analysis`, {
  text: 'Legal text to analyze...'
})
  .then(response => console.log(response.data));
```

---

## Support

For API support:
- **Email:** suporte@judicial-automation.com.br
- **GitHub Issues:** https://github.com/fbmoulin/2acivelagent/issues
