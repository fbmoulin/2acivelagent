# Sistema de Automacao Juridica - API Routes Unit Tests

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    @pytest.mark.unit
    def test_health_check_returns_200(self, client):
        """Test health endpoint returns 200 OK"""
        response = client.get('/health')

        assert response.status_code == 200

    @pytest.mark.unit
    def test_health_check_returns_json(self, client):
        """Test health endpoint returns JSON"""
        response = client.get('/health')

        assert response.content_type == 'application/json'

    @pytest.mark.unit
    def test_health_check_contains_status(self, client):
        """Test health response contains status field"""
        response = client.get('/health')
        data = json.loads(response.data)

        assert 'status' in data
        assert data['status'] == 'healthy'

    @pytest.mark.unit
    def test_health_check_contains_services(self, client):
        """Test health response contains services status"""
        response = client.get('/health')
        data = json.loads(response.data)

        assert 'services' in data
        assert 'redis' in data['services']
        assert 'openai' in data['services']
        assert 'datajud' in data['services']

    @pytest.mark.unit
    def test_health_check_contains_version(self, client):
        """Test health response contains version"""
        response = client.get('/health')
        data = json.loads(response.data)

        assert 'version' in data
        assert data['version'] == '1.0.0'


class TestExtractPDFEndpoint:
    """Tests for /extract-pdf endpoint"""

    @pytest.mark.unit
    def test_extract_pdf_requires_pdf_content(self, client):
        """Test that pdf_content is required"""
        response = client.post('/extract-pdf',
                               data=json.dumps({}),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_extract_pdf_accepts_base64(self, client, sample_pdf_base64):
        """Test that base64 encoded PDF is accepted"""
        response = client.post('/extract-pdf',
                               data=json.dumps({'pdf_content': sample_pdf_base64}),
                               content_type='application/json')

        assert response.status_code == 200

    @pytest.mark.unit
    def test_extract_pdf_returns_text(self, client, sample_pdf_base64):
        """Test that extracted text is returned"""
        response = client.post('/extract-pdf',
                               data=json.dumps({'pdf_content': sample_pdf_base64}),
                               content_type='application/json')

        data = json.loads(response.data)
        assert 'text' in data or 'error' in data

    @pytest.mark.unit
    def test_extract_pdf_invalid_base64(self, client):
        """Test handling of invalid base64 content"""
        response = client.post('/extract-pdf',
                               data=json.dumps({'pdf_content': 'not-valid-base64!!!'}),
                               content_type='application/json')

        assert response.status_code in [400, 500]

    @pytest.mark.unit
    def test_extract_pdf_empty_request(self, client):
        """Test handling of empty request body"""
        response = client.post('/extract-pdf',
                               data='',
                               content_type='application/json')

        assert response.status_code == 400


class TestFIRACAnalysisEndpoint:
    """Tests for /firac-analysis endpoint"""

    @pytest.mark.unit
    def test_firac_requires_text(self, client):
        """Test that text field is required"""
        response = client.post('/firac-analysis',
                               data=json.dumps({}),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_firac_rejects_short_text(self, client):
        """Test that very short text is rejected"""
        response = client.post('/firac-analysis',
                               data=json.dumps({'text': 'Too short'}),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'short' in data['error'].lower() or 'minimum' in data['error'].lower()

    @pytest.mark.unit
    @patch('scripts.python.app.openai_client.chat.completions.create')
    def test_firac_calls_openai(self, mock_openai, client, sample_legal_text, mock_openai_response):
        """Test that OpenAI is called for analysis"""
        mock_openai.return_value = mock_openai_response

        response = client.post('/firac-analysis',
                               data=json.dumps({'text': sample_legal_text}),
                               content_type='application/json')

        mock_openai.assert_called_once()

    @pytest.mark.unit
    @patch('scripts.python.app.openai_client.chat.completions.create')
    def test_firac_returns_analysis(self, mock_openai, client, sample_legal_text, mock_openai_response):
        """Test that FIRAC analysis is returned"""
        mock_openai.return_value = mock_openai_response

        response = client.post('/firac-analysis',
                               data=json.dumps({'text': sample_legal_text}),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'firac_analysis' in data


class TestDatajudSearchEndpoint:
    """Tests for /datajud-search endpoint"""

    @pytest.mark.unit
    def test_datajud_accepts_empty_params(self, client):
        """Test that empty params returns error or default search"""
        response = client.post('/datajud-search',
                               data=json.dumps({}),
                               content_type='application/json')

        # Should return 200 with error in body or perform default search
        assert response.status_code in [200, 400]

    @pytest.mark.unit
    @patch('requests.post')
    def test_datajud_calls_api(self, mock_post, client):
        """Test that DATAJUD API is called"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_post.return_value = mock_response

        response = client.post('/datajud-search',
                               data=json.dumps({
                                   'tribunal': 'tjsp',
                                   'texto_livre': 'execucao fiscal'
                               }),
                               content_type='application/json')

        mock_post.assert_called_once()

    @pytest.mark.unit
    @patch('requests.post')
    def test_datajud_returns_results(self, mock_post, client, sample_datajud_response):
        """Test that search results are returned"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_datajud_response
        mock_post.return_value = mock_response

        response = client.post('/datajud-search',
                               data=json.dumps({'tribunal': 'tjsp'}),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'total_results' in data


class TestDistinguishAnalysisEndpoint:
    """Tests for /distinguish-analysis endpoint"""

    @pytest.mark.unit
    def test_distinguish_requires_current_facts(self, client, sample_precedent_data):
        """Test that current_facts is required"""
        response = client.post('/distinguish-analysis',
                               data=json.dumps({'precedent_data': sample_precedent_data}),
                               content_type='application/json')

        assert response.status_code == 400

    @pytest.mark.unit
    def test_distinguish_requires_precedent_data(self, client):
        """Test that precedent_data is required"""
        response = client.post('/distinguish-analysis',
                               data=json.dumps({'current_facts': 'Some facts'}),
                               content_type='application/json')

        assert response.status_code == 400

    @pytest.mark.unit
    @patch('scripts.python.app.openai_client.chat.completions.create')
    def test_distinguish_returns_analysis(self, mock_openai, client, sample_legal_text,
                                          sample_precedent_data, mock_openai_response):
        """Test that distinguish analysis is returned"""
        mock_openai.return_value = mock_openai_response

        response = client.post('/distinguish-analysis',
                               data=json.dumps({
                                   'current_facts': sample_legal_text,
                                   'precedent_data': sample_precedent_data
                               }),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestGenerateDocumentEndpoint:
    """Tests for /generate-document endpoint"""

    @pytest.mark.unit
    def test_generate_requires_document_type(self, client, sample_case_data):
        """Test that document_type is required"""
        response = client.post('/generate-document',
                               data=json.dumps({'case_data': sample_case_data}),
                               content_type='application/json')

        assert response.status_code == 400

    @pytest.mark.unit
    def test_generate_requires_case_data(self, client):
        """Test that case_data is required"""
        response = client.post('/generate-document',
                               data=json.dumps({'document_type': 'sentenca'}),
                               content_type='application/json')

        assert response.status_code == 400

    @pytest.mark.unit
    @patch('scripts.python.app.openai_client.chat.completions.create')
    def test_generate_sentenca(self, mock_openai, client, sample_case_data):
        """Test generating sentenca document"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Generated sentenca content"))]
        mock_openai.return_value = mock_response

        response = client.post('/generate-document',
                               data=json.dumps({
                                   'document_type': 'sentenca',
                                   'case_data': sample_case_data
                               }),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['document_type'] == 'sentenca'

    @pytest.mark.unit
    @patch('scripts.python.app.openai_client.chat.completions.create')
    def test_generate_despacho(self, mock_openai, client, sample_case_data):
        """Test generating despacho document"""
        mock_response = Mock()

        mock_openai.return_value = mock_response

        response = client.post('/generate-document',
                               data=json.dumps({
                                   'document_type': 'despacho',
                                   'case_data': sample_case_data
                               }),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['document_type'] == 'despacho'

    @pytest.mark.unit
    def test_generate_invalid_type(self, client, sample_case_data):
        """Test that invalid document type returns error"""
        response = client.post('/generate-document',
                               data=json.dumps({
                                   'document_type': 'invalid_type',
                                   'case_data': sample_case_data
                               }),
                               content_type='application/json')

        # The endpoint should handle this - either 400 or 200 with error
        data = json.loads(response.data)
        assert data['success'] is False or response.status_code == 400


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.unit
    def test_404_returns_json(self, client):
        """Test that 404 errors return JSON"""
        response = client.get('/nonexistent-endpoint')

        assert response.status_code == 404
        assert response.content_type == 'application/json'

    @pytest.mark.unit
    def test_method_not_allowed(self, client):
        """Test handling of wrong HTTP method"""
        response = client.get('/extract-pdf')

        assert response.status_code == 405
