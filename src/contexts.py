import re
import docx 
from pypdf import PdfReader
from urllib.request import urlopen
from langchain_community.document_transformers import Html2TextTransformer
from langchain_community.document_loaders import AsyncHtmlLoader
import concurrent

# Is this class really necessary?
class Contexts:
    def __init__(self, contextf, delim = ","):
        with open(contextf, "r") as f:
            parsed_lines = [[item.strip().replace("\n", "") for item in list(line.split(delim))] for line in f.readlines()]
        if len(parsed_lines) == 0 or len(parsed_lines[0]) != 2:
            raise ValueError("Format of contextf incorrect. Structure should be DESCRIPTION DELIM PATH")
        # TODO: eventually multi-thread parsing
        self.contexts = []
        def init_context(dp_tup):
            print(f"Processing Context: {dp_tup[0]}, {dp_tup[1]}")
            return Context(dp_tup[0], dp_tup[1])

        with concurrent.futures.ThreadPoolExecutor(max_workers = 5) as executor:
            for context in executor.map(init_context, parsed_lines):
                self.contexts.append(context)

    
    def __str__(self):
        return str([str(context) for context in self.contexts])

    def to_dict(self):
        return {contexts: [context.to_dict() for context in self.contexts]}
        
# NOTE: maybe I want to extend this design to allow any generic type of parser
class ContextParser:
    def __init__(self, ftype):
        supported_ftypes = ["txt", "pdf", "docx", "https"]
        if ftype in supported_ftypes:
            self.parser = eval("self.{}_parser".format(ftype))
        else:
            self.parser = self.txt_parser

    def parse(self, fname):
        return self.parser(fname)

    def https_parser(self, fname):
        urls = [fname]
        loader = AsyncHtmlLoader(urls)
        docs = loader.load()
        html2text = Html2TextTransformer()
        docs_transformed = html2text.transform_documents(docs)
        return docs_transformed[0].page_content

    def docx_parser(self, fname):
        doc = docx.Document(fname)
        return "\n".join([par.text for par in doc.paragraphs])

    def txt_parser(self, fname):
        with (fname, 'r') as f:
            return "\n".join(f.readlines())

    def pdf_parser(self, fname):
        reader = PdfReader(fname)
        return "\n".join([page.extract_text() for page in reader.pages])

class Context:
    # We can brainstorm this as necessary
    def __str__(self):
        return "Context(description: {}, path: {}, ftype: {}, content: {})".format(self.description, self.path, self.ftype, self.content)

    def __init__(self, description, path):
        supported_ftypes = ["txt", "pdf", "docx"]

        self.description = description
        self.path = path

        ftype_search = re.search(r'.*?\.([a-z]*)$', path)
        http_search = re.match(r'^http(s?):.*', path)
        if http_search != None:
            self.ftype = "https"
        elif ftype_search != None: 
            ftype = ftype_search.group(1)
            if ftype in supported_ftypes:
                self.ftype = ftype 
            else:
                self.ftype = None
        else:
            self.ftype = None

        self.content = ContextParser(self.ftype).parse(self.path)

    def to_dict(self):
        return {
            "description": self.description,
            "content": self.content
        }

