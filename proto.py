import docx
import re
from src.contextparser import Context, Contexts, ContextParser
from pypdf import PdfReader

def main():
    reader = PdfReader("resume.pdf")
    text = "\n".join([page.extract_text() for page in reader.pages])
    print(text)

if __name__ == '__main__':
    main()
