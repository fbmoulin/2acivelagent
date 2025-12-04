# Sistema de Automacao Juridica - Pytest Configuration
# conftest.py - Shared fixtures and configuration

import os
import sys
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import after path setup
from scripts.python.app import app, PDFExtractor, FIRACAnalyzer, DatajudClient, DistinguishAnalyzer, DocumentGenerator


@pytest.fixture
def client():
    """Create test client for Flask application"""
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    with app.test_client() as client:
        yield client


@pytest.fixture
def app_context():
    """Create application context"""
    with app.app_context():
        yield app


@pytest.fixture
def sample_pdf_content():
    """Generate a minimal valid PDF for testing"""
    # Minimal PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
306
%%EOF"""
    return pdf_content


@pytest.fixture
def sample_pdf_base64(sample_pdf_content):
    """Base64 encoded PDF content"""
    import base64
    return base64.b64encode(sample_pdf_content).decode('utf-8')


@pytest.fixture
def sample_legal_text():
    """Sample legal text for FIRAC analysis"""
    return """
    PROCESSO: 1234567-89.2023.8.26.0100
    AUTOR: JOAO DA SILVA
    REU: EMPRESA XYZ LTDA

    FATOS:
    O autor alega que celebrou contrato de prestacao de servicos com a re em 01/01/2023.
    O valor acordado foi de R$ 10.000,00 mensais. A re deixou de efetuar o pagamento
    das parcelas referentes aos meses de junho, julho e agosto de 2023, totalizando
    R$ 30.000,00 em debito.

    O autor notificou extrajudicialmente a re em 15/09/2023, sem obter resposta.

    PEDIDO:
    Requer a condenacao da re ao pagamento de R$ 30.000,00, acrescidos de juros
    e correcao monetaria, alem de honorarios advocaticios.
    """


@pytest.fixture
def sample_case_data():
    """Sample case data for document generation"""
    return {
        "case_number": "1234567-89.2023.8.26.0100",
        "tribunal": "TJSP",
        "court": "1a Vara Civel",
        "plaintiff": "Joao da Silva",
        "defendant": "Empresa XYZ Ltda",
        "claim_amount": 30000.00,
        "claim_type": "Cobranca",
        "facts": "Inadimplemento contratual",
        "legal_basis": "Art. 389 do Codigo Civil"
    }


@pytest.fixture
def sample_precedent_data():
    """Sample precedent data for distinguish analysis"""
    return {
        "case_number": "9876543-21.2022.8.26.0100",
        "tribunal": "TJSP",
        "decision_date": "2023-01-15",
        "summary": "Contrato de prestacao de servicos. Inadimplemento. Procedencia.",
        "holding": "Comprovado o inadimplemento, deve o devedor arcar com o pagamento.",
        "judges": ["Des. Maria Santos"],
        "subject": "Direito Civil - Obrigacoes"
    }


@pytest.fixture
def sample_datajud_response():
    """Sample DATAJUD API response"""
    return {
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_source": {
                        "numeroProcesso": "1234567-89.2023.8.26.0100",
                        "classe": {"codigo": 1116, "nome": "Procedimento Comum Civel"},
                        "orgaoJulgador": {"nome": "1a Vara Civel"},
                        "assuntos": [{"nome": "Cobranca"}],
                        "movimentos": [{"nome": "Sentenca Proferida"}]
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content=json.dumps({
            "fatos": "Contrato de prestacao de servicos inadimplido",
            "questoes": "Houve inadimplemento contratual?",
            "regras": "Art. 389 do Codigo Civil",
            "analise": "Restou comprovado o inadimplemento",
            "conclusao": "Procedencia do pedido"
        })))
    ]
    return mock_response


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    return mock


@pytest.fixture
def pdf_extractor():
    """PDFExtractor instance"""
    return PDFExtractor()


@pytest.fixture
def firac_analyzer():
    """FIRACAnalyzer instance"""
    return FIRACAnalyzer()


@pytest.fixture
def datajud_client():
    """DatajudClient instance"""
    return DatajudClient()


@pytest.fixture
def distinguish_analyzer():
    """DistinguishAnalyzer instance"""
    return DistinguishAnalyzer()


@pytest.fixture
def document_generator():
    """DocumentGenerator instance"""
    return DocumentGenerator()


# Markers for different test types
def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_api: mark test as requiring external API")
