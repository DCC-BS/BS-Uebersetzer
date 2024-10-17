import openai
import logging
from tqdm import tqdm
import os
import httpx
import contextlib
from contextvars import ContextVar


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

def split_into_chunks(text, max_length=5000, overlap=200):
    """Split text into chunks based on string length with overlap."""
    logger.info(f"Splitting text of length {len(text)} into chunks (max_length={max_length}, overlap={overlap})")
    chunks = []
    start = 0
    with tqdm(total=len(text), desc="Splitting into chunks", disable=tqdm_disabled.get()):
        while start < len(text):
            end = start + max_length
            if end >= len(text):
                chunks.append(text[start:])
                start = len(text) + 1
            else:
                last_period = find_last_period(text, start, end, overlap)
                chunks.append(text[start:last_period])
                start = last_period
    logger.info(f"Split into {len(chunks)} chunks")
    return chunks

def find_last_period(text, start, end, overlap):
    """Find the last period within the overlap region."""
    overlap_start = max(start, end - overlap)
    overlap_end = min(end + overlap, len(text))
    for i in range(overlap_end - 1, overlap_start - 1, -1):
        if text[i] == '.':
            return i + 1
    return overlap_end

def find_context_start(text, end, overlap):
    """Find the start of the context, beginning from a period."""
    start = max(0, end - overlap)
    for i in range(end - overlap, 0, -1):
        if text[i] == '.':
            return i + 1
    return start

def translate_chunk(chunk_text, target_language, context="", llm='gpt-4o-mini'):
    """Translate a single chunk of text."""
    if "pappai01" in os.getenv("BASE_URL"):
        client = openai.OpenAI(base_url=os.getenv("BASE_URL"))
    else:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=httpx.Client(proxy=os.getenv("PROXY_URL")), base_url=os.getenv("BASE_URL"))

    prompt = f"{context}Translate the following content of the XML from a Word document and keep the formatting to {target_language}: {chunk_text}"

    print(prompt)
    
    try:
        logger.debug(f"Sending translation request for chunk of length {len(chunk_text)}")
        response = client.chat.completions.create(
            model=llm,
            messages=[
                {"role": "system", "content": f"You are an expert translator with fluency in German, French, English and Italian languages. Translate the following content of the XML from a Word document and keep the formatting to {target_language}. For German output use Swiss German writing, i.e. use ss instead of ß. Do not use mark down formating. Do not modify the meaning of the text. Do not leave out parts of the text. Every sentence needs to be translated."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        translated_text = response.choices[0].message.content.strip()
        logger.debug(f"Received translation of length {len(translated_text)}")
        return translated_text
    except openai.OpenAIError as e:
        logger.error(f"An error occurred while translating: {e}")
        return None
    
def translate_chunks(chunks, target_language, llm, overlap):
    """Translate all chunks and maintain context between them."""
    translated_chunks = []
    logger.info(f"Translating {len(chunks)} chunks to {target_language}")
    with tqdm(total=len(chunks), desc="Translating chunks", disable=tqdm_disabled.get()) as pbar:
        for i, chunk in enumerate(chunks):
            context = ""
            if i > 0:
                context_start = find_context_start(translated_chunks[-1], len(translated_chunks[-1]), overlap)
                context = f"Previous translated text as context: {translated_chunks[-1][context_start:]}\n\n"
            
            translated_chunk = translate_chunk(chunk, target_language, context, llm)
            if translated_chunk:
                translated_chunks.append(translated_chunk)
                pbar.update(1)
            else:
                logger.error(f"Translation failed for chunk {i}")
                return None
    return translated_chunks

def chunk_and_translate(text, target_language, max_length=5000, overlap=200, llm="gpt-4o-mini"):
    """Main function to chunk, translate, and combine text."""
    logger.info(f"Starting translation process for text of length {len(text)} to {target_language}")
    chunks = split_into_chunks(text, max_length, overlap)
    translated_chunks = translate_chunks(chunks, target_language, llm, overlap)
    if translated_chunks:
        final_translation = combine_translations(translated_chunks)
        logger.info(f"Translation completed. Final length: {len(final_translation)}")
        return final_translation
    logger.error("Translation process failed")
    return None

def combine_translations(translated_chunks):
    """Combine translated chunks into a single text."""
    logger.info(f"Combining {len(translated_chunks)} translated chunks")
    final_translation = " ".join(translated_chunks)
    if len(final_translation) == 0:
        raise ValueError("Produced an empty translation.")
    return final_translation