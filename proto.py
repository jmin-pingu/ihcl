import docx
import re
from pypdf import PdfReader
from urllib.request import urlopen
from langchain_community.document_transformers import Html2TextTransformer
from langchain_community.document_loaders import AsyncHtmlLoader
from typing import TypedDict, List
from langchain_core.pydantic_v1 import BaseModel, Field

class Context(BaseModel):
    description: str = Field(description="The description about what is contained in this Context object")
    content: str = Field(description="The content of the context object")


class CleanedContext(BaseModel):
    cleaned: bool = Field(description="Whether the Context was cleaned or not")
    context: Context = Field(description="A Context object")

class ContextAgentState(BaseModel):
    cleaned_contexts: List[CleanedContext] = Field(description= "A list of CleanedContext objects")# descriptions: guidelines for acting on content

def main():
    data: ContextAgentState = {
            "cleaned_contexts": {"cleaned": False, 
                                 "context": {"description":"test_desc", "content": "test_content"}}
    }
    print(data)

if __name__ == '__main__':
    main()
