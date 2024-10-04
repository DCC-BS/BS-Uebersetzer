from file_utils import load_content, generate_comparison_output
from llm_translate import chunk_and_translate
from dotenv import load_dotenv

load_dotenv()

def main(input_file: str):
    original_text = load_content(input_file)
    llm = 'gpt-4o-mini'
    translated_text = chunk_and_translate(original_text, target_language="German", llm=llm)
    if translated_text:
        print(f"Original length: {len(original_text)}")
        print(f"Translated length: {len(translated_text)}")
        print(f"Translated text: {translated_text[:100]}...")
    else:
        print("Translation failed.")
    output_file = input_file.replace('input', 'output')
    generate_comparison_output(original_text, translated_text, output_file, translation_method=llm)

if __name__ == '__main__':
    input_file = 'data/input/Info ai Comuni via SEL_23.04.2024.pdf'
    main(input_file)