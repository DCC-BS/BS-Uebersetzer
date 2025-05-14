import base64
import os
import tempfile
from pathlib import Path
from urllib.parse import quote, unquote

import pyperclip
import streamlit as st
import streamlit.components.v1 as components
from streamlit_theme import st_theme

from translator import DocxTranslator, TextTranslator, TranslationConfig
from translator.utils import (
    DOMAIN_MAPPING,
    LANGUAGE_MAPPING,
    TONE_MAPPING,
    is_rtl_language,
)

# Create singleton instances of translators
text_translator = TextTranslator()
docx_translator = DocxTranslator()


def main():
    st.set_page_config(page_title="BS-Übersetzer", page_icon="🌐", layout="wide")
    st.title("BS-Übersetzer")
    show_disclaimer()

    config = create_translation_config()

    text_section(config)
    st.markdown("---")
    document_section(config)
    footer()


def show_disclaimer():
    with st.expander("⚠️ Disclaimer", expanded=False):
        st.warning("""
        **Disclaimer / Haftungsausschluss**
        
        Diese Webanwendung verwendet interne Large Language Models (LLMs) zur Verarbeitung Ihrer Anfragen. 
        Alle Daten werden innerhalb des Kantons Basel-Stadt gespeichert und verarbeitet.

        **Wichtiger Hinweis:** Diese Anwendung befindet sich im Proof-of-Concept (PoC) Stadium. 
        Es wird keine Garantie für die Verfügbarkeit, Korrektheit oder Vollständigkeit der Ergebnisse übernommen. 
        Die zugrundeliegende KI Plattform befindet sich im aktiven Aufbau, daher können die Antwortzeiten stark variieren.

        Bei Fehlern oder Problemen wenden Sie sich bitte an [Yanick Schraner](mailto:yanick.schraner@bs.ch).
        """)


def text_section(config: TranslationConfig):
    st.header("Text übersetzen")

    # Use the global text_translator instance
    global text_translator

    # Create two columns for input and output text
    text_col1, text_col2 = st.columns(2)

    with text_col1:
        st.subheader("Ausgangstext")
        source_text = st.text_area("Text zum übersetzen eingeben", height=200)

    with text_col2:
        st.subheader("Übersetzung")
        is_rtl = False
        if "translated_text" not in st.session_state:
            st.session_state.translated_text = ""
        else:
            is_rtl = is_rtl_language(st.session_state.translated_text)

        create_text_component(st.session_state.translated_text, is_rtl)

        if st.session_state.translated_text:
            if st.button("In Zwischenablage kopieren"):
                copy_to_clipboard(st.session_state.translated_text)

    if st.button("Übersetzen"):
        if source_text:
            with st.spinner("Übersetzung läuft..."):
                st.session_state.translated_text = text_translator.translate_text(
                    source_text, config
                )
                st.rerun()


def document_section(config: TranslationConfig):
    st.header("Dokumentübersetzung")
    st.write("Optional können Sie ein Word-Dokument (.docx) zum übersetzen hochladen")

    # Initialize session state
    if "translated_doc" not in st.session_state:
        st.session_state.translated_doc = None
        st.session_state.original_filename = None

    # File uploader
    uploaded_file = st.file_uploader("DOCX-Datei auswählen", type=["docx"])

    if uploaded_file is not None and (
        st.session_state.original_filename != uploaded_file.name
    ):
        st.session_state.translated_doc = None
        st.session_state.original_filename = uploaded_file.name
        suffix = uploaded_file.name.split(".")[-1]

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{suffix}"
        ) as tmp_input:
            tmp_input.write(uploaded_file.getvalue())
            input_path = tmp_input.name

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{suffix}"
        ) as tmp_output:
            output_path = tmp_output.name

        try:
            with st.spinner("Übersetzung läuft..."):
                # Use the global docx_translator instance
                global docx_translator
                if suffix == "docx":
                    docx_translator.translate(input_path, output_path, config)

            with open(output_path, "rb") as file:
                st.session_state.translated_doc = file.read()

        except Exception as e:
            st.error(f"Bei der Übersetzung ist ein Fehler aufgetreten: {str(e)}")
            raise e
        finally:
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except Exception:
                pass

    if st.session_state.translated_doc is not None:
        mime = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if st.session_state.original_filename
            and st.session_state.original_filename.endswith("docx")
            else "application/pdf"
        )
        st.download_button(
            label="Übersetzte Datei herunterladen",
            data=st.session_state.translated_doc,
            file_name=f"translated_{st.session_state.original_filename}",
            mime=mime,
        )


