import os
from typing import Optional
import zipfile
import shutil
import tempfile
from utils import detect_language

# import xml.etree.ElementTree as ET
from lxml import etree as ET
import openai
from dotenv import load_dotenv

load_dotenv()


client = openai.OpenAI(api_key="ABC", base_url=os.environ.get("BASE_URL"))
# Namespaces used in Word XML
namespaces = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
}

# Register namespaces to preserve them in the output XML
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)


def translate_text(
    text: str,
    context: str = None,
    target_language: str = "German",
    source_language: Optional[str] = None,
    domain: Optional[str] = None,
    tone: Optional[str] = None,
) -> str:
    """
    Translates text to German using the LLM.
    Ensures that XML tags within the text are preserved.

    Args:
      text (str): The text to be translated.
      context (str, optional): Additional context for the translation.
      target_language (str, optional): The target language for the translation. Defaults to German.
      source_language (str, optional): The source language for the translation. Defaults to auto-detection.
      domain (str, optional): The domain for the translation.
      tone (str, optional): The tone for the translation.
    Returns:
      str: The translated text.
    """
    # Handle empty texts
    if not text.strip() or len(text.strip()) == 1:
        return text

    if source_language is None or source_language == "auto":
        source_language = detect_language(text)

    endswith_r = text.endswith("\r")

    if tone is None:
        tone_prompt = "Use a neutral tone that is objective, informative, and unbiased."
    elif tone.lower() == "formal":
        tone_prompt = "Use a formal and professional tone appropriate for official documents, academic writing, or business communications."
    elif tone.lower() == "informal":
        tone_prompt = (
            "Use an informal and conversational tone that is friendly and engaging."
        )
    elif tone.lower() == "technical":
        if domain:
            tone_prompt = f"Use a technical and specialized tone appropriate for {domain}, incorporating industry-specific terminology."
        else:
            tone_prompt = (
                "Use a technical and specialized tone appropriate professional writing."
            )
    else:
        tone_prompt = "Use a neutral tone that is objective, informative, and unbiased."

    if domain is not None:
        domain_prompt= f"Use terminology and phrases specific to the {domain} to ensure the translation is appropriate for the field."
    else:
        domain_prompt = "No specific domain requirements."

    prompt = f"""You are an expert translator.\n
                Requirements:\n
                    1. Accuracy: The translation should be accurate and convey the same meaning as the original text.\n
                    2. Fluency: The translated text should be natural and fluent in the target language.\n
                    3. Style: Maintain the original style and tone of the text as much as possible.\n
                    4. Context: Consider the context enclosed in <context></context> of the text when translating. The context may be empty.\n
                    5. No Unnecessary Translations: Do not translate proper nouns like names (e.g., "Yanick Schraner"), brands (e.g., "Apple"), places (e.g., "Basel-Stadt"), addresses, URLs, email addresses, phone numbers, or any element that would lose its meaning or functionality if translated. These should remain in their original form.\n
                    6. Domain-Specific Terminology: {domain_prompt} \n
                    7. Tone: {tone_prompt}\n
                    8. Idioms and Cultural References: Adapt idiomatic expressions and culturally specific references to their equivalents in the target language to maintain meaning and readability.\n
                    9. Source Text Errors: If there are any obvious errors or typos in the source text, correct them in the translation to improve clarity.
                    10. Formatting: Preserve the original formatting of the text, including line breaks, bullet points, and any emphasis like bold or italics.\n
                    11. Special characters: Use '\n' for line breaks. Preserve line breaks and paragraphs as in the source text. Keep carriage return characters ('\r') if they are used in the source text.\n
                    12. Output Requirements: Provide only the translated text enclosed within <translated_text></translated_text>. Do not add explanations, notes, comments, or any additional text outside of this.
                      \n\n
                <example>\n
                  Translate the text enclosed in <source_text></source_text> from English to German. \n\n
                  <context>Imagine this text is part of a "Contact Us" section on the US website of a company that also operates in Germany. They want to provide their German customers with a translated version of this section.</context>\n
                  <source_text>Visit our website at www.example.com or call us at +1-555-123-4567.\n Our office is located at 123 Main Street, Anytown, USA.</source_text>\n
                  <translated_text>Besuchen Sie unsere Website unter www.example.com oder rufen Sie uns an unter +1-555-123-4567.\n Unser Büro befindet sich in der 123 Main Street, Anytown, USA.</translated_text>\n
                </example> \n\n
                Translate the text enclosed in <source_text></source_text> from {source_language} to {target_language}. \n\n
                <context>{context}</context>\n
                <source_text>{text}</source_text>\n
                <translated_text>"""
    response = client.completions.create(
        model="llama3.1:70b",
        prompt=prompt,
        temperature=0,
    )
    translated_text = response.choices[0].text.strip()
    translated_text = translated_text.replace("ß", "ss")

    start_index = translated_text.find("<translated_text>") + len("<translated_text>")
    end_index = translated_text.find("</translated_text>")
    translated_text = translated_text[start_index:end_index]

    translated_text += "\r" if endswith_r else ""
    return translated_text


