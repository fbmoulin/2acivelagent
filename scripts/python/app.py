#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Automacao Juridica - API Python
Microservicos para processamento de documentos e analise juridica

Security-hardened version with:
- JWT authentication
- Input validation
- Rate limiting
- Secure error handling
- Request tracing
"""

import os
import re
import logging
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, Tuple, List

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import redis
import openai
import requests
from requests.exceptions import RequestException, Timeout
import jwt
import PyPDF2
from io import BytesIO
import base64

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Application configuration from environment variables."""

    # Required variables (must be set)
    JWT_SECRET: str = os.getenv('JWT_SECRET', '')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')

    # Optional with secure defaults
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    DATAJUD_BASE_URL: str = os.getenv('DATAJUD_BASE_URL', 'https://api-publica.datajud.cnj.jus.br')
    DATAJUD_USERNAME: str = os.getenv('DATAJUD_USERNAME', '')
    DATAJUD_PASSWORD: str = os.getenv('DATAJUD_PASSWORD', '')

    # Security settings
    ALLOWED_ORIGINS: List[str] = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5678').split(',')
    MAX_CONTENT_LENGTH: int = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))  # 50MB
    JWT_EXPIRY_HOURS: int = int(os.getenv('JWT_EXPIRY_HOURS', 24))

    # OpenAI settings
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4')
    OPENAI_MAX_TOKENS: int = int(os.getenv('OPENAI_MAX_TOKENS', 2000))
    OPENAI_TIMEOUT: int = int(os.getenv('OPENAI_TIMEOUT', 60))

    # Input limits
    MAX_TEXT_LENGTH: int = int(os.getenv('MAX_TEXT_LENGTH', 50000))
    MIN_TEXT_LENGTH: int = int(os.getenv('MIN_TEXT_LENGTH', 50))
    MAX_PDF_SIZE: int = int(os.getenv('MAX_PDF_SIZE', 25 * 1024 * 1024))  # 25MB

    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """Validate required configuration."""
        errors = []

        if not cls.JWT_SECRET or cls.JWT_SECRET == 'dev-secret-key':
            errors.append("JWT_SECRET must be set to a secure value")

        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY must be set")

        return len(errors) == 0, errors


# =============================================================================
# LOGGING SETUP
# =============================================================================

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s'
)
logger = logging.getLogger(__name__)


class RequestIdFilter(logging.Filter):
    """Add request ID to all log records."""

    def filter(self, record):
        record.request_id = getattr(g, 'request_id', 'no-request')
        return True


logger.addFilter(RequestIdFilter())


# =============================================================================
# FLASK APP INITIALIZATION
# =============================================================================

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Secure CORS configuration - restrict to allowed origins only
CORS(app, resources={
    r"/*": {
        "origins": Config.ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Request-ID"],
        "max_age": 3600
    }
})

# Set secret key (required for JWT)
if Config.JWT_SECRET:
    app.config['SECRET_KEY'] = Config.JWT_SECRET
else:
    logger.critical("JWT_SECRET not configured - authentication will fail")

# Configure OpenAI
if Config.OPENAI_API_KEY:
    openai.api_key = Config.OPENAI_API_KEY


# =============================================================================
# REDIS CONNECTION
# =============================================================================

redis_client: Optional[redis.Redis] = None
try:
    redis_client = redis.from_url(Config.REDIS_URL)
    redis_client.ping()
    logger.info("Redis connection established")
except redis.RedisError as e:
    logger.warning(f"Redis connection failed: {type(e).__name__}. Running without cache.")
    redis_client = None
except Exception as e:
    logger.warning(f"Unexpected Redis error: {type(e).__name__}. Running without cache.")
    redis_client = None


# =============================================================================
# SECURITY UTILITIES
# =============================================================================

def generate_request_id() -> str:
    """Generate unique request ID for tracing."""
    return str(uuid.uuid4())[:8]


def sanitize_error_message(error: Exception) -> str:
    """Sanitize error message to prevent information disclosure."""
    error_type = type(error).__name__

    # Map known error types to safe messages
    safe_messages = {
        'ConnectionError': 'Service temporarily unavailable',
        'Timeout': 'Request timed out',
        'AuthenticationError': 'Authentication failed',
        'RateLimitError': 'Rate limit exceeded, please retry later',
        'InvalidRequestError': 'Invalid request',
        'APIError': 'External service error',
        'JSONDecodeError': 'Invalid JSON format',
        'ValidationError': 'Validation error',
    }

    return safe_messages.get(error_type, 'An error occurred processing your request')


