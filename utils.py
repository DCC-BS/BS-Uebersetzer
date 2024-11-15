from langdetect import detect, LangDetectException

def detect_language(text):
    """Detect the language of the text."""
    try:
        return detect(text)
    except LangDetectException:
        print(text)
