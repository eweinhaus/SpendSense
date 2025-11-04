"""
OpenAI content generation module for SpendSense MVP.
Generates personalized recommendations using OpenAI API with fallback to templates.
"""

import os
import json
import logging
import sqlite3
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from .database import get_db_connection

# Configure logging
logger = logging.getLogger(__name__)

# Try to import OpenAI, but don't fail if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available. AI content generation will be disabled.")


class ContentGenerator:
    """
    Content generator using OpenAI API with caching and fallback support.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.cache = {}  # In-memory cache: {cache_key: {content: str, generated_at: datetime}}
        self.cache_ttl = timedelta(hours=24)  # Cache TTL: 24 hours
        
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAI package not installed. AI generation disabled.")
            elif not self.api_key:
                logger.warning("OPENAI_API_KEY not set. AI generation disabled.")
    
    def _cache_key(self, user_context: Dict) -> str:
        """
        Generate cache key from user context.
        
        Args:
            user_context: User context dictionary
            
        Returns:
            Cache key string (persona + signal combination)
        """
        persona = user_context.get('persona', 'unknown')
        # Get primary signal types for caching
        signal_types = []
        signals = user_context.get('signals', {})
        for signal_type in ['credit_utilization_max', 'credit_utilization_avg', 
                           'subscription_count', 'subscription_monthly_spend',
                           'savings_net_inflow_30d', 'savings_growth_rate_30d',
                           'income_variability', 'median_pay_gap']:
            if signal_type in signals:
                signal_value = signals[signal_type].get('value', 0)
                # Round to reduce cache misses for similar values
                if isinstance(signal_value, (int, float)):
                    if signal_type.startswith('credit_utilization'):
                        signal_value = round(signal_value / 10) * 10  # Round to nearest 10%
                    elif signal_type.startswith('subscription'):
                        signal_value = round(signal_value / 25) * 25  # Round to nearest $25
                    else:
                        signal_value = round(signal_value, 1)
                signal_types.append(f"{signal_type}:{signal_value}")
        
        signal_str = "_".join(signal_types[:3])  # Use first 3 signals for cache key
        return f"{persona}+{signal_str}"
    
    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """
        Check if content is cached and still valid.
        
        Args:
            cache_key: Cache key string
            
        Returns:
            Cached content dictionary or None if not found/expired
        """
        if cache_key not in self.cache:
            return None
        
        cached = self.cache[cache_key]
        if datetime.now() - cached['generated_at'] > self.cache_ttl:
            # Cache expired, remove it
            del self.cache[cache_key]
            return None
        
        return cached
    
    def _store_cache(self, cache_key: str, content: Dict) -> None:
        """
        Store content in cache.
        
        Args:
            cache_key: Cache key string
            content: Content dictionary to cache
        """
        self.cache[cache_key] = {
            'content': content,
            'generated_at': datetime.now()
        }
    
    def _build_prompt(self, user_context: Dict) -> str:
        """
        Build prompt for OpenAI API with user context.
        
        Args:
            user_context: User context dictionary with persona, signals, account details
            
        Returns:
            Prompt string for OpenAI API
        """
        persona = user_context.get('persona', 'unknown')
        persona_descriptions = {
            'high_utilization': 'High Credit Utilization (credit card utilization above 50%)',
            'variable_income_budgeter': 'Variable Income Budgeter (irregular income patterns)',
            'savings_builder': 'Savings Builder (actively building savings)',
            'financial_newcomer': 'Financial Newcomer (new to managing finances)',
            'subscription_heavy': 'Subscription-Heavy (multiple recurring subscriptions)',
            'neutral': 'Neutral (no specific financial patterns detected)'
        }
        persona_desc = persona_descriptions.get(persona, persona)
        
        signals = user_context.get('signals', {})
        signal_summary = []
        
        # Credit signals
        if 'credit_utilization_max' in signals:
            util = signals['credit_utilization_max'].get('value', 0)
            signal_summary.append(f"Credit utilization: {util:.0f}%")
        if 'credit_interest_charges' in signals:
            interest = signals['credit_interest_charges'].get('value', 0)
            if interest > 0:
                signal_summary.append(f"Monthly interest charges: ${interest:.2f}")
        
        # Subscription signals
        if 'subscription_count' in signals:
            sub_count = signals['subscription_count'].get('value', 0)
            signal_summary.append(f"Active subscriptions: {int(sub_count)}")
        if 'subscription_monthly_spend' in signals:
            sub_spend = signals['subscription_monthly_spend'].get('value', 0)
            if sub_spend > 0:
                signal_summary.append(f"Monthly subscription spend: ${sub_spend:.2f}")
        
        # Savings signals
        if 'savings_net_inflow_30d' in signals:
            inflow = signals['savings_net_inflow_30d'].get('value', 0)
            if inflow > 0:
                signal_summary.append(f"Monthly savings: ${inflow:.2f}")
        if 'savings_growth_rate_30d' in signals:
            growth = signals['savings_growth_rate_30d'].get('value', 0)
            if growth > 0:
                signal_summary.append(f"Savings growth rate: {growth:.2f}%")
        
        # Income signals
        if 'income_variability' in signals:
            variability = signals['income_variability'].get('value', 0)
            signal_summary.append(f"Income variability: {variability:.2f}")
        
        signal_text = "\n".join(signal_summary) if signal_summary else "No specific financial signals detected."
        
        # Account details
        accounts = user_context.get('accounts', [])
        account_summary = []
        for account in accounts[:3]:  # Limit to first 3 accounts
            acc_type = account.get('type', 'unknown')
            balance = account.get('current_balance', 0)
            if acc_type == 'credit':
                limit = account.get('limit', 0)
                account_summary.append(f"{acc_type} account: ${balance:.2f} balance, ${limit:.2f} limit")
            else:
                account_summary.append(f"{acc_type} account: ${balance:.2f} balance")
        
        account_text = "\n".join(account_summary) if account_summary else "No account details available."
        
        prompt = f"""You are a financial education assistant helping users understand their financial situation and make better decisions. Generate personalized, educational financial content.

