from typing import Dict, Any, Optional
import asyncio
import openai
from openai import AsyncOpenAI

class OpenAITranslationService:
    """Service for handling text translation using OpenAI models."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialize the OpenAI translation service.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use for translation
        """
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)
        
    async def translate(
        self, 
        text: str, 
        source_lang: str = "ko", 
        target_lang: str = "en"
    ) -> str:
        """Translate text from source language to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        if not text:
            return ""
        
        # Create system prompt for translation
        system_prompt = f"""You are a professional translator. 
Translate the following text from {source_lang} to {target_lang}.
Provide ONLY the translation, with no additional text, explanations, or notes.
Maintain the original meaning, tone, and style as closely as possible.
"""
        
        try:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=1024,
            )
            
            # Extract translated text
            translated_text = response.choices[0].message.content.strip()
            return translated_text
            
        except Exception as e:
            # Log error
            print(f"Translation error: {e}")
            # Return original text if translation fails
            return f"[Translation Error] {text}"
