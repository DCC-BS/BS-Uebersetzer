import streamlit as st
import tempfile
import os
from xml_translate import translate_docx, translate_text
import iso639
import pyperclip
from pathlib import Path
import base64

TONE_MAPPING = {
    "Keiner": None,
    "Formell": "Formal",
    "Informell": "Informal",
    "Technisch": "Technical",
}

TONE_MAPPING_REVERSE = {v: k for k, v in TONE_MAPPING.items()}

DOMAIN_MAPPING = {
    "Keines": None,
    "Behörden": "Government",
    "Rechtswesen": "Legal",
    "Medizin": "Medical",
    "Technik": "Technical",
    "Finanzen": "Financial",
    "Wissenschaft": "Scientific",
    "Marketing": "Marketing",
    "Literatur": "Literary",
    "Bildung": "Educational",
    "Gastgewerbe und Tourismus": "Hospitality and Tourism",
    "Informationstechnologie": "Information Technology",
    "Landwirtschaft": "Agriculture",
    "Energie": "Energy",
    "Immobilien": "Real Estate",
    "Personalwesen": "Human Resources",
    "Pharmazie": "Pharmaceutical",
    "Kunst und Kultur": "Art and Culture",
    "Logistik und Transport": "Logistics and Transportation",
}

DOMAIN_MAPPING_REVERSE = {v: k for k, v in DOMAIN_MAPPING.items()}

LANGUAGE_MAPPING = {
    "Automatisch erkennen": "Auto-detect",
    "Englisch": "English",
    "Deutsch": "German",
    "Französisch": "French",
    "Italienisch": "Italian",
}

LANGUAGE_MAPPING_REVERSE = {v: k for k, v in LANGUAGE_MAPPING.items()}


def main():
    st.set_page_config(page_title="BS Übersetzer", page_icon="🌐", layout="wide")
    st.title("Basel Stadt Übersetzer")

    with st.expander("⚠️ Disclaimer", expanded=False):
        st.warning("""
        **Disclaimer / Haftungsausschluss**
        
        Diese Webanwendung verwendet interne Large Language Models (LLMs) zur Verarbeitung Ihrer Anfragen. Alle Daten werden innerhalb des Kantons Basel-Stadt gespeichert und verarbeitet.

        **Wichtiger Hinweis:** Diese Anwendung befindet sich im Proof-of-Concept (PoC) Stadium. Es wird keine Garantie für die Verfügbarkeit, Korrektheit oder Vollständigkeit der Ergebnisse übernommen. Die zugrundeliegende KI Plattform befindet sich im aktiven Aufbau, daher können die Antwortzeiten stark variieren.

        Bei Fehlern oder Problemen wenden Sie sich bitte an [Yanick Schraner](mailto:yanick.schraner@bs.ch).
        """)

    text_section()
    st.markdown("---")
    docx_section()
    footer()


def text_section():
    st.header("Text übersetzen")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.selectbox(
            "Ausgangssprache",
            ["Automatisch Erkennen", "German", "English", "French", "Italian"]
            + [lang["name"] for lang in iso639.data if lang["iso639_1"] != ""],
            index=0,
            key="source_lang",
        )

    with col2:
        st.selectbox(
            "Zielsprache",
            ["German", "English", "French", "Italian"]
            + [lang["name"] for lang in iso639.data if lang["iso639_1"] != ""],
            index=0,
            key="target_lang",
        )
    with col3:
        st.selectbox(
            "Tonalität (Optional)",
            list(TONE_MAPPING.keys()),
            index=0,
            key="tone",
            help="Wählen Sie den gewünschten Schreibstil für die Übersetzung:\n\n"
            + "• Keiner: Neutraler, sachlicher Stil\n\n"
            + "• Formell: Professioneller Stil für offizielle Dokumente\n\n"
            + "• Informell: Lockerer, persönlicher Konversationsstil\n\n"
            + "• Technisch: Fachspezifischer Stil mit Fachterminologie",
        )
    with col4:
        st.selectbox(
            "Fachgebiet (Optional)",
            list(DOMAIN_MAPPING.keys()),
            key="domain",
            index=0,
            help="Wählen Sie das passende Fachgebiet für Ihre Übersetzung. "
            + "Dies hilft dem System, die richtige Fachterminologie und "
            + "kontextspezifische Übersetzungen zu verwenden.",
        )

    # Create two columns for input and output text
    text_col1, text_col2 = st.columns(2)

    with text_col1:
        st.subheader("Ausgangstext")
        source_text = st.text_area("Text zum Übersetzen eingeben", height=200)

    with text_col2:
        st.subheader("Übersetzung")
        # Initialize translated_text in session state if it doesn't exist
        if "translated_text" not in st.session_state:
            st.session_state.translated_text = ""

        # Display translation text area
        st.text_area(
            "Übersetzung",
            value=st.session_state.translated_text,
            height=200,
            disabled=False,  # Make it read-only
        )

        if st.session_state.translated_text:
            if st.button("In Zwischenablage kopieren"):
                copy_to_clipboard(st.session_state.translated_text)

    if st.button("Übersetzen"):
        if source_text:
            with st.spinner("Übersetzung läuft..."):
                translated_text = translate_text(
                    source_text,
                    source_language=st.session_state.source_lang,
                    target_language=st.session_state.target_lang,
                    tone=TONE_MAPPING.get(st.session_state.tone),
                    domain=DOMAIN_MAPPING.get(st.session_state.domain),
                )
                st.session_state.translated_text = translated_text
                st.rerun()


def docx_section():
    # Document Translation Section
    st.header("Dokumentübersetzung")
    st.write("Optional können Sie ein Word-Dokument (.docx) zum Übersetzen hochladen")

    # Initialize session state for storing the translated document
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
                translate_docx(
                    input_path,
                    output_path,
                    source_language=st.session_state.source_lang,
                    target_language=st.session_state.target_lang,
                    tone=TONE_MAPPING.get(st.session_state.tone),
                    domain=DOMAIN_MAPPING.get(st.session_state.domain),
                )

            with open(output_path, "rb") as file:
                st.session_state.translated_doc = file.read()

        except Exception as e:
            st.error(f"Bei der Übersetzung ist ein Fehler aufgetreten: {str(e)}")

        finally:
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except Exception as e:
                pass

    if st.session_state.translated_doc is not None:
        st.download_button(
            label="Übersetzte Datei herunterladen",
            data=st.session_state.translated_doc,
            file_name=f"translated_{st.session_state.original_filename}",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
            </div>
            """,
            unsafe_allow_html=True,
        )


def get_language_dict():
    keys = [lang["name"] for lang in iso639.data if lang["iso639_1"] != ""]
    values = [lang["name"] for lang in iso639.data if lang["iso639_1"] != ""]
    return dict(zip(keys, values))


def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        st.success("Text wurde in die Zwischenablage kopiert!")
    except Exception as e:
        st.error(f"Fehler beim Kopieren: {str(e)}")


if __name__ == "__main__":
    main()
