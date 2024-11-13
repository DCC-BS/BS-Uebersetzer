import os
import zipfile
import shutil
import tempfile

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


previous_translation = ""


def translate_text(text: str) -> str:
    """
    Translates text to German using the LLM.
    Ensures that XML tags within the text are preserved.
    """
    global previous_translation
    # Handle empty texts
    if not text.strip() or len(text.strip()) == 1:
        return text

    endswith_r = text.endswith("\r")

    base_prompt = """You are an expert translator with fluency in German, French, English and Italian languages. 
                        Translate the given text to German. 
                        Do not modify the meaning of the text. The text is formal. Use natural and idiomatic translations.
                        Do not add any explanations, notes or comments to your translation. 
                        Do not enclose the translation into tags.
                        Preserve \r and \n.
                        Do not translate street names, trade marks, names, urls, phone numbers or other things that are not logical to be translated.
                        The text to translate is enclosed in <source_text> </source_text>."""
    context_prompt = ""
    if previous_translation:
        context_prompt = f"""\nThe translated text generated befor this text is provided below enclosed in <context> </context>. \n\n
                        <context>{previous_translation}</context>\n\n"""
    prompt = f"{base_prompt} {context_prompt} Translate this source text without generating anything other than the translation. \n\n <source_text>{text}</source_text> \n Translation: "
    response = client.completions.create(
        model="llama3.1:70b",
        prompt=prompt,
        temperature=0,
    )
    translated_text = response.choices[0].text.strip()
    translated_text = translated_text.replace("ß", "ss")
    previous_translation = translated_text
    translated_text += "\r" if endswith_r else ""
    return translated_text


def get_run_properties(elem):
    """Get the formatting properties of a text run"""
    parent_run = elem.getparent()  # Get the parent 'w:r' element
    if parent_run is not None:
        props = parent_run.find(".//w:rPr", namespaces=namespaces)
        return ET.tostring(props) if props is not None else None
    return None


def process_xml(file_path):
    """
    Parses and translates text within an XML file while preserving the structure.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

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
                    current_elem.text = translate_text(combined_text)

                # Start new accumulation
                current_text = [elem.text]
                current_format = elem_format
                current_elem = elem

        # Handle the last group of text
        if current_text and current_elem is not None:
            combined_text = "".join(current_text)
            current_elem.text = translate_text(combined_text)

    # Write the modified XML back to file
    tree.write(file_path, xml_declaration=True, encoding="UTF-8", method="xml")


def translate_docx(input_docx_path, output_docx_path):
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
                process_xml(xml_path)

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
    