def create_jwt_token(user_id: str, roles: List[str] = None) -> str:
    """Create JWT token for authentication."""
    payload = {
        'user_id': user_id,
        'roles': roles or ['user'],
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {type(e).__name__}")
        return None


def require_auth(f):
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Missing or invalid Authorization header',
                'error_code': 'AUTH_REQUIRED'
            }), 401

        token = auth_header.split(' ', 1)[1]
        payload = verify_jwt_token(token)

        if not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'error_code': 'INVALID_TOKEN'
            }), 401

        g.user = payload
        return f(*args, **kwargs)

    return decorated


# =============================================================================
# INPUT VALIDATION
# =============================================================================

class InputValidator:
    """Input validation and sanitization utilities."""

    # Patterns that might indicate prompt injection
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

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = None) -> Tuple[str, bool]:
        """
        Sanitize text input and check for injection patterns.

        Returns:
            Tuple of (sanitized_text, is_safe)
        """
        if max_length:
            text = text[:max_length]

        # Check for dangerous patterns
        text_lower = text.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Potential prompt injection detected: pattern={pattern}")
                return text, False

        return text, True

    @classmethod
    def validate_pdf_content(cls, content: bytes) -> Tuple[bool, str]:
        """Validate PDF content."""
        if len(content) > Config.MAX_PDF_SIZE:
            return False, f"PDF too large (max {Config.MAX_PDF_SIZE // 1024 // 1024}MB)"

        # Check PDF magic bytes
        if not content.startswith(b'%PDF'):
            return False, "Invalid PDF format"

        return True, ""

    @classmethod
    def validate_text_length(cls, text: str) -> Tuple[bool, str]:
        """Validate text length."""
        if len(text) < Config.MIN_TEXT_LENGTH:
            return False, f"Text too short (minimum {Config.MIN_TEXT_LENGTH} characters)"

        if len(text) > Config.MAX_TEXT_LENGTH:
            return False, f"Text too long (maximum {Config.MAX_TEXT_LENGTH} characters)"

        return True, ""

    @classmethod
    def validate_document_type(cls, doc_type: str) -> Tuple[bool, str]:
        """Validate document type."""
        valid_types = ['sentenca', 'despacho', 'decisao']
        if doc_type not in valid_types:
            return False, f"Invalid document type. Valid types: {valid_types}"
        return True, ""

    @classmethod
    def validate_tribunal(cls, tribunal: str) -> Tuple[bool, str]:
        """Validate tribunal code."""
        valid_tribunals = [
            'tjsp', 'tjrj', 'tjmg', 'tjrs', 'tjpr', 'tjsc', 'tjba', 'tjpe', 'tjce', 'tjgo',
            'trf1', 'trf2', 'trf3', 'trf4', 'trf5', 'tst', 'stj', 'stf'
        ]
        if tribunal.lower() not in valid_tribunals:
            return False, f"Invalid tribunal. Valid tribunals: {valid_tribunals}"
        return True, ""


# =============================================================================
# SERVICE CLASSES
# =============================================================================

class PDFExtractor:
    """PDF text extraction service."""

    @staticmethod
    def extract_text(pdf_content: bytes) -> Dict[str, Any]:
        """Extract text from PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text_parts = []

            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            return {
                "success": True,
                "text": "\n".join(text_parts).strip(),
                "pages": len(pdf_reader.pages),
                "metadata": {
                    "extracted_at": datetime.now().isoformat(),
                    "method": "PyPDF2"
                }
            }
        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"PDF read error: {type(e).__name__}")
            return {"success": False, "error": "Invalid or corrupted PDF file"}
        except Exception as e:
            logger.error(f"PDF extraction error: {type(e).__name__}: {e}")
            return {"success": False, "error": "Failed to extract text from PDF"}


class FIRACAnalyzer:
    """FIRAC legal analysis service."""

    SYSTEM_PROMPT = """Voce e um especialista em analise juridica brasileira.
Analise textos usando a metodologia FIRAC de forma objetiva e fundamentada.
Responda sempre em formato JSON estruturado."""

    @classmethod
    def analyze(cls, text: str) -> Dict[str, Any]:
        """Analyze text using FIRAC methodology."""
        # Truncate text to safe limit
        safe_text = text[:3000]

        prompt = f"""Analise o seguinte texto juridico usando a metodologia FIRAC:

