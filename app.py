import streamlit as st
import tempfile
import os
from translator.utils import (
    DOMAIN_MAPPING,
    LANGUAGE_MAPPING,
    TONE_MAPPING,
    is_rtl_language,
)
from translator import TextTranslator, DocxTranslator, TranslationConfig
import pyperclip
from pathlib import Path
import base64
import streamlit.components.v1 as components
from streamlit_theme import st_theme


def main():
    st.set_page_config(page_title="BS Übersetzer", page_icon="🌐", layout="wide")
    st.title("Basel Stadt Übersetzer")
    show_disclaimer()

    config = create_translation_config()

    text_section(config)
    st.markdown("---")
    docx_section(config)
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

    translator = TextTranslator()

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
                st.session_state.translated_text = translator.translate_text(
                    source_text, config
                )
                st.rerun()


def docx_section(config: TranslationConfig):
    st.header("Dokumentübersetzung")
    st.write("Optional können Sie ein Word-Dokument (.docx) zum übersetzen hochladen")

    translator = DocxTranslator()

    # Initialize session state
    if "translated_doc" not in st.session_state:
        st.session_state.translated_doc = None
        st.session_state.original_filename = None

    # File uploader
    uploaded_file = st.file_uploader("DOCX-Datei auswählen", type="docx")

    if uploaded_file is not None and (
        st.session_state.original_filename != uploaded_file.name
    ):
        st.session_state.translated_doc = None
        st.session_state.original_filename = uploaded_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_input:
            tmp_input.write(uploaded_file.getvalue())
            input_path = tmp_input.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_output:
            output_path = tmp_output.name

        try:
            with st.spinner("Übersetzung läuft..."):
                translator.translate(input_path, output_path, config)

            with open(output_path, "rb") as file:
                st.session_state.translated_doc = file.read()

        except Exception as e:
            st.error(f"Bei der Übersetzung ist ein Fehler aufgetreten: {str(e)}")

        finally:
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except Exception:
                pass

    if st.session_state.translated_doc is not None:
        st.download_button(
            label="Übersetzte Datei herunterladen",
            data=st.session_state.translated_doc,
            file_name=f"translated_{st.session_state.original_filename}",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


def create_translation_config():
    """Creates and returns a TranslationConfig object based on user input"""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        source_lang = st.selectbox(
            "Ausgangssprache",
            list(LANGUAGE_MAPPING.keys()),
            index=0,
            key="source_lang",
        )

    with col2:
        target_lang = st.selectbox(
            "Zielsprache",
            list(LANGUAGE_MAPPING.keys())[1:],
            index=0,
            key="target_lang",
        )

    with col3:
        tone = st.selectbox(
            "Tonalität (Optional)",
            list(TONE_MAPPING.keys()),
            index=0,
            key="tone",
            help="Wählen Sie den gewünschten Schreibstil für die Übersetzung",
        )

    with col4:
        domain = st.selectbox(
            "Fachgebiet (Optional)",
            list(DOMAIN_MAPPING.keys()),
            key="domain",
            index=0,
            help="Wählen Sie das passende Fachgebiet für Ihre Übersetzung",
        )

    with col5:
        glossary = st.text_input(
            "Glossar (Optional)",
            placeholder="Begriff1:Beschreibung1;Begriff2:Beschreibung2",
            key="glossary",
            help="Geben Sie ein benutzerdefiniertes Glossar an",
        )

    return TranslationConfig(
        target_language=LANGUAGE_MAPPING.get(target_lang),
        source_language=LANGUAGE_MAPPING.get(source_lang),
        tone=TONE_MAPPING.get(tone),
        domain=DOMAIN_MAPPING.get(domain),
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
                <p>Developped with ❤️ by Data Alchemy Team</p>
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


if __name__ == "__main__":
    main()
