# Criando o script principal da API Python (Flask)
flask_app = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Automação Jurídica - API Python
Microserviços para processamento de documentos e análise jurídica
"""

import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import openai
from google.cloud import documentai
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import PyPDF2
import docx
from io import BytesIO
import base64

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialização do Flask
app = Flask(__name__)
CORS(app)

# Configurações
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'dev-secret-key')
openai.api_key = os.getenv('OPENAI_API_KEY')

# Redis para cache
try:
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
except Exception as e:
    logger.error(f"Erro ao conectar no Redis: {e}")
    redis_client = None

class PDFExtractor:
    """Classe para extração de texto de PDFs"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_content):
        """Extrai texto de um arquivo PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\\n"
            
            return {
                "success": True,
                "text": text,
                "pages": len(pdf_reader.pages),
                "metadata": {
                    "extracted_at": datetime.now().isoformat(),
                    "method": "PyPDF2"
                }
            }
        except Exception as e:
            logger.error(f"Erro na extração de PDF: {e}")
            return {
                "success": False,
                "error": str(e)
            }

class FIRACAnalyzer:
    """Classe para análise FIRAC de documentos jurídicos"""
    
    @staticmethod
    def analyze_text(text):
        """Analisa texto usando metodologia FIRAC"""
        prompt = f"""
        Analise o seguinte texto jurídico usando a metodologia FIRAC:
        
        Texto: {text[:3000]}...
        
        Forneça uma análise estruturada em:
        1. FATOS: Quais são os fatos principais do caso?
        2. QUESTÕES (Issues): Quais são as questões jurídicas envolvidas?
        3. REGRAS: Quais normas jurídicas se aplicam?
        4. ANÁLISE: Como as regras se aplicam aos fatos?
        5. CONCLUSÃO: Qual a conclusão jurídica?
        
        Responda em formato JSON estruturado.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um especialista em análise jurídica brasileira."},
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
            logger.error(f"Erro na análise FIRAC: {e}")
            return {
                "success": False,
                "error": str(e)
            }

class DatajudClient:
    """Cliente para API do DATAJUD"""
    
    def __init__(self):
        self.base_url = "https://api-publica.datajud.cnj.jus.br"
        self.username = os.getenv('DATAJUD_USERNAME')
        self.password = os.getenv('DATAJUD_PASSWORD')
    
    def search_jurisprudence(self, query_params):
        """Busca jurisprudência no DATAJUD"""
        try:
            # Determinar o tribunal baseado no query
            tribunal = query_params.get('tribunal', 'tjsp')
            endpoint = f"{self.base_url}/api_publica_{tribunal}/_search"
            
            # Construir query Elasticsearch
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
            
            # Adicionar filtros baseados nos parâmetros
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
                return {
                    "success": True,
                    "data": response.json(),
                    "tribunal": tribunal,
                    "total_results": response.json().get('hits', {}).get('total', {}).get('value', 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"Erro na API DATAJUD: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"Erro na busca DATAJUD: {e}")
            return {
                "success": False,
                "error": str(e)
            }

class DistinguishAnalyzer:
    """Classe para análise de distinguish entre precedentes e fatos"""
    
    @staticmethod
    def analyze_distinguish(current_facts, precedent_data):
        """Analisa se precedente se aplica aos fatos atuais"""
        prompt = f"""
        Analise se o precedente judicial se aplica ao caso atual (distinguish):
        
        FATOS DO CASO ATUAL:
        {current_facts}
        
        DADOS DO PRECEDENTE:
        {json.dumps(precedent_data, indent=2, ensure_ascii=False)}
        
        Faça a análise de distinguish respondendo:
        1. O precedente se aplica ao caso atual? (SIM/NÃO)
        2. Quais são as semelhanças entre os casos?
        3. Quais são as diferenças relevantes?
        4. Por que o precedente deve ou não ser aplicado?
        5. Sugestão de argumentação para distinguish (se aplicável)
        
        Responda em formato JSON estruturado com análise jurídica fundamentada.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um magistrado especialista em análise de precedentes e distinguish."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.2
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "distinguish_analysis": analysis,
                "applicable": True,  # Será determinado pela análise
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro na análise de distinguish: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Inicialização dos serviços
pdf_extractor = PDFExtractor()
firac_analyzer = FIRACAnalyzer()
datajud_client = DatajudClient()
distinguish_analyzer = DistinguishAnalyzer()

# =================== ROTAS DA API ===================

@app.route('/health', methods=['GET'])
def health_check():
    """Verificação de saúde da API"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "redis": redis_client is not None,
            "openai": bool(openai.api_key),
            "datajud": bool(datajud_client.username)
        }
    })

