import openai
import logging
from tqdm import tqdm
import os
import httpx
import contextlib
from contextvars import ContextVar
import zipfile
from lxml import etree
import re  # Import re for regular expressions
from file_utils import extract_document_xml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

tqdm_disabled = ContextVar("tqdm_disabled", default=False)
@contextlib.contextmanager
def suppress_output():
    """Context manager to temporarily suppress tqdm progress bars and logging."""
    original_log_level = logging.getLogger().level
    t = tqdm_disabled.set(True)
    try:
        logging.getLogger().setLevel(logging.CRITICAL + 1)
        yield
    finally:
        # Restore original logging state and re-enable tqdm
        logging.getLogger().setLevel(original_log_level)
        tqdm_disabled.reset(t)

def translate_text(text, target_language="de-CH", llm='gpt-4'):
    """Translate text using the LLM."""
    # Check if the text is empty or whitespace-only
    if not text.strip():
        # Return the text as is to preserve any whitespace or special characters
        return text

    if "pappai01" in os.getenv("BASE_URL", ""):
        client = openai.OpenAI(api_key="DummyValue", base_url=os.getenv("BASE_URL"))
    else:
        client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=httpx.Client(proxy=os.getenv("PROXY_URL")),
            base_url=os.getenv("BASE_URL")
        )

    prompt = (
        f"Please translate the following text into German (Switzerland):\n\n"
        f"Text:\n{text}\n\n"
        "Instructions:\n"
        "1. Translate the text into German (Switzerland).\n"
        "2. Replace any occurrences of 'ß' with 'ss'.\n"
        "3. Preserve all original formatting, including whitespace and special characters at the beginning and end of the text.\n"
        "4. Do not include any additional text or comments.\n\n"
        "IMPORTANT: Do not include any additional text, explanations, or comments. Only provide the translated text.\n"
    )

    try:
        logger.debug(f"Sending translation request for chunk of length {len(text)}")
        response = client.chat.completions.create(
            model=llm,
            messages=[
                {"role": "system", "content": (
                    "You are a professional translator. "
                    f"Translate the following text into {target_language}, ensuring proper grammar and spelling. "
                    "Preserve any whitespace or special characters at the beginning and end of the text."
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        translated_text = response.choices[0].message.content.strip()
        # Replace 'ß' with 'ss'
        translated_text = translated_text.replace('ß', 'ss')
        logger.debug(f"Translated text: {translated_text}")
        return translated_text
    except openai.OpenAIError as e:
        logger.error(f"An error occurred while translating text: {e}")
        return None

def translate_text_elements(xml_text, target_language="de-CH", llm='gpt-4'):
    """Translate the text content of each <w:t> element in the XML and update language codes."""
    # Parse XML to avoid disturbing structure and handle namespaces
    tree = etree.fromstring(xml_text.encode('utf-8'))
    namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    # Find all <w:t> tags
    text_elements = tree.findall(".//w:t", namespaces=namespace)

    logger.info(f"Found {len(text_elements)} <w:t> elements to translate.")

    for text_element in tqdm(text_elements, desc="Translating text elements", disable=tqdm_disabled.get()):
        original_text = text_element.text
        if original_text is not None:
            # Separate leading and trailing whitespace/special characters
            match = re.match(r'^(\s*)(.*?)(\s*)$', original_text, re.DOTALL)
            if match:
                leading_ws = match.group(1)
                core_text = match.group(2)
                trailing_ws = match.group(3)
            else:
                # If no match, treat the entire text as core_text
                leading_ws = ''
                core_text = original_text
                trailing_ws = ''

            if core_text.strip():
                # Translate the core text
                translated_text = translate_text(core_text, target_language, llm)
                if translated_text is not None:
                    # Reassemble the text
                    text_element.text = leading_ws + translated_text + trailing_ws
                else:
                    logger.warning("Translation failed for a text element. Keeping original text.")
                    text_element.text = original_text
            else:
                # Core text is empty or whitespace-only
                logger.debug("Whitespace-only core text encountered. Preserving original text.")
                text_element.text = original_text
        else:
            # Text element has no text content
            logger.debug("Empty text element encountered. Preserving as is.")
            text_element.text = original_text

    # Update language codes
    # Find all elements that have a <w:lang> attribute or child
    lang_elements = tree.xpath(".//w:*[@w:lang] | .//w:lang", namespaces=namespace)
    logger.info(f"Found {len(lang_elements)} elements with language attributes to update.")

    for elem in lang_elements:
        # Update language code to 'de-CH'
        if elem.tag.endswith('lang'):
            elem.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'] = target_language
        else:
            elem.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}lang'] = target_language

    # Return the entire translated XML as a string
    return etree.tostring(tree, encoding='utf-8').decode('utf-8')

def translate_document(docx_input_path, docx_output_path, target_language="de-CH", llm="gpt-4"):
    # Extract the raw XML text from document.xml
    xml_text = extract_document_xml(docx_input_path)

    # Translate each <w:t> element individually without disturbing the structure
    translated_xml_text = translate_text_elements(xml_text, target_language, llm)

    if translated_xml_text is None:
        logger.error("Translation process failed.")
        return

    # Write the modified XML content back to document.xml in a new .docx file
    with zipfile.ZipFile(docx_input_path, 'r') as docx, zipfile.ZipFile(docx_output_path, 'w') as docx_out:
        for item in docx.infolist():
            if item.filename != 'word/document.xml':
                # Copy other files unchanged
                docx_out.writestr(item, docx.read(item.filename))
            else:
                # Write the modified document.xml
                docx_out.writestr('word/document.xml', translated_xml_text)
