import os
import zipfile
import shutil
import tempfile
import xml.etree.ElementTree as ET
import openai


client = openai.OpenAI(api_key="ABC", base_url=os.environ.get("BASE_URL"))
# Namespaces used in Word XML
namespaces = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'v': 'urn:schemas-microsoft-com:vml'
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
    if not text.strip():
        return text
    
    endswith_r = text.endswith("\r")

    prompt = f"""You are an expert translator with fluency in German, French, English and Italian languages. 
                    Translate the given text to German. 
                    Do not modify the meaning of the text. The text is formal. Use natural and idiomatic translations.
                    Do not add any explanations or comments to your translation. Preserve any XML tags or markup within the text.
                    For context, this is the translated text written befor the new one. \n\n
                    Context: {previous_translation}\n\n
                    Translate this text:\n\n{text.strip()}"""

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

def process_xml(file_path):
    """
    Parses and translates text within an XML file while preserving the structure.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Iterate over all text elements in the XML
    for elem in root.iter():
        if elem.tag.endswith('}t'):  # Text nodes in Word XML
            if elem.text and elem.text.strip():
                original_text = elem.text
                translated_text = translate_text(original_text)
                elem.text = translated_text

    # Write the modified XML back to file
    tree.write(file_path, xml_declaration=True, encoding='UTF-8', method="xml")

def translate_docx(input_docx_path, output_docx_path):
    """
    Translates a .docx file to German while preserving formatting.
    """
    # Create a temporary directory to work with the contents
    temp_dir = tempfile.mkdtemp()

    try:
        # Unzip the .docx file into the temporary directory
        with zipfile.ZipFile(input_docx_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # List of XML files to process
        xml_files = [
            'word/document.xml',
            # Add headers and footers if they exist
            *[f'word/{name}' for name in os.listdir(os.path.join(temp_dir, 'word')) if name.startswith(('header', 'footer')) and name.endswith('.xml')]
        ]

        # Process each XML file
        for xml_file in xml_files:
            xml_path = os.path.join(temp_dir, xml_file)
            if os.path.exists(xml_path):
                process_xml(xml_path)

        # Rezip the contents into a new .docx file
        with zipfile.ZipFile(output_docx_path, 'w', zipfile.ZIP_DEFLATED) as docx:
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
    input_docx = "data/input/Info ai Comuni via SEL_23.04.2024.docx"
    output_docx = "data/output/llm/v3/Info ai Comuni via SEL_23.04.2024.docx"

    # Translate the document
    translate_docx(input_docx, output_docx)
    print(f"Translation complete. Translated document saved as '{output_docx}'.")