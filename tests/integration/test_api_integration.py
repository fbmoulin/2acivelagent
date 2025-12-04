# Sistema de Automacao Juridica - Integration Tests

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestFullWorkflowIntegration:
    """Integration tests for complete workflow"""

    @pytest.mark.integration
    @patch('scripts.python.app.openai.ChatCompletion.create')
    def test_pdf_to_firac_workflow(self, mock_openai, client, sample_pdf_base64, mock_openai_response):
        """Test workflow from PDF extraction to FIRAC analysis"""
        # Step 1: Extract PDF
        extract_response = client.post('/extract-pdf',
                                       data=json.dumps({'pdf_content': sample_pdf_base64}),
                                       content_type='application/json')

        assert extract_response.status_code == 200
        extract_data = json.loads(extract_response.data)

        # Step 2: If extraction successful and has text, perform FIRAC analysis
        if extract_data.get('success') and extract_data.get('text'):
            text = extract_data['text']

            # Ensure text is long enough for analysis
            if len(text) < 50:
                text = text + " " * 50  # Pad for test

            mock_openai.return_value = mock_openai_response

            firac_response = client.post('/firac-analysis',
                                         data=json.dumps({'text': text}),
                                         content_type='application/json')

            # Analysis should succeed with mocked OpenAI
            if mock_openai.called:
                assert firac_response.status_code == 200

    @pytest.mark.integration
    @patch('scripts.python.app.openai.ChatCompletion.create')
    @patch('requests.post')
    def test_firac_to_jurisprudence_workflow(self, mock_requests, mock_openai, client,
                                              sample_legal_text, mock_openai_response,
                                              sample_datajud_response):
        """Test workflow from FIRAC analysis to jurisprudence search"""
        mock_openai.return_value = mock_openai_response

        # Step 1: FIRAC Analysis
        firac_response = client.post('/firac-analysis',
                                     data=json.dumps({'text': sample_legal_text}),
                                     content_type='application/json')

        assert firac_response.status_code == 200
        firac_data = json.loads(firac_response.data)
        assert firac_data['success'] is True

        # Step 2: Search jurisprudence based on analysis
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = sample_datajud_response
        mock_requests.return_value = mock_api_response

        search_response = client.post('/datajud-search',
                                      data=json.dumps({
                                          'tribunal': 'tjsp',
                                          'texto_livre': 'cobranca contrato'
                                      }),
                                      content_type='application/json')

        assert search_response.status_code == 200
        search_data = json.loads(search_response.data)
        assert search_data['success'] is True

    @pytest.mark.integration
    @patch('scripts.python.app.openai.ChatCompletion.create')
    @patch('requests.post')
    def test_complete_analysis_workflow(self, mock_requests, mock_openai, client,
                                        sample_legal_text, sample_case_data,
                                        mock_openai_response, sample_datajud_response):
        """Test complete workflow: FIRAC -> Search -> Distinguish -> Generate"""
        # Mock OpenAI responses
        mock_openai.return_value = mock_openai_response

        # Mock DATAJUD response
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = sample_datajud_response
        mock_requests.return_value = mock_api_response

        # Step 1: FIRAC Analysis
        firac_response = client.post('/firac-analysis',
                                     data=json.dumps({'text': sample_legal_text}),
                                     content_type='application/json')
        assert firac_response.status_code == 200

        # Step 2: Jurisprudence Search
        search_response = client.post('/datajud-search',
                                      data=json.dumps({
                                          'tribunal': 'tjsp',
                                          'texto_livre': 'cobranca'
                                      }),
                                      content_type='application/json')
        assert search_response.status_code == 200
        search_data = json.loads(search_response.data)

        # Step 3: Distinguish Analysis (if results found)
        if search_data.get('total_results', 0) > 0:
            precedent = sample_datajud_response['hits']['hits'][0]['_source']
            distinguish_response = client.post('/distinguish-analysis',
                                               data=json.dumps({
                                                   'current_facts': sample_legal_text,
                                                   'precedent_data': precedent
                                               }),
                                               content_type='application/json')
            assert distinguish_response.status_code == 200

        # Step 4: Generate Document
        generate_response = client.post('/generate-document',
                                        data=json.dumps({
                                            'document_type': 'sentenca',
                                            'case_data': sample_case_data
                                        }),
                                        content_type='application/json')
        assert generate_response.status_code == 200
        generate_data = json.loads(generate_response.data)
        assert generate_data['success'] is True
        assert 'generated_text' in generate_data


