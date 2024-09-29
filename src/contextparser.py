import re
import docx 
from pypdf import PdfReader

class Contexts:
    def __init__(self, contextf, delim = ","):
        with open(contextf, "r") as f:
            parsed_lines = [[item.strip().replace("\n", "") for item in list(line.split(delim))] for line in f.readlines()]
        self.contexts = [Context(desc, path) for (desc, path) in parsed_lines]
        
class ContextParser:
    def __init__(self, ftype):
        supported_ftypes = ["txt", "pdf", "docx", "https"]
        if ftype in supported_ftypes:
            self.parser = eval("self.{}_parser".format(ftype))
        else:
            self.parser = self.txt_parser

    def parse(self, fname):
        return self.parser(fname)

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
        return "Context(description: {}, path: {}, ftype: {})".format(self.description, self.path, self.ftype)

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

    def get_type():
        pass
