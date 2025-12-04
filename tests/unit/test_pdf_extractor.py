# Sistema de Automacao Juridica - PDF Extractor Unit Tests

import pytest
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
import PyPDF2


class TestPDFExtractor:
    """Unit tests for PDFExtractor class"""

    @pytest.mark.unit
    def test_extract_text_success(self, pdf_extractor, sample_pdf_content):
        """Test successful PDF text extraction"""
        result = pdf_extractor.extract_text_from_pdf(sample_pdf_content)

        assert result['success'] is True
        assert 'text' in result
        assert 'pages' in result
        assert 'metadata' in result
        assert result['metadata']['method'] == 'PyPDF2'

    @pytest.mark.unit
    def test_extract_text_returns_page_count(self, pdf_extractor, sample_pdf_content):
        """Test that page count is returned"""
        result = pdf_extractor.extract_text_from_pdf(sample_pdf_content)

        assert result['success'] is True
        assert isinstance(result['pages'], int)
        assert result['pages'] >= 1

    @pytest.mark.unit
    def test_extract_text_invalid_pdf(self, pdf_extractor):
        """Test extraction from invalid PDF content"""
        invalid_content = b"This is not a PDF file"
        result = pdf_extractor.extract_text_from_pdf(invalid_content)

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.unit
    def test_extract_text_empty_content(self, pdf_extractor):
        """Test extraction from empty content"""
        result = pdf_extractor.extract_text_from_pdf(b"")

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.unit
    def test_extract_text_metadata_contains_timestamp(self, pdf_extractor, sample_pdf_content):
        """Test that metadata contains extraction timestamp"""
        result = pdf_extractor.extract_text_from_pdf(sample_pdf_content)

        assert result['success'] is True
        assert 'extracted_at' in result['metadata']

    @pytest.mark.unit
    def test_extract_text_handles_corrupted_pdf(self, pdf_extractor):
        """Test handling of corrupted PDF"""
        # Corrupted PDF header
        corrupted_content = b"%PDF-1.4\n%%EOF"
        result = pdf_extractor.extract_text_from_pdf(corrupted_content)

        # Should handle gracefully
        assert 'success' in result

    @pytest.mark.unit
    @patch('PyPDF2.PdfReader')
    def test_extract_text_multi_page(self, mock_pdf_reader, pdf_extractor):
        """Test extraction from multi-page PDF"""
        # Mock multiple pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        result = pdf_extractor.extract_text_from_pdf(b"dummy pdf content")

        assert result['success'] is True
        assert result['pages'] == 2
        assert "Page 1 content" in result['text']
        assert "Page 2 content" in result['text']

    @pytest.mark.unit
    @patch('PyPDF2.PdfReader')
    def test_extract_text_empty_pages(self, mock_pdf_reader, pdf_extractor):
        """Test extraction from PDF with empty pages"""
        mock_page = Mock()
        mock_page.extract_text.return_value = None

        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        result = pdf_extractor.extract_text_from_pdf(b"dummy pdf content")

        assert result['success'] is True
        assert result['text'] == ""
