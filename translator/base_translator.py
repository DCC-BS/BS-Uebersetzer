import ssl
from abc import ABC, abstractmethod
from typing import Optional

import httpx
import truststore
from openai import Client

from translator.config import LLMConfig, TranslationConfig
from translator.utils import detect_language

ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


class BaseTranslator(ABC):
    """Base class for all translators"""

    def __init__(self):
        self.llm_config = LLMConfig()
        self.translation_config = TranslationConfig()
        self.client = Client(
            base_url=self.llm_config.base_url,
            http_client=httpx.Client(verify=ssl_context),
        )

        models = self.client.models.list()
        self.model_name = models.data[0].id

    def _create_prompt(self, text: str, config: TranslationConfig) -> str:
        """Creates the translation prompt"""
        tone_prompt = self._get_tone_prompt(config.tone, config.domain)
        domain_prompt = self._get_domain_prompt(config.domain)
        glossary_prompt = self._get_glossary_prompt(config.glossary)

        return f"""You are an expert translator.\n
                Requirements:\n
                    1. Accuracy: The translation should be accurate and convey the same meaning as the original text.\n
                    2. Fluency: The translated text should be natural and fluent in the target language.\n
                    3. Style: Maintain the original style and tone of the text as much as possible.\n
                    4. Context: Consider the context enclosed in <context> </context> of the text when translating. The context may be empty.\n
                    5. No Unnecessary Translations: Do not translate proper nouns like names (e.g., "Yanick Schraner"), brands (e.g., "Apple"), places (e.g., "Basel-Stadt"), addresses, URLs, email addresses, phone numbers, or any element that would lose its meaning or functionality if translated. These should remain in their original form.\n
                    6. Domain-Specific Terminology: {domain_prompt} \n
                    7. Tone: {tone_prompt}\n
                    8. Idioms and Cultural References: Adapt idiomatic expressions and culturally specific references to their equivalents in the target language to maintain meaning and readability.\n
                    9. Source Text Errors: If there are any obvious errors or typos in the source text, correct them in the translation to improve clarity.
                    10. Formatting: Preserve the original markdown formatting of the text, including line breaks, bullet points, and any emphasis like bold or italics.\n
                    11. Special characters: Use '\n' for line breaks. Preserve line breaks and paragraphs as in the source text. Keep carriage return characters ('\r') if they are used in the source text.\n
                    12. Output Requirements: Provide only the translated text enclosed within <translation_text> </translation_text>. Do not add explanations, notes, comments, or any additional text outside of this.\n
                    13. Glossary: {glossary_prompt}
                      \n\n
                <example>\n
                  Translate the text enclosed in <source_text></source_text> from English to German. \n\n
                  <context> Imagine this text is part of a "Contact Us" section on the US website of a company that also operates in Germany. They want to provide their German customers with a translated version of this section. </context>\n
                  <source_text> Visit our website at www.example.com or call us at +1-555-123-4567.\n Our office is located at 123 Main Street, Anytown, USA. </source_text>\n
                  <translation_text> Besuchen Sie unsere Website unter www.example.com oder rufen Sie uns an unter +1-555-123-4567.\n Unser Büro befindet sich in der 123 Main Street, Anytown, USA. </translation_text>\n
                </example> \n\n
                Translate the text enclosed in <source_text> </source_text> from {config.source_language} to {config.target_language}. \n\n
                <context> {config.context} </context>\n
                <source_text> {text} </source_text>\n
                <translation_text> """

    def _get_tone_prompt(self, tone: Optional[str], domain: Optional[str]) -> str:
        """Generates the tone-specific part of the prompt"""
        if tone is None:
            return "Use a neutral tone that is objective, informative, and unbiased."

        tone_prompts = {
            "formal": "Use a formal and professional tone appropriate for official documents.",
            "informal": "Use an informal and conversational tone that is friendly and engaging.",
            "technical": f"Use a technical tone appropriate for {domain if domain else 'professional'} writing.",
        }
        return tone_prompts.get(tone.lower(), "Use a neutral tone.")

    def _get_domain_prompt(self, domain: Optional[str]) -> str:
        """Generates the domain-specific part of the prompt"""
        return (
            f"Use terminology specific to the {domain} field."
            if domain
            else "No specific domain requirements."
        )

    def _get_glossary_prompt(self, glossary: Optional[str]) -> str:
        """Generates the glossary-specific part of the prompt"""
        glossary = "\n".join(glossary.replace(":", ": ").split(";"))
        return (
            f"Use the following glossary to ensure accurate translations:\n{glossary}"
            if glossary
            else "No specific glossary provided."
        )

    def translate_text(self, text: str, config: TranslationConfig) -> str:
        """Base translation method"""
        if not text.strip() or len(text.strip()) == 1:
            return text

        if not config.source_language or config.source_language.lower() in [
            "auto",
            "automatisch erkennen",
        ]:
            config.source_language = detect_language(text)

        endswith_r = text.endswith("\r")

        prompt = self._create_prompt(text, config)
        response = self.client.completions.create(
            model=self.model_name,
            prompt=prompt,
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.num_ctx,
            frequency_penalty=self.llm_config.frequency_penalty,
            top_p=self.llm_config.top_p,
        )

        translation_text = self._process_response(response.response)
        return translation_text + ("\r" if endswith_r else "")

    def _process_response(self, text: str) -> str:
        """Process the translation response"""
        text = text.strip().replace("ß", "ss")
        start_index = (
            len("<translation_text>") if text.startswith("<translation_text>") else 0
        )
        end_index = text.find("</translation_text>")
        return text[start_index:end_index]

    @abstractmethod
    def translate(
        self, input_path: str, output_path: str, config: TranslationConfig
    ) -> None:
        """Abstract method to be implemented by specific translators"""
        pass