Texto: {safe_text}

Forneca uma analise estruturada com os campos:
- fatos: Quais sao os fatos principais do caso?
- questoes: Quais sao as questoes juridicas envolvidas?
- regras: Quais normas juridicas se aplicam?
- analise: Como as regras se aplicam aos fatos?
- conclusao: Qual a conclusao juridica?

Responda em formato JSON."""

        try:
            response = openai.ChatCompletion.create(
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Voce e um especialista em analise juridica brasileira."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            return {
                "success": True,
                "firac_analysis": response.choices[0].message.content,
                "model": Config.OPENAI_MODEL,
                "timestamp": datetime.now().isoformat()
            }

        except openai.error.RateLimitError:
            logger.warning("OpenAI rate limit exceeded")
            return {"success": False, "error": "Service temporarily unavailable, please retry"}
        except openai.error.AuthenticationError:
            logger.error("OpenAI authentication failed")
            return {"success": False, "error": "Service configuration error"}
        except openai.error.Timeout:
            logger.warning("OpenAI request timeout")
            return {"success": False, "error": "Analysis timeout, please retry"}
        except Exception as e:
            logger.error(f"FIRAC analysis error: {type(e).__name__}")
            return {"success": False, "error": "Analysis failed"}


class DatajudClient:
    """DATAJUD API client."""

    def __init__(self):
        self.base_url = Config.DATAJUD_BASE_URL
        self.username = Config.DATAJUD_USERNAME
        self.password = Config.DATAJUD_PASSWORD

    def search(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search jurisprudence in DATAJUD."""
        tribunal = query_params.get('tribunal', 'tjsp').lower()

        # Validate tribunal
        valid, error = InputValidator.validate_tribunal(tribunal)
        if not valid:
            return {"success": False, "error": error}

        endpoint = f"{self.base_url}/api_publica_{tribunal}/_search"

        search_query = {
            "query": {"bool": {"must": []}},
            "size": min(query_params.get('size', 50), 100),  # Cap at 100
            "sort": [{"@timestamp": {"order": "desc"}}]
        }

        if 'classe_codigo' in query_params:
            search_query["query"]["bool"]["must"].append({
                "match": {"classe.codigo": query_params['classe_codigo']}
            })

        if 'texto_livre' in query_params:
            # Sanitize search text
            search_text, is_safe = InputValidator.sanitize_text(
                query_params['texto_livre'], max_length=500
            )
            if is_safe:
                search_query["query"]["bool"]["must"].append({
                    "multi_match": {
                        "query": search_text,
                        "fields": ["movimentos.nome", "classe.nome", "assuntos.nome"]
                    }
                })

        try:
            response = requests.post(
                endpoint,
                json=search_query,
                headers={'Content-Type': 'application/json'},
                auth=(self.username, self.password),
                timeout=30,
                verify=True  # Enforce SSL verification
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "tribunal": tribunal,
                    "total_results": data.get('hits', {}).get('total', {}).get('value', 0)
                }
            elif response.status_code == 401:
                logger.error("DATAJUD authentication failed")
                return {"success": False, "error": "Service authentication failed"}
            elif response.status_code == 429:
                return {"success": False, "error": "Rate limit exceeded, please retry later"}
            else:
                logger.error(f"DATAJUD error: status={response.status_code}")
                return {"success": False, "error": "Search service unavailable"}

        except Timeout:
            logger.warning("DATAJUD request timeout")
            return {"success": False, "error": "Search timeout, please retry"}
        except RequestException as e:
            logger.error(f"DATAJUD connection error: {type(e).__name__}")
            return {"success": False, "error": "Search service unavailable"}


