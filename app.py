import streamlit as st
import tempfile
import os
from xml_translate import translate_docx

def main():
    st.title("Document Translator")
    st.write("Upload a Word document (.docx) to translate it to German")

    if 'translated_doc' not in st.session_state:
        st.session_state.translated_doc = None
        st.session_state.original_filename = None

    uploaded_file = st.file_uploader("Choose a DOCX file", type="docx")

    if uploaded_file is not None and (st.session_state.original_filename != uploaded_file.name):
        # Reset translated doc if a new file is uploaded
        st.session_state.translated_doc = None
        st.session_state.original_filename = uploaded_file.name

        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_input:
            tmp_input.write(uploaded_file.getvalue())
            input_path = tmp_input.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_output:
            output_path = tmp_output.name


        try:
            with st.spinner('Translating document...'):
                translate_docx(input_path, output_path)

            with open(output_path, 'rb') as file:
                st.session_state.translated_doc = file.read()

        except Exception as e:
            st.error(f"An error occurred during translation: {str(e)}")

        finally:
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except:
                pass

    # Show download button if we have a translated document
    if st.session_state.translated_doc is not None:
        st.download_button(
            label="Download translated document",
            data=st.session_state.translated_doc,
            file_name=f"translated_{st.session_state.original_filename}",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    st.markdown("""
    ### Instructions:
    1. Upload a Word document (.docx format)
    2. Wait for the translation to complete
    3. Download the translated document using the button that appears
    
    **Note:** Documents are processed securely and are not stored permanently.
    """)

if __name__ == "__main__":
    main()