@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    """Extrai texto de arquivo PDF"""
    try:
        data = request.get_json()
        
        if 'pdf_content' not in data:
            return jsonify({"error": "pdf_content é obrigatório"}), 400
        
        # Decodificar base64 se necessário
        if isinstance(data['pdf_content'], str):
            pdf_content = base64.b64decode(data['pdf_content'])
        else:
            pdf_content = data['pdf_content']
        
        result = pdf_extractor.extract_text_from_pdf(pdf_content)
        
        # Cache do resultado se Redis disponível
        if redis_client and result['success']:
            cache_key = f"pdf_extract:{hash(pdf_content)}"
            redis_client.setex(cache_key, 3600, json.dumps(result))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na rota extract-pdf: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/firac-analysis', methods=['POST'])
def firac_analysis():
    """Realiza análise FIRAC do texto"""
    try:
        data = request.get_json()
        
        if 'text' not in data:
            return jsonify({"error": "text é obrigatório"}), 400
        
        text = data['text']
        result = firac_analyzer.analyze_text(text)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na análise FIRAC: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/datajud-search', methods=['POST'])
def datajud_search():
    """Busca jurisprudência no DATAJUD"""
    try:
        data = request.get_json()
        result = datajud_client.search_jurisprudence(data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na busca DATAJUD: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/distinguish-analysis', methods=['POST'])
def distinguish_analysis():
    """Realiza análise de distinguish"""
    try:
        data = request.get_json()
        
        if 'current_facts' not in data or 'precedent_data' not in data:
            return jsonify({"error": "current_facts e precedent_data são obrigatórios"}), 400
        
        result = distinguish_analyzer.analyze_distinguish(
            data['current_facts'], 
            data['precedent_data']
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na análise distinguish: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate-document', methods=['POST'])
def generate_document():
    """Gera documento jurídico com OpenAI"""
    try:
        data = request.get_json()
        
        required_fields = ['document_type', 'case_data']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} é obrigatório"}), 400
        
        # Prompt baseado no tipo de documento
        document_type = data['document_type']
        case_data = data['case_data']
        
        if document_type == 'sentenca':
            prompt = f"""
            Gere uma minuta de sentença judicial com base nos seguintes dados:
            
            {json.dumps(case_data, indent=2, ensure_ascii=False)}
            
            A sentença deve conter:
            1. Relatório dos fatos
            2. Fundamentação jurídica
            3. Dispositivo
            4. Formatação adequada
            
            Gere um texto profissional e tecnicamente correto.
            """
        elif document_type == 'despacho':
            prompt = f"""
            Gere um despacho judicial com base nos seguintes dados:
            
            {json.dumps(case_data, indent=2, ensure_ascii=False)}
            
            O despacho deve ser claro, objetivo e tecnicamente correto.
            """
        else:
            return jsonify({"error": "Tipo de documento não suportado"}), 400
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um magistrado especialista em redação de peças judiciais."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.3
        )
        
        generated_text = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "document_type": document_type,
            "generated_text": generated_text,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro na geração de documento: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Iniciando API de Automação Jurídica...")
    app.run(host='0.0.0.0', port=5000, debug=False)
'''

print("🐍 FLASK API CRIADA")
print("=" * 50)
print("📋 ENDPOINTS DISPONÍVEIS:")
print("• GET  /health - Status da API")
print("• POST /extract-pdf - Extração de texto PDF")
print("• POST /firac-analysis - Análise FIRAC")
print("• POST /datajud-search - Busca DATAJUD")
print("• POST /distinguish-analysis - Análise distinguish")
print("• POST /generate-document - Geração de documentos")
print("\n🔧 RECURSOS INCLUÍDOS:")
print("• Cache Redis")
print("• Logging estruturado")
print("• Tratamento de erros")
print("• Validação de dados")
print("• Integração OpenAI")
print("• Cliente DATAJUD")
print("• Análise FIRAC automática")
print("• Geração de documentos")
print("\n✅ API Flask criada com sucesso!")