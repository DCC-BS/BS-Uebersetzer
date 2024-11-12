from typing import List
import spacy
import logging
from langdetect import detect, LangDetectException


logger = logging.getLogger(__name__)

def detect_language(text):
    """Detect the language of the text."""
    try:
        return detect(text)
    except LangDetectException:
        print(text)

def _language_to_spacy_model(language_code: str) -> str:
    """Return the appropriate spacy model for the given language code."""
    if language_code == 'de':
        return "de_core_news_sm"
    elif language_code == "fr":
        return "fr_core_news_sm"
    elif language_code == "it":
        return "it_core_news_sm"
    return "en_core_web_sm"


def load_spacy_model(model_name="en_core_web_sm"):
    """
    Load the appropriate spaCy model, downloading if necessary.
    
    Args:
        model_name (str): Name of the spaCy model to load (default: en_core_web_sm)
    
    Returns:
        spacy.language.Language: Loaded spaCy model
    """
    try:
        nlp = spacy.load(model_name)
        logger.info(f"Loaded existing spaCy model: {model_name}")
    except OSError:
        logger.info(f"Downloading spaCy model: {model_name}")
        spacy.cli.download(model_name)
        nlp = spacy.load(model_name)
    
    # nlp.disable_pipes(*[pipe for pipe in nlp.pipe_names if pipe != "senter"])
    
    return nlp

def split_into_sentences(text: str, language_model: str=None) -> List[str]:
    """
    Split text into sentences using spaCy.
    
    Args:
        text (str): Text to split into sentences
        language_model (str): Name of the spaCy language model to use
    
    Returns:
        list: List of sentences
    """
    logger.info(f"Splitting text of length {len(text)} into sentences")
    if not language_model:
        language = detect_language(text)
        language_model = _language_to_spacy_model(language)
    nlp = load_spacy_model(language_model)
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    
    logger.info(f"Split into {len(sentences)} sentences")
    return sentences