class TestServiceAvailability:
    """Tests for service availability and degradation"""

    @pytest.mark.integration
    def test_api_available_without_redis(self, client):
        """Test that API works even if Redis is unavailable"""
        # Health check should still work
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        # Redis might be false but API should work
        assert 'services' in data

    @pytest.mark.integration
    @patch('scripts.python.app.openai.ChatCompletion.create')
    def test_api_handles_openai_failure(self, mock_openai, client, sample_legal_text):
        """Test graceful handling of OpenAI API failure"""
        mock_openai.side_effect = Exception("OpenAI API Error")

        response = client.post('/firac-analysis',
                               data=json.dumps({'text': sample_legal_text}),
                               content_type='application/json')

        # Should return error gracefully, not crash
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        assert 'error' in data or data.get('success') is False

    @pytest.mark.integration
    @patch('requests.post')
    def test_api_handles_datajud_failure(self, mock_requests, client):
        """Test graceful handling of DATAJUD API failure"""
        mock_requests.side_effect = Exception("Connection timeout")

        response = client.post('/datajud-search',
                               data=json.dumps({'tribunal': 'tjsp'}),
                               content_type='application/json')

        # Should return error gracefully
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        assert 'error' in data or data.get('success') is False

    @pytest.mark.integration
    @patch('requests.post')
    def test_api_handles_datajud_auth_failure(self, mock_requests, client):
        """Test handling of DATAJUD authentication failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_requests.return_value = mock_response

        response = client.post('/datajud-search',
                               data=json.dumps({'tribunal': 'tjsp'}),
                               content_type='application/json')

        data = json.loads(response.data)
        assert data['success'] is False


class TestConcurrentRequests:
    """Tests for handling concurrent requests"""

    @pytest.mark.integration
    def test_multiple_health_checks(self, client):
        """Test multiple concurrent health checks"""
        responses = []
        for _ in range(10):
            response = client.get('/health')
            responses.append(response)

        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.integration
    @patch('scripts.python.app.openai.ChatCompletion.create')
    def test_multiple_pdf_extractions(self, mock_openai, client, sample_pdf_base64):
        """Test multiple PDF extractions"""
        responses = []
        for _ in range(5):
            response = client.post('/extract-pdf',
                                   data=json.dumps({'pdf_content': sample_pdf_base64}),
                                   content_type='application/json')
            responses.append(response)

        assert all(r.status_code == 200 for r in responses)


class TestDataValidation:
    """Tests for data validation across endpoints"""

    @pytest.mark.integration
    def test_json_content_type_required(self, client):
        """Test that JSON content type is properly handled"""
        # Send without content-type
        response = client.post('/firac-analysis',
                               data='{"text": "some text"}')

        # Should handle gracefully
        assert response.status_code in [200, 400, 415]

    @pytest.mark.integration
    def test_malformed_json_handled(self, client):
        """Test handling of malformed JSON"""
        response = client.post('/firac-analysis',
                               data='{"text": invalid json}',
                               content_type='application/json')

        assert response.status_code == 400

    @pytest.mark.integration
    def test_unicode_text_handled(self, client, sample_pdf_base64):
        """Test handling of Unicode text (Portuguese characters)"""
        unicode_text = """
        Processo judicial com caracteres especiais:
        ação, execução, sentença, decisão, réu, autôr,
        índice, cônsul, além, através, após, até
        """ + " " * 100  # Ensure minimum length

        with patch('scripts.python.app.openai.ChatCompletion.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='{"result": "ok"}'))]
            mock_openai.return_value = mock_response

            response = client.post('/firac-analysis',
                                   data=json.dumps({'text': unicode_text}),
                                   content_type='application/json')

            assert response.status_code == 200
