import re
import docx 
from pypdf import PdfReader
from urllib.request import urlopen
from langchain_community.document_transformers import Html2TextTransformer
from langchain_community.document_loaders import AsyncHtmlLoader
import concurrent
from rich import print
import requests
import functools
import html2text
from typing_extensions import TypedDict, List
from pydantic import TypeAdapter

import os

class Contexts:
    def __init__(self, contexts, delim = ","):
        class ContextInput(TypedDict): 
            description: str
            path: str
        
        class ContextsInput(TypedDict):
            contexts: List[ContextInput]

        try:
            ta = TypeAdapter(ContextsInput)
            ta.validate_python({"contexts": contexts})
        except:
            raise ValueError("`contexts` is not of the correct structure. Double-check contextf.")

        self.contexts = []
        print(f"[bold bright_red]Processing Contexts[/bold bright_red]")
        
        # NOTE: we need to cache because we do not want to reparse strings that we already have handled
        @functools.cache
        def init_context(context):
            print(f"\t-> processing Context: {context['path']}")
            return Context(context['description'], context['path'])

        with concurrent.futures.ThreadPoolExecutor(max_workers = 5) as executor:
            for context in executor.map(init_context, contexts):
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
        try: 
            urls = [fname]
            loader = AsyncHtmlLoader(urls)
            docs = loader.load()
            h2t = Html2TextTransformer()
            docs_transformed = h2t.transform_documents(docs)
            content = docs_transformed[0].page_content
        except Exception as inst:
            print(f"Error Parsing: {inst}\nRetrying") 
            with requests.Session() as s:
                response = s.get(fname)
            h = html2text.HTML2Text()
            content = h.handle(str(response.content))
        return content
    def docx_parser(self, fname):
        doc = docx.Document(fname)
        return "\n".join([par.text for par in doc.paragraphs])

    def txt_parser(self, fname):
        with open(fname, 'r') as f:
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

        ftype = os.path.splitext(path)[1]
        http_search = re.match(r'^http(s?):.*', path)
        if http_search != None:
            self.ftype = "https"
        elif ftype != '': 
            if ftype[1:] in supported_ftypes:
                self.ftype = ftype[1:]
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

