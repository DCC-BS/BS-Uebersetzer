import fitz

from translator.config import TranslationConfig
from translator.base_translator import BaseTranslator


class PdfTranslator(BaseTranslator):
    """Translator for PDF files"""

    # def translate_text(self, text: str, config: TranslationConfig) -> str:
    #     return text + " " + text[: int(0.2 * len(text))]

    def translate(
        self, input_path: str, output_path: str, translation_config: TranslationConfig
    ) -> None:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        translation_config.context = ""
        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                new_page = new_doc.new_page(
                    width=page.rect.width, height=page.rect.height
                )
                text_dict = page.get_text("dict")
                blocks = text_dict["blocks"]

                for block in blocks:
                    if block["type"] == 0:  # Text block
                        text_writer = fitz.TextWriter(new_page.rect)
                        
                        # Initialize position at block start
                        current_x = block["bbox"][0]
                        current_y = block["bbox"][1]
                        line_height = 0

                        for line in block["lines"]:
                            for span in line["spans"]:
                                # Original text properties
                                orig_text = span["text"]
                                font_name = span["font"]
                                font_size = span["size"]
                                font_color = span["color"]
                                font_flags = span["flags"]

                                # Update line height if this span is taller
                                line_height = max(line_height, font_size * 1.2)

                                if isinstance(font_color, int):
                                    r = ((font_color >> 16) & 0xFF) / 255
                                    g = ((font_color >> 8) & 0xFF) / 255
                                    b = (font_color & 0xFF) / 255
                                    font_color = (r, g, b)

                                translated_text = self.translate_text(orig_text, config=translation_config)
                                translation_config.context = self._create_translation_context(
                                    translation_config.context, translated_text
                                )
                                fallback_font = self._get_fallback_font(font_name, font_flags)

                                # Split text into words for better width handling
                                words = translated_text.split()
                                current_line = ""

                                for word in words:
                                    # Calculate width with current word
                                    test_line = current_line + (" " if current_line else "") + word
                                    text_width = fallback_font.text_length(test_line, fontsize=font_size)

                                    # Check if adding this word would exceed block width
                                    if current_x + text_width > block["bbox"][2]:
                                        # Write current line before starting new one
                                        if current_line:
                                            text_writer.color = font_color
                                            text_writer.append(
                                                pos=(current_x, current_y),
                                                text=current_line,
                                                font=fallback_font,
                                                fontsize=font_size,
                                            )
                                        
                                        # Move to next line
                                        current_x = block["bbox"][0]
                                        current_y += line_height
                                        current_line = word
                                    else:
                                        # Add word to current line
                                        current_line = test_line

                                # Write any remaining text
                                if current_line:
                                    text_writer.color = font_color
                                    text_writer.append(
                                        pos=(current_x, current_y),
                                        text=current_line,
                                        font=fallback_font,
                                        fontsize=font_size,
                                    )
                                    current_x += fitz.get_text_length(
                                        current_line,
                                        fontname=fallback_font.name,
                                        fontsize=font_size,
                                    ) + font_size * 0.2

                            # Move to next line after processing all spans in current line
                            current_x = block["bbox"][0]
                            current_y += line_height
                            line_height = 0

                        text_writer.write_text(new_page)
                    elif block["type"] == 1:  # Image block
                        new_page.insert_image(
                            rect=fitz.Rect(block["bbox"]), stream=block["image"]
                        )

            new_doc.save(output_path)
            print(f"Saved modified PDF to '{output_path}'.")
        finally:
            doc.close()
            new_doc.close()

    def _create_translation_context(
        self, current_context: str, new_translation: str, max_context_length: int = 1000
    ) -> str:
        """
        Creates a translation context by combining current context with new translation,
        respecting the maximum context length and maintaining sentence integrity.

        Args:
            current_context (str): Existing context string
            new_translation (str): New translation to be added
            max_context_length (int): Maximum allowed length of the combined context

        Returns:
            str: Updated context string within max length constraints
        """
        # Add space between contexts if needed
        separator = " " if current_context and new_translation else ""
        combined = current_context + separator + new_translation

        # If combined length is within limit, return the full context
        if len(combined) <= max_context_length:
            return combined

        # If new translation alone exceeds limit, truncate it from the start of a sentence
        if len(new_translation) > max_context_length:
            # Find the first sentence boundary after max_context_length characters from the end
            for punct in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                start_pos = new_translation[-max_context_length:].find(punct)
                if start_pos != -1:
                    return new_translation[-(max_context_length - start_pos - 2) :]
            return new_translation[
                -max_context_length:
            ]  # Fallback if no sentence boundary found

        # Otherwise, trim from the beginning while preserving complete sentences
        excess = len(combined) - max_context_length
        truncated = combined[excess:]

        # Find the start of the first complete sentence
        for punct in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
            start_pos = truncated.find(punct)
            if start_pos != -1:
                return truncated[start_pos + 2 :]

        return truncated  # Fallback if no sentence boundary found

    def _get_fallback_font(self, font_name: str, font_flags) -> fitz.Font:
        # Default fallback font family is Helvetica
        base_font = "helvetica"

        # Check if the original font has serif characteristics
        if "times" in font_name.lower() or font_flags & 1:  # serif flag is 1
            base_font = "times-roman"
        elif "courier" in font_name.lower() or font_flags & 32:  # mono flag is 32
            base_font = "courier"

        # Determine style variations
        is_bold = font_flags & 2 != 0  # bold flag is 2
        is_italic = font_flags & 4 != 0  # italic flag is 4

        # Construct the appropriate font name
        if is_bold and is_italic:
            if base_font == "times-roman":
                return fitz.Font("times", is_bold=1, is_italic=1)
            else:
                return fitz.Font(base_font, is_bold=1, is_italic=1)
        elif is_bold:
            return fitz.Font(base_font, is_bold=1)
        elif is_italic:
            if base_font == "times-roman":
                return fitz.Font("times", is_italic=1)
            else:
                return fitz.Font(base_font, is_italic=1)

        return fitz.Font(base_font)