def get_run_properties(elem):
    """Get the formatting properties of a text run"""
    parent_run = elem.getparent()  # Get the parent 'w:r' element
    if parent_run is not None:
        props = parent_run.find(".//w:rPr", namespaces=namespaces)
        return ET.tostring(props) if props is not None else None
    return None


def process_xml(
    file_path: str,
    target_language: str = "German",
    source_language: Optional[str] = None,
    tone: Optional[str] = None,
    domain: Optional[str] = None,
) -> None:
    """
    Parses and translates text within an XML file while preserving the structure.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    previous_translation = ""

    # Find all paragraphs
    for paragraph in root.findall(".//w:p", namespaces=namespaces):
        current_text = []
        current_format = None
        current_elem = None

        # Iterate through text elements in the paragraph
        for elem in paragraph.findall(".//w:t", namespaces=namespaces):
            if not elem.text or not elem.text.strip():
                continue

            elem_format = get_run_properties(elem)

            # If this element has the same formatting as previous elements, combine them
            if elem_format == current_format:
                current_text.append(elem.text)
                elem.text = ""  # Clear the current element's text
            else:
                # Translate and clear accumulated text if we have any
                if current_text and current_elem is not None:
                    combined_text = "".join(current_text)
                    current_elem.text = translate_text(
                        text=combined_text,
                        context=previous_translation,
                        target_language=target_language,
                        source_language=source_language,
                        domain=domain,
                        tone=tone,
                    )
                    previous_translation = current_elem.text

                # Start new accumulation
                current_text = [elem.text]
                current_format = elem_format
                current_elem = elem

        # Handle the last group of text
        if current_text and current_elem is not None:
            combined_text = "".join(current_text)
            current_elem.text = translate_text(
                text=combined_text,
                context=previous_translation,
                target_language=target_language,
                source_language=source_language,
                domain=domain,
                tone=tone,
            )

    # Write the modified XML back to file
    tree.write(file_path, xml_declaration=True, encoding="UTF-8", method="xml")


def translate_docx(
    input_docx_path: str,
    output_docx_path: str,
    target_language: str = "German",
    source_language: Optional[str] = None,
    tone: Optional[str] = None,
    domain: Optional[str] = None,
) -> None:
    """
    Translates a .docx file to German while preserving formatting.
    """
    # Create a temporary directory to work with the contents
    temp_dir = tempfile.mkdtemp()

    try:
        # Unzip the .docx file into the temporary directory
        with zipfile.ZipFile(input_docx_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # List of XML files to process
        xml_files = [
            "word/document.xml",
            # Add headers and footers if they exist
            *[
                f"word/{name}"
                for name in os.listdir(os.path.join(temp_dir, "word"))
                if name.startswith(("header", "footer")) and name.endswith(".xml")
            ],
        ]

        # Process each XML file
        for xml_file in xml_files:
            xml_path = os.path.join(temp_dir, xml_file)
            if os.path.exists(xml_path):
                process_xml(xml_path, target_language, source_language, tone, domain)

        # Rezip the contents into a new .docx file
        with zipfile.ZipFile(output_docx_path, "w", zipfile.ZIP_DEFLATED) as docx:
            for foldername, subfolders, filenames in os.walk(temp_dir):
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    # Get the path relative to the temporary directory
                    archive_name = os.path.relpath(file_path, temp_dir)
                    docx.write(file_path, archive_name)
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    input_files = [
        "data/input/Info ai Comuni via SEL_23.04.2024.docx",
        "data/input/2015 instruction_et_guide_chik_dengue_16_avril_2015.docx",
        "data/input/2024 Strasbourg_Priorisierung von Aufentshaltorten.docx",
    ]
    for input_file in input_files:
        output_docx = input_file.replace("input", "output/llm/v3")
        translate_docx(input_file, output_docx)
        print(f"Translation complete. Translated document saved as '{output_docx}'.")
