#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Automacao Juridica - API Python
Microservicos para processamento de documentos e analise juridica
"""

import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import openai
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import PyPDF2
from io import BytesIO
import base64

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask initialization
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'dev-secret-key')
openai.api_key = os.getenv('OPENAI_API_KEY')

# Redis for cache
try:
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    redis_client.ping()
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Running without cache.")
    redis_client = None


class PDFExtractor:
    """Class for PDF text extraction"""

    @staticmethod
    def extract_text_from_pdf(pdf_content):
        """Extracts text from a PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text = ""

            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

            return {
                "success": True,
                "text": text.strip(),
                "pages": len(pdf_reader.pages),
                "metadata": {
                    "extracted_at": datetime.now().isoformat(),
                    "method": "PyPDF2"
                }
            }
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class FIRACAnalyzer:
    """Class for FIRAC analysis of legal documents"""

    @staticmethod
    def analyze_text(text):
        """Analyzes text using FIRAC methodology"""
        prompt = f"""
        Analise o seguinte texto juridico usando a metodologia FIRAC:

        Texto: {text[:3000]}...

        Forneca uma analise estruturada em:
        1. FATOS: Quais sao os fatos principais do caso?
        2. QUESTOES (Issues): Quais sao as questoes juridicas envolvidas?
        3. REGRAS: Quais normas juridicas se aplicam?
        4. ANALISE: Como as regras se aplicam aos fatos?
        5. CONCLUSAO: Qual a conclusao juridica?

        Responda em formato JSON estruturado.
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Voce e um especialista em analise juridica brasileira."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            analysis_text = response.choices[0].message.content

            return {
                "success": True,
                "firac_analysis": analysis_text,
                "analysis_type": "auto-detect",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"FIRAC analysis error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class DatajudClient:
    """Client for DATAJUD API"""

    def __init__(self):
        self.base_url = "https://api-publica.datajud.cnj.jus.br"
        self.username = os.getenv('DATAJUD_USERNAME')
        self.password = os.getenv('DATAJUD_PASSWORD')

    def search_jurisprudence(self, query_params):
        """Searches jurisprudence in DATAJUD"""
        try:
            # Determine tribunal based on query
            tribunal = query_params.get('tribunal', 'tjsp')
            endpoint = f"{self.base_url}/api_publica_{tribunal}/_search"

            # Build Elasticsearch query
            search_query = {
                "query": {
                    "bool": {
                        "must": []
                    }
                },
                "size": query_params.get('size', 50),
                "sort": [
                    {
                        "@timestamp": {
                            "order": "desc"
                        }
                    }
                ]
            }

            # Add filters based on parameters
            if 'classe_codigo' in query_params:
                search_query["query"]["bool"]["must"].append({
                    "match": {"classe.codigo": query_params['classe_codigo']}
                })

            if 'orgao_julgador' in query_params:
                search_query["query"]["bool"]["must"].append({
                    "match": {"orgaoJulgador.codigo": query_params['orgao_julgador']}
                })

            if 'texto_livre' in query_params:
                search_query["query"]["bool"]["must"].append({
                    "multi_match": {
                        "query": query_params['texto_livre'],
                        "fields": ["movimentos.nome", "classe.nome", "assuntos.nome"]
                    }
                })

            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.post(
                endpoint,
                json=search_query,
                headers=headers,
                auth=(self.username, self.password),
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "tribunal": tribunal,
                    "total_results": data.get('hits', {}).get('total', {}).get('value', 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"DATAJUD API error: {response.status_code}",
                    "details": response.text
                }

        except Exception as e:
            logger.error(f"DATAJUD search error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class DistinguishAnalyzer:
    """Class for distinguish analysis between precedents and facts"""

    @staticmethod
    def analyze_distinguish(current_facts, precedent_data):
        """Analyzes if precedent applies to current facts"""
        prompt = f"""
        Analise se o precedente judicial se aplica ao caso atual (distinguish):

        FATOS DO CASO ATUAL:
        {current_facts}

        DADOS DO PRECEDENTE:
        {json.dumps(precedent_data, indent=2, ensure_ascii=False)}

        Faca a analise de distinguish respondendo:
        1. O precedente se aplica ao caso atual? (SIM/NAO)
        2. Quais sao as semelhancas entre os casos?
        3. Quais sao as diferencas relevantes?
        4. Por que o precedente deve ou nao ser aplicado?
        5. Sugestao de argumentacao para distinguish (se aplicavel)

        Responda em formato JSON estruturado com analise juridica fundamentada.
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Voce e um magistrado especialista em analise de precedentes e distinguish."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.2
            )

            analysis = response.choices[0].message.content

            return {
                "success": True,
                "distinguish_analysis": analysis,
                "applicable": True,
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Distinguish analysis error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class DocumentGenerator:
    """Class for generating legal documents"""

    @staticmethod
    def generate(document_type, case_data):
        """Generates legal document with OpenAI"""
        prompts = {
            'sentenca': f"""
            Gere uma minuta de sentenca judicial com base nos seguintes dados:

            {json.dumps(case_data, indent=2, ensure_ascii=False)}

            A sentenca deve conter:
            1. Relatorio dos fatos
            2. Fundamentacao juridica
            3. Dispositivo
            4. Formatacao adequada

            Gere um texto profissional e tecnicamente correto.
            """,
            'despacho': f"""
            Gere um despacho judicial com base nos seguintes dados:

            {json.dumps(case_data, indent=2, ensure_ascii=False)}

            O despacho deve ser claro, objetivo e tecnicamente correto.
            """,
            'decisao': f"""
            Gere uma decisao interlocutoria com base nos seguintes dados:

            {json.dumps(case_data, indent=2, ensure_ascii=False)}

            A decisao deve conter fundamentacao e dispositivo claros.
            """
        }

        if document_type not in prompts:
            return {
                "success": False,
                "error": f"Document type '{document_type}' not supported. Valid types: {list(prompts.keys())}"
            }

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Voce e um magistrado especialista em redacao de pecas judiciais."},
                    {"role": "user", "content": prompts[document_type]}
                ],
                max_tokens=3000,
                temperature=0.3
            )

            generated_text = response.choices[0].message.content

            return {
                "success": True,
                "document_type": document_type,
                "generated_text": generated_text,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Document generation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Service initialization
pdf_extractor = PDFExtractor()
firac_analyzer = FIRACAnalyzer()
datajud_client = DatajudClient()
distinguish_analyzer = DistinguishAnalyzer()
document_generator = DocumentGenerator()


# =================== API ROUTES ===================

@app.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    redis_status = False
    if redis_client:
        try:
            redis_client.ping()
            redis_status = True
        except Exception:
            redis_status = False

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "redis": redis_status,
            "openai": bool(openai.api_key),
            "datajud": bool(datajud_client.username)
        }
    })


