from langdetect import detect, LangDetectException


def detect_language(text: str) -> str:
    """Detect the language of the text. 
    If it is not possible to detect the language, 
    return an empty string and let the llm handle the problem itself."""
    try:
        return detect(text)
    except LangDetectException:
        return ""