def create_translation_config():
    """Creates and returns a TranslationConfig object based on user input"""
    # Handle parameters in url
    query_params = st.query_params

    url_source = None
    if "source" in query_params:
        url_source = query_params.get("source")
        if isinstance(url_source, list) and url_source:
            url_source = url_source[0]

    source_index = 0
    if url_source:
        url_source = url_source.capitalize()
        try:
            source_index = list(LANGUAGE_MAPPING.values()).index(url_source)
        except ValueError:
            pass

    url_target = None
    if "target" in query_params:
        url_target = query_params.get("target")
        if isinstance(url_target, list) and url_target:
            url_target = url_target[0]

    target_index = 0
    if url_target:
        url_target = url_target.capitalize()
        try:
            target_index = list(LANGUAGE_MAPPING.values())[1:].index(url_target)
        except ValueError:
            pass

    url_tone = None
    if "tonality" in query_params:
        url_tone = query_params.get("tonality")
        if isinstance(url_tone, list) and url_tone:
            url_tone = url_tone[0]

    tone_index = 0
    if url_tone:
        url_tone = url_tone.capitalize()
        try:
            tone_index = list(TONE_MAPPING.values()).index(url_tone)
        except ValueError:
            pass

    url_domain = None
    if "domain" in query_params:
        url_domain = query_params.get("domain")
        if isinstance(url_domain, list) and url_domain:
            url_domain = url_domain[0]

    domain_index = 0
    if url_domain:
        url_domain = url_domain.lower()
        try:
            domain_index = [
                domain.lower() for domain in DOMAIN_MAPPING.values() if domain
            ].index(url_domain)
            # Filter out "Keine" domain, therefore add index + 1
            domain_index += 1
        except ValueError:
            pass

    url_glossary = None
    if "glossary" in query_params:
        url_glossary = query_params.get("glossary")
        if isinstance(url_glossary, list) and url_glossary:
            url_glossary = url_glossary[0]

    glossary_default = ""
    if url_glossary:
        glossary_default = unquote(url_glossary)

    # Configure translation settings
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        source_lang = st.selectbox(
            "Ausgangssprache",
            list(LANGUAGE_MAPPING.keys()),
            index=source_index,
            key="source_lang",
            on_change=update_url_params,
        )

    with col2:
        target_lang = st.selectbox(
            "Zielsprache",
            list(LANGUAGE_MAPPING.keys())[1:],
            index=target_index,
            key="target_lang",
            on_change=update_url_params,
        )

    with col3:
        tone = st.selectbox(
            "Tonalität (Optional)",
            list(TONE_MAPPING.keys()),
            index=tone_index,
            key="tone",
            help="Wählen Sie den gewünschten Schreibstil für die Übersetzung",
            on_change=update_url_params,
        )

    with col4:
        domain = st.selectbox(
            "Fachgebiet (Optional)",
            list(DOMAIN_MAPPING.keys()),
            key="domain",
            index=domain_index,
            help="Wählen Sie das passende Fachgebiet für Ihre Übersetzung",
            on_change=update_url_params,
        )

    with col5:
        glossary = st.text_input(
            "Glossar (Optional)",
            value=glossary_default,
            placeholder="Begriff1:Beschreibung1;Begriff2:Beschreibung2",
            key="glossary",
            help="Geben Sie ein benutzerdefiniertes Glossar an",
            on_change=update_url_params,
        )

    # Create a TranslationConfig with non-None values
    source_language = LANGUAGE_MAPPING.get(source_lang, "")
    target_language = LANGUAGE_MAPPING.get(target_lang, "")
    tone_value = TONE_MAPPING.get(tone)
    domain_value = DOMAIN_MAPPING.get(domain)

    return TranslationConfig(
        target_language=target_language,
        source_language=source_language,
        tone=tone_value,
        domain=domain_value,
        glossary=glossary,
    )


