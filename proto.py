import docx
import re
from pypdf import PdfReader
from urllib.request import urlopen
from langchain_community.document_transformers import Html2TextTransformer
from langchain_community.document_loaders import AsyncHtmlLoader

def main():
    url = "https://jobs.fidelity.com/job-details/21056911/associate-data-scientist/"
    urls = [url]
    loader = AsyncHtmlLoader(urls)
    docs = loader.load()
    html2text = Html2TextTransformer()
    docs_transformed = html2text.transform_documents(docs)

    print(docs_transformed)
    print(docs_transformed[0].page_content)


if __name__ == '__main__':
    main()
