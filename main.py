from file_utils import load_content, generate_comparison_output
from llm_translate import chunk_and_translate
from document_cleaner import DocumentCleaner
from dotenv import load_dotenv

load_dotenv()

def main(input_file: str):
    original_text = load_content(input_file)
    doc_cleaner = DocumentCleaner(remove_empty_lines=False)
    # original_text = doc_cleaner.run(original_text)
    llm = 'llama3.1:70b'
    translated_text = chunk_and_translate(original_text, target_language="German", llm=llm, max_length=1_500, overlap=400)
    if translated_text:
        print(f"Original length: {len(original_text)}")
        print(f"Translated length: {len(translated_text)}")
        print(f"Translated text: {translated_text[:100]}...")
    else:
        print("Translation failed.")
    output_file = input_file.replace('input', 'output')
    generate_comparison_output(original_text, translated_text, output_file, translation_method=llm)

    # eval_translation('data/eval/de-fr.txt/EMEA.de-fr.fr', "German", llm, 'data/eval/de-fr.txt/EMEA.de-fr.de-gpt4o-mini')

if __name__ == '__main__':
    input_files = [
        'data/input/Info ai Comuni via SEL_23.04.2024.pdf',
        'data/input/2015 instruction_et_guide_chik_dengue_16_avril_2015.pdf',
        'data/input/2024 Strasbourg_Priorisierung von Aufentshaltorten.pdf'
                   ]
    for input_file in input_files:
        main(input_file)