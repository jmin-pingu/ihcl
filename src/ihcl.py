from rich import print
import typer
from typing_extensions import Annotated
from typing import Optional, Tuple, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import os
import sys
# Get the absolute path of the project's root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add the 'src' directory to the Python path
src_dir = os.path.join(project_root, 'src')
sys.path.append(src_dir)
import contextparser

model = ChatOpenAI(model="gpt-4")

app = typer.Typer()

def CreateTemplate(context: str, template: str):
    output = f"""Use the following context to fill in the appropriate sections in the template, surrounding these changes with [u][/u]. An appropriate section is defined between < and >. For example, <name> represents a template where we would want to fill in a name from the context and would be surrounded by [u]inserted name[/u]. If you don't know what to fill in, don't try to make anything up. Make sure that the filled in sections make sense with respect to the template and is grammatically correct.
    Context: {context}

    Template: {template}

    Output:"""
    return output

@app.command()
def contextify(
        contextf: Annotated[str, typer.Argument()], 
        template: Annotated[str, typer.Argument()]
    ):
    # Process contect and template appropriately
    if not contexts: 
        raise ValueError("No argument provided for contexts")

    template_f = open(template, "r")
    parsed_context = context_f.read()
    parsed_template = template_f.read()

    
if __name__ == "__main__":
    app()
