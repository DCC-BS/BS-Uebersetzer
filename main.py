from file_utils import load_content, generate_comparison_output, extract_xml_from_docx
from llm_translate import chunk_and_translate
from document_cleaner import DocumentCleaner
from dotenv import load_dotenv

load_dotenv()

def main(input_file: str):
    xml_content = extract_xml_from_docx(input_file, 'word/document.xml')
    llm = 'llama3.1:70b'
    translated_text = chunk_and_translate(xml_content, target_language="German", llm=llm, max_length=1_500, overlap=400)
    if translated_text:
        print(f"Original length: {len(xml_content)}")
        print(f"Translated length: {len(translated_text)}")
        print(f"Translated text: {translated_text[:100]}...")
    else:
        print("Translation failed.")
    output_file = input_file.replace('input', 'output')
    generate_comparison_output(xml_content, translated_text, output_file, translation_method=llm)

    # eval_translation('data/eval/de-fr.txt/EMEA.de-fr.fr', "German", llm, 'data/eval/de-fr.txt/EMEA.de-fr.de-gpt4o-mini')

if __name__ == '__main__':
    input_files = [
        'data/input/Info ai Comuni via SEL_23.04.2024.zip',
        'data/input/2015 instruction_et_guide_chik_dengue_16_avril_2015.zip',
        'data/input/2024 Strasbourg_Priorisierung von Aufentshaltorten.zip'
                   ]
    for input_file in input_files:
        main(input_file)
