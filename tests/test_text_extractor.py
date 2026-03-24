from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_compliance.core.parsers.text_extractor import extract_text


class TextExtractorTests(unittest.TestCase):
    def test_extract_text_uses_pdf_specific_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\n")
            with (
                patch("agent_compliance.core.parsers.text_extractor._extract_with_pypdf", return_value="这是一段足够长的 PDF 正文文本，用于验证专门解析链路。"),
                patch("agent_compliance.core.parsers.text_extractor._extract_with_pdfplumber") as plumber,
                patch("agent_compliance.core.parsers.text_extractor._extract_with_textutil") as textutil,
            ):
                text = extract_text(source)
        self.assertIn("PDF 正文文本", text)
        plumber.assert_not_called()
        textutil.assert_not_called()

    def test_extract_text_falls_back_to_pdfplumber_when_pypdf_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\n")
            with (
                patch("agent_compliance.core.parsers.text_extractor._extract_with_pypdf", return_value=""),
                patch("agent_compliance.core.parsers.text_extractor._extract_with_pdfplumber", return_value="pdfplumber 成功提取到更完整的正文内容。") as plumber,
                patch("agent_compliance.core.parsers.text_extractor._extract_with_textutil") as textutil,
            ):
                text = extract_text(source)
        self.assertIn("pdfplumber", text)
        plumber.assert_called_once()
        textutil.assert_not_called()

    def test_extract_text_falls_back_to_textutil_when_no_pdf_parser_returns_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\n")
            with (
                patch("agent_compliance.core.parsers.text_extractor._extract_with_pypdf", return_value=""),
                patch("agent_compliance.core.parsers.text_extractor._extract_with_pdfplumber", return_value=""),
                patch("agent_compliance.core.parsers.text_extractor._extract_with_textutil", return_value="textutil 兜底文本。") as textutil,
            ):
                text = extract_text(source)
        self.assertEqual(text, "textutil 兜底文本。")
        textutil.assert_called_once()


if __name__ == "__main__":
    unittest.main()
