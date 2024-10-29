from file_utils import copy_to_output_directory
from llm_translate import translate_document
from document_cleaner import DocumentCleaner
from dotenv import load_dotenv

load_dotenv()

def main(input_file: str):
    llm = 'llama3.1:70b'
    output_file = copy_to_output_directory(input_file)
    translate_document(input_file, output_file, target_language="German", llm=llm, max_length=4_000, overlap=400)
    # eval_translation('data/eval/de-fr.txt/EMEA.de-fr.fr', "German", llm, 'data/eval/de-fr.txt/EMEA.de-fr.de-gpt4o-mini')

if __name__ == '__main__':
    input_files = [
        '/home/jovyan/projects/translator/data/input/Info ai Comuni via SEL_23.04.docx'
                   ]
    for input_file in input_files:
        main(input_file)
