"""
Tests for OpenAI content generation module.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path to import modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from spendsense.content_generator import ContentGenerator, get_content_generator


class TestContentGenerator:
    """Test ContentGenerator class."""
    
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            generator = ContentGenerator()
            assert generator.client is None
            assert generator.api_key is None
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            # Mock OpenAI import at module level
            with patch('openai.OpenAI') as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                # Reimport to get mocked OpenAI
                import importlib
                import spendsense.content_generator
                importlib.reload(spendsense.content_generator)
                generator = spendsense.content_generator.ContentGenerator()
                assert generator.api_key == 'test-key'
                # Client may be None if OpenAI package not installed
                # This test verifies the key is set correctly
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        generator = ContentGenerator()
        user_context = {
            'persona': 'high_utilization',
            'signals': {
                'credit_utilization_max': {'value': 75.0},
                'subscription_count': {'value': 5}
            }
        }
        cache_key = generator._cache_key(user_context)
        assert 'high_utilization' in cache_key
        assert isinstance(cache_key, str)
    
    def test_cache_storage_and_retrieval(self):
        """Test cache storage and retrieval."""
        generator = ContentGenerator()
        cache_key = "test_key"
        content = {"recommendations": [{"title": "Test"}]}
        
        generator._store_cache(cache_key, content)
        cached = generator._check_cache(cache_key)
        
        assert cached is not None
        assert cached['content'] == content
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        from datetime import datetime, timedelta
        generator = ContentGenerator()
        generator.cache_ttl = timedelta(seconds=0)  # Expire immediately
        
        cache_key = "test_key"
        content = {"recommendations": []}
        generator._store_cache(cache_key, content)
        
        cached = generator._check_cache(cache_key)
        assert cached is None  # Should be expired
    
    def test_build_prompt(self):
        """Test prompt building."""
        generator = ContentGenerator()
        user_context = {
            'persona': 'high_utilization',
            'signals': {
                'credit_utilization_max': {'value': 75.0},
                'credit_interest_charges': {'value': 50.0}
            },
            'accounts': [{'type': 'credit', 'current_balance': 5000, 'limit': 10000}]
        }
        
        prompt = generator._build_prompt(user_context)
        assert 'utilization' in prompt.lower()
        assert 'educational' in prompt.lower()
        assert 'credit' in prompt.lower()  # Should mention credit
    
    @patch('openai.OpenAI')
    def test_generate_recommendation_success(self, mock_openai_class):
        """Test successful recommendation generation."""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''[
            {
                "title": "Test Recommendation",
                "content": "Test content",
                "type": "article"
            }
        ]'''
        mock_client.chat.completions.create.return_value = mock_response
        
        generator = ContentGenerator(api_key='test-key')
        user_context = {
            'persona': 'high_utilization',
            'signals': {},
            'accounts': []
        }
        
        result = generator.generate_recommendation(user_context)
        
        assert result is not None
        assert 'recommendations' in result
        assert len(result['recommendations']) > 0
    
    @patch('openai.OpenAI')
    def test_generate_recommendation_api_failure(self, mock_openai_class):
        """Test handling of API failure."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        generator = ContentGenerator(api_key='test-key')
        user_context = {
            'persona': 'high_utilization',
            'signals': {},
            'accounts': []
        }
        
        result = generator.generate_recommendation(user_context)
        assert result is None
    
    @patch('openai.OpenAI')
    def test_generate_recommendation_invalid_json(self, mock_openai_class):
        """Test handling of invalid JSON response."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON"
        mock_client.chat.completions.create.return_value = mock_response
        
        generator = ContentGenerator(api_key='test-key')
        user_context = {
            'persona': 'high_utilization',
            'signals': {},
            'accounts': []
        }
        
        result = generator.generate_recommendation(user_context)
        assert result is None
    
    def test_get_content_generator_singleton(self):
        """Test singleton pattern for content generator."""
        generator1 = get_content_generator()
        generator2 = get_content_generator()
        assert generator1 is generator2