def footer():
    st.markdown("<br>" * 2, unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        current_dir = Path(__file__).parent
        logo_path = current_dir / "assets" / "logo.png"
        st.markdown(
            f"""
            <div style='text-align: center;'>
                <a href="https://www.bs.ch/schwerpunkte/daten-und-statistiken/databs/schwerpunkte/datenwissenschaften-und-ki" target="_blank">
                    <img src="data:image/png;base64,{base64.b64encode(open(logo_path, 'rb').read()).decode()}" width="100">
                </a>
                <p style='margin-top: 10px;'>Datenwissenschaften und KI</p>
                <p>Developed with ❤️ by Data Alchemy Team</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        st.success("Text wurde in die Zwischenablage kopiert!")
    except Exception as e:
        st.error(f"Fehler beim Kopieren: {str(e)}")


def create_text_component(text, is_rtl=False, height=200):
    theme = "dark" if st.get_option("theme.base") == "dark" else "light"
    text_color = "#FFFFFF" if theme == "dark" else "#31333f"
    bg_color = "#262730" if theme == "dark" else "#f0f2f6"
    theme = st_theme()
    try:
        bg_color = theme["secondaryBackgroundColor"]
        text_color = theme["textColor"]
    except Exception:
        pass

    direction = "rtl" if is_rtl else "ltr"
    text_align = "right" if is_rtl else "left"

    html = f"""
    <style>
    label {{
    display: block;
    margin-bottom: 5px;
    font-size: 14px;
    color: {text_color};
    font-family: "Source Sans Pro", sans-serif; 
    }}
    textarea {{
        width: 100%;
        padding: 16px;
        border: 1px solid #ccc;
        border-radius: 5px; 
        box-sizing: border-box; 
        resize: vertical;
        font-family: "Source Sans Pro", sans-serif;
        background-color: {bg_color};
        border-color: {bg_color};
        overflow-y: auto;
        color: {text_color};
        caret-color: {text_color};
        font-size: 16px;
        height: {height}px;
        direction: {direction}; 
        text-align: {text_align};
    }}
</style>
    <label for="translatedText">Übersetzung:</label>
    <textarea id="translatedText" inputmode="text" rows="3">{text}</textarea>
"""
    components.html(html, height=height + 30)


def update_url_params():
    """Update URL parameters based on current selection"""
    # Create a dictionary to store all potential parameters
    all_params = {
        "source": LANGUAGE_MAPPING.get(st.session_state.source_lang),
        "target": LANGUAGE_MAPPING.get(st.session_state.target_lang),
        "tonality": TONE_MAPPING.get(st.session_state.tone),
        "domain": DOMAIN_MAPPING.get(st.session_state.domain),
        "glossary": st.session_state.glossary,
    }

    params = {}

    for key in ["source", "target", "tonality", "domain", "glossary"]:
        if all_params[key]:
            # Skip default values
            if (
                (
                    key == "tonality"
                    and all_params[key] == list(TONE_MAPPING.values())[0]
                )
                or (
                    key == "domain"
                    and all_params[key] == list(DOMAIN_MAPPING.values())[0]
                )
                or (key == "glossary" and not all_params[key].strip())
            ):
                continue

            if key == "glossary":
                params[key] = quote(str(all_params[key]))
            else:
                params[key] = str(all_params[key]).lower()

    # Clear all parameters and set new ones
    st.query_params.clear()
    if params:
        st.query_params.update(params)


if __name__ == "__main__":
    main()