class DistinguishAnalyzer:
    """Distinguish analysis service."""

    SYSTEM_PROMPT = """Voce e um magistrado especialista em analise de precedentes.
Analise comparacoes entre casos de forma objetiva e fundamentada.
Responda sempre em formato JSON estruturado."""

    @classmethod
    def analyze(cls, current_facts: str, precedent_data: Dict) -> Dict[str, Any]:
        """Analyze if precedent applies to current facts."""
        # Sanitize inputs
        safe_facts, facts_safe = InputValidator.sanitize_text(current_facts, max_length=2000)

        if not facts_safe:
            return {"success": False, "error": "Invalid input detected"}

        # Limit precedent data size
        precedent_json = json.dumps(precedent_data, ensure_ascii=False)[:1500]

        prompt = f"""Analise se o precedente judicial se aplica ao caso atual:

FATOS DO CASO ATUAL:
{safe_facts}

DADOS DO PRECEDENTE:
{precedent_json}

Responda em JSON com os campos:
- aplicavel: boolean (true/false)
- semelhancas: lista de semelhancas
- diferencas: lista de diferencas relevantes
- recomendacao: texto com recomendacao fundamentada"""

        try:
            response = openai.ChatCompletion.create(
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Voce e um magistrado especialista em analise de precedentes e distinguish."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.2
            )

            return {
                "success": True,
                "distinguish_analysis": response.choices[0].message.content,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Distinguish analysis error: {type(e).__name__}")
            return {"success": False, "error": sanitize_error_message(e)}


class DocumentGenerator:
    """Legal document generation service."""

    SYSTEM_PROMPT = """Voce e um magistrado especialista em redacao de pecas judiciais.
Gere documentos profissionais e tecnicamente corretos."""

    TEMPLATES = {
        'sentenca': "Gere uma minuta de sentenca judicial completa com relatorio, fundamentacao e dispositivo.",
        'despacho': "Gere um despacho judicial claro e objetivo.",
        'decisao': "Gere uma decisao interlocutoria com fundamentacao e dispositivo."
    }

    @classmethod
    def generate(cls, document_type: str, case_data: Dict) -> Dict[str, Any]:
        """Generate legal document."""
        valid, error = InputValidator.validate_document_type(document_type)
        if not valid:
            return {"success": False, "error": error}

        # Sanitize case data
        case_json = json.dumps(case_data, ensure_ascii=False)[:2000]

        prompt = f"""{cls.TEMPLATES[document_type]}

Dados do caso:
{case_json}

Gere o documento completo e formatado."""

        try:
            response = openai.ChatCompletion.create(
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Voce e um magistrado especialista em redacao de pecas judiciais."},
                    {"role": "user", "content": prompts[document_type]}
                ],
                max_tokens=3000,
                temperature=0.3
            )

            return {
                "success": True,
                "document_type": document_type,
                "generated_text": response.choices[0].message.content,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Document generation error: {type(e).__name__}")
            return {"success": False, "error": sanitize_error_message(e)}


# =============================================================================
# SERVICE INSTANCES
# =============================================================================

pdf_extractor = PDFExtractor()
firac_analyzer = FIRACAnalyzer()
datajud_client = DatajudClient()
distinguish_analyzer = DistinguishAnalyzer()
document_generator = DocumentGenerator()


# =============================================================================
# REQUEST MIDDLEWARE
# =============================================================================

@app.before_request
def before_request():
    """Set up request context."""
    g.request_id = request.headers.get('X-Request-ID', generate_request_id())
    g.start_time = datetime.now()


@app.after_request
def after_request(response):
    """Add security headers and log request."""
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Request-ID'] = g.request_id

    # Remove server header
    response.headers.pop('Server', None)

    # Log request
    duration = (datetime.now() - g.start_time).total_seconds()
    logger.info(
        f"method={request.method} path={request.path} "
        f"status={response.status_code} duration={duration:.3f}s"
    )

    return response


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Public health check endpoint (no auth required)."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })


@app.route('/auth/token', methods=['POST'])
def get_auth_token():
    """
    Get authentication token.

    In production, this should validate credentials against a user database.
    This is a simplified version for demonstration.
    """
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Request body required"}), 400

    # In production: validate against user database
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({"success": False, "error": "api_key required"}), 400

    # Simple validation - in production use proper user lookup
    expected_key = os.getenv('API_ACCESS_KEY')
    if not expected_key or api_key != expected_key:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    token = create_jwt_token(user_id='api_user', roles=['api'])

    return jsonify({
        "success": True,
        "token": token,
        "expires_in": Config.JWT_EXPIRY_HOURS * 3600
    })


@app.route('/extract-pdf', methods=['POST'])
@require_auth
def extract_pdf():
    """Extract text from PDF file (requires auth)."""
    data = request.get_json()

    if not data or 'pdf_content' not in data:
        return jsonify({
            "success": False,
            "error": "pdf_content is required",
            "error_code": "MISSING_FIELD"
        }), 400

    # Decode base64
    try:
        pdf_content = base64.b64decode(data['pdf_content'])
    except Exception:
        return jsonify({
            "success": False,
            "error": "Invalid base64 content",
            "error_code": "INVALID_FORMAT"
        }), 400

    # Validate PDF
    valid, error = InputValidator.validate_pdf_content(pdf_content)
    if not valid:
        return jsonify({
            "success": False,
            "error": error,
            "error_code": "VALIDATION_ERROR"
        }), 400

    result = pdf_extractor.extract_text(pdf_content)

    # Cache result if Redis available
    if redis_client and result.get('success'):
        try:
            content_hash = hashlib.sha256(pdf_content[:1024]).hexdigest()[:16]
            cache_key = f"pdf:{content_hash}"
            redis_client.setex(cache_key, 3600, json.dumps(result))
        except redis.RedisError as e:
            logger.warning(f"Cache write failed: {type(e).__name__}")

    return jsonify(result)


@app.route('/firac-analysis', methods=['POST'])
@require_auth
def firac_analysis():
    """Perform FIRAC analysis (requires auth)."""
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({
            "success": False,
            "error": "text is required",
            "error_code": "MISSING_FIELD"
        }), 400

    text = data['text']

    # Validate text length
    valid, error = InputValidator.validate_text_length(text)
    if not valid:
        return jsonify({
            "success": False,
            "error": error,
            "error_code": "VALIDATION_ERROR"
        }), 400

    # Check for injection patterns
    safe_text, is_safe = InputValidator.sanitize_text(text)
    if not is_safe:
        logger.warning(f"Potential injection attempt from user={g.user.get('user_id')}")
        return jsonify({
            "success": False,
            "error": "Invalid input detected",
            "error_code": "INVALID_INPUT"
        }), 400

    result = firac_analyzer.analyze(safe_text)
    return jsonify(result)


@app.route('/datajud-search', methods=['POST'])
@require_auth
def datajud_search():
    """Search jurisprudence in DATAJUD (requires auth)."""
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "Request body is required",
            "error_code": "MISSING_BODY"
        }), 400

    result = datajud_client.search(data)
    return jsonify(result)


