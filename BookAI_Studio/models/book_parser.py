import os
import re


class BookParser:

    def parse(self, file_path: str) -> dict:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self._parse_pdf(file_path)
        elif ext == ".epub":
            return self._parse_epub(file_path)
        elif ext in [".txt", ".md"]:
            return self._parse_txt(file_path)
        elif ext == ".docx":
            return self._parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")

    def _parse_pdf(self, path: str) -> dict:
        try:
            import fitz
            doc = fitz.open(path)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()
            chapters = self._split_into_chapters(full_text)
            return {
                "title": os.path.splitext(os.path.basename(path))[0],
                "full_text": full_text,
                "chapters": chapters,
                "word_count": len(full_text.split()),
            }
        except ImportError:
            raise ImportError("PyMuPDF not installed. Run: pip install PyMuPDF")

    def _parse_epub(self, path: str) -> dict:
        try:
            import ebooklib
            from ebooklib import epub
            from html.parser import HTMLParser

            class MLStripper(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.reset()
                    self.fed = []
                def handle_data(self, d):
                    self.fed.append(d)
                def get_data(self):
                    return " ".join(self.fed)

            def strip_tags(html):
                s = MLStripper()
                s.feed(html)
                return s.get_data()

            book = epub.read_epub(path)
            title = book.get_metadata("DC", "title")
            title = title[0][0] if title else os.path.splitext(os.path.basename(path))[0]

            chapters = []
            full_text = ""
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                content = item.get_content().decode("utf-8", errors="ignore")
                text = strip_tags(content).strip()
                if len(text) > 200:
                    chapters.append({"title": f"Chapter {len(chapters)+1}", "content": text})
                    full_text += text + "\n\n"

            return {
                "title": title,
                "full_text": full_text,
                "chapters": chapters,
                "word_count": len(full_text.split()),
            }
        except ImportError:
            raise ImportError("ebooklib not installed. Run: pip install ebooklib")

    def _parse_txt(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            full_text = f.read()
        chapters = self._split_into_chapters(full_text)
        return {
            "title": os.path.splitext(os.path.basename(path))[0],
            "full_text": full_text,
            "chapters": chapters,
            "word_count": len(full_text.split()),
        }

    def _parse_docx(self, path: str) -> dict:
        try:
            from docx import Document
            doc = Document(path)
            full_text = "\n".join([p.text for p in doc.paragraphs])
            chapters = self._split_into_chapters(full_text)
            return {
                "title": os.path.splitext(os.path.basename(path))[0],
                "full_text": full_text,
                "chapters": chapters,
                "word_count": len(full_text.split()),
            }
        except ImportError:
            raise ImportError("python-docx not installed. Run: pip install python-docx")

    def _split_into_chapters(self, text: str) -> list:
        patterns = [
            r"(?i)(chapter\s+\d+[^\n]*)\n",
            r"(?i)(chapter\s+[a-z]+[^\n]*)\n",
            r"\n\s*(\d+\.\s+[A-Z][^\n]+)\n",
        ]
        chapters = []
        for pattern in patterns:
            parts = re.split(pattern, text)
            if len(parts) > 3:
                for i in range(1, len(parts) - 1, 2):
                    title = parts[i].strip()
                    content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                    if len(content) > 100:
                        chapters.append({"title": title, "content": content})
                if chapters:
                    return chapters

        # fallback: split by word count chunks
        words = text.split()
        chunk_size = 2000
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chapters.append({"title": f"Section {len(chapters)+1}", "content": chunk})
        return chapters