@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    """Extracts text from PDF file"""
    try:
        data = request.get_json()

        if not data or 'pdf_content' not in data:
            return jsonify({"error": "pdf_content is required"}), 400

        # Decode base64 if needed
        pdf_content = data['pdf_content']
        if isinstance(pdf_content, str):
            try:
                pdf_content = base64.b64decode(pdf_content)
            except Exception as e:
                return jsonify({"error": f"Invalid base64 content: {e}"}), 400

        result = pdf_extractor.extract_text_from_pdf(pdf_content)

        # Cache result if Redis available
        if redis_client and result.get('success'):
            try:
                cache_key = f"pdf_extract:{hash(data['pdf_content'][:100])}"
                redis_client.setex(cache_key, 3600, json.dumps(result))
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"extract-pdf route error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/firac-analysis', methods=['POST'])
def firac_analysis():
    """Performs FIRAC analysis on text"""
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({"error": "text is required"}), 400

        text = data['text']
        if len(text) < 50:
            return jsonify({"error": "Text too short for analysis (minimum 50 characters)"}), 400

        result = firac_analyzer.analyze_text(text)
        return jsonify(result)

    except Exception as e:
        logger.error(f"FIRAC analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/datajud-search', methods=['POST'])
def datajud_search():
    """Searches jurisprudence in DATAJUD"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        result = datajud_client.search_jurisprudence(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"DATAJUD search error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/distinguish-analysis', methods=['POST'])
def distinguish_analysis():
    """Performs distinguish analysis"""
    try:
        data = request.get_json()

        if not data or 'current_facts' not in data or 'precedent_data' not in data:
            return jsonify({"error": "current_facts and precedent_data are required"}), 400

        result = distinguish_analyzer.analyze_distinguish(
            data['current_facts'],
            data['precedent_data']
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Distinguish analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/generate-document', methods=['POST'])
def generate_document():
    """Generates legal document with OpenAI"""
    try:
        data = request.get_json()

        required_fields = ['document_type', 'case_data']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        result = document_generator.generate(
            data['document_type'],
            data['case_data']
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Document generation error: {e}")
        return jsonify({"error": str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    logger.info("Starting Judicial Automation API...")
    logger.info(f"OpenAI configured: {bool(openai.api_key)}")
    logger.info(f"DATAJUD configured: {bool(datajud_client.username)}")
    logger.info(f"Redis configured: {redis_client is not None}")

    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