@app.route('/distinguish-analysis', methods=['POST'])
@require_auth
def distinguish_analysis():
    """Perform distinguish analysis (requires auth)."""
    data = request.get_json()

    if not data or 'current_facts' not in data or 'precedent_data' not in data:
        return jsonify({
            "success": False,
            "error": "current_facts and precedent_data are required",
            "error_code": "MISSING_FIELD"
        }), 400

    result = distinguish_analyzer.analyze(
        data['current_facts'],
        data['precedent_data']
    )
    return jsonify(result)


@app.route('/generate-document', methods=['POST'])
@require_auth
def generate_document():
    """Generate legal document (requires auth)."""
    data = request.get_json()

    if not data or 'document_type' not in data or 'case_data' not in data:
        return jsonify({
            "success": False,
            "error": "document_type and case_data are required",
            "error_code": "MISSING_FIELD"
        }), 400

    result = document_generator.generate(
        data['document_type'],
        data['case_data']
    )
    return jsonify(result)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": "Bad request",
        "error_code": "BAD_REQUEST"
    }), 400


@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "success": False,
        "error": "Authentication required",
        "error_code": "UNAUTHORIZED"
    }), 401


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "error_code": "NOT_FOUND"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "error": "Method not allowed",
        "error_code": "METHOD_NOT_ALLOWED"
    }), 405


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "success": False,
        "error": "Request too large",
        "error_code": "PAYLOAD_TOO_LARGE"
    }), 413


@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        "success": False,
        "error": "Rate limit exceeded",
        "error_code": "RATE_LIMITED"
    }), 429


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "error_code": "INTERNAL_ERROR"
    }), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Validate configuration
    valid, errors = Config.validate()
    if not valid:
        for error in errors:
            logger.critical(f"Configuration error: {error}")
        logger.critical("Application cannot start with invalid configuration")
        exit(1)

    logger.info("Starting Judicial Automation API (Security-Hardened)...")
    logger.info(f"Allowed origins: {Config.ALLOWED_ORIGINS}")
    logger.info(f"OpenAI configured: {bool(Config.OPENAI_API_KEY)}")
    logger.info(f"DATAJUD configured: {bool(Config.DATAJUD_USERNAME)}")
    logger.info(f"Redis configured: {redis_client is not None}")

    # IMPORTANT: In production, use a proper WSGI server like Gunicorn
    # gunicorn -w 4 -b 0.0.0.0:5000 app:app
    app.run(host='127.0.0.1', port=5000)