User Profile:
- Persona: {persona_desc}
- Financial Signals: {signal_text}
- Account Details: {account_text}

Requirements:
1. Generate educational, supportive content (3-5 recommendations) that helps this user understand their financial situation
2. Use a non-judgmental, encouraging tone - NEVER use shaming language
3. Include specific data points from the user's profile in your recommendations
4. Focus on actionable advice, not generic financial tips
5. Each recommendation should include:
   - A clear title
   - Educational content explaining the concept
   - Specific data citations from the user's profile
   - Actionable steps the user can take

IMPORTANT: 
- DO NOT use phrases like "you're overspending", "you're doing it wrong", "you're bad with money", or any judgmental language
- Be supportive and educational, not critical
- Include the disclaimer: "This is educational content, not financial advice"

Return your response as a JSON array with this structure:
[
  {{
    "title": "Recommendation Title",
    "content": "Educational content with specific data citations...",
    "type": "article"
  }},
  ...
]

Generate 3-5 personalized recommendations for this user."""
        
        return prompt
    
    def generate_recommendation(self, user_context: Dict) -> Optional[Dict]:
        """
        Generate personalized recommendation using OpenAI API.
        
        Args:
            user_context: User context dictionary with:
                - persona: Persona type
                - signals: Dictionary of signal types to values
                - accounts: List of account dictionaries
        
        Returns:
            Dictionary with generated content or None if generation fails
        """
        if not self.client:
            logger.debug("OpenAI client not available, skipping AI generation")
            return None
        
        # Check cache first
        cache_key = self._cache_key(user_context)
        cached = self._check_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached['content']
        
        try:
            # Build prompt
            prompt = self._build_prompt(user_context)
            
            # Call OpenAI API
            logger.info(f"Calling OpenAI API for persona: {user_context.get('persona')}")
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model for initial implementation
                messages=[
                    {"role": "system", "content": "You are a financial education assistant. Always respond with valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON (may be wrapped in markdown code blocks)
            if content.startswith("```"):
                # Extract JSON from markdown code block
                lines = content.split("\n")
                json_start = None
                json_end = None
                for i, line in enumerate(lines):
                    if line.strip().startswith("```") and json_start is None:
                        json_start = i + 1
                    elif line.strip().startswith("```") and json_start is not None:
                        json_end = i
                        break
                
                if json_start is not None and json_end is not None:
                    content = "\n".join(lines[json_start:json_end])
                elif json_start is not None:
                    content = "\n".join(lines[json_start:])
            
            # Parse JSON
            try:
                recommendations = json.loads(content)
                if not isinstance(recommendations, list):
                    recommendations = [recommendations]
                
                # Cache the result
                result = {
                    'recommendations': recommendations,
                    'source': 'openai'
                }
                self._store_cache(cache_key, result)
                
                logger.info(f"Successfully generated {len(recommendations)} recommendations via OpenAI")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                logger.debug(f"Response content: {content[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return None


def get_content_generator() -> ContentGenerator:
    """
    Get or create a ContentGenerator instance.
    Uses singleton pattern to reuse the same instance and cache.
    
    Returns:
        ContentGenerator instance
    """
    if not hasattr(get_content_generator, '_instance'):
        get_content_generator._instance = ContentGenerator()
    return get_content_generator._instance

