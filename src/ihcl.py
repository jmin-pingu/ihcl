from rich import print
import typer
from typing_extensions import Annotated
from typing import Optional, Tuple, List
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage

import os
import sys
# Get the absolute path of the project's root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add the 'src' directory to the Python path
src_dir = os.path.join(project_root, 'src')
sys.path.append(src_dir)
from contexts import Contexts, Context
from preprocess import PreprocessAgentState, Preprocess
from contextify import ContextifierAgentState, Contextifier
from langchain_openai import ChatOpenAI

# TODO: eventually switch to an ollama model 

app = typer.Typer()

@app.command()
def contextify(
        contextf: Annotated[str, typer.Argument(help="The file that contains a (description, path) pair. The structure should follow DESCRIPTION DELIM PATH")], 
        templatef: Annotated[str, typer.Argument(help="The template file which contains fields surrounded by a bracket that will be filled based on context and the template")],
        bracket: Annotated[Tuple[str, str], typer.Argument(help="The pair of brackets which identify fields in the template that will be filled with context")],
        delim: Annotated[str, typer.Option("--delim", "-d", help= "The delimiter for contextf")] = ",",
        hitl: Annotated[bool, typer.Option("--hitl", "-h", help= "Option for human in the loop workflow")] = False,
        logf: Annotated[str, typer.Option("--log", "-l", help= "Filename for log")] = None
        # human-in-the-loop option
        # tools
    ):

    parsed_contexts = Contexts(contextf, delim)
    parsed_template = Context("template", templatef)

    template_metadata = {
        "to_substitute": [],
        "brackets": bracket
    }

    template = {
        "content": parsed_template.content,
        "description": parsed_template.description,
        "metadata": template_metadata
    }

    model = ChatOpenAI(model="gpt-4o-mini")
    contexts = [context.to_dict() | {"metadata": {"processed": False}} for context in parsed_contexts.contexts]    
    state: ContextifierAgentState = {
        "contexts": contexts,
        "template": template,
        "output": None
    }

    result = Contextifier(model, logf=logf).graph.invoke(state)
    

    response = result["output"].filled_templates
    for i, txt in enumerate(response):
        with open("output/filled_template_{}.txt".format(i), "w") as f:
            f.write(txt)

    
if __name__ == "__main__":
    app()
