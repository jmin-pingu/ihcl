from rich import print
import typer
from typing_extensions import Annotated
from typing import Optional, Tuple, List

import os
import sys
# Get the absolute path of the project's root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add the 'src' directory to the Python path
src_dir = os.path.join(project_root, 'src')
sys.path.append(src_dir)
from contexts import Contexts

# TODO: eventually switch to an ollama model 
model = ChatOpenAI(model="gpt-4")

app = typer.Typer()

@app.command()
def contextify(
        contextf: Annotated[str, typer.Argument(help="The file that contains a (description, path) pair. The structure should follow DESCRIPTION DELIM PATH")], 
        delim: Annotated[str, typer.Option("--delim", "-d", help= "The delimiter for contextf")] = ",", 
        templatef: Annotated[str, typer.Argument(help="The template file which contains fields surrounded by a bracket that will be filled based on context and the template")],
        bracket: Annotated[Tuple[str, str], typer.Argument(help="The pair of brackets which identify fields in the template that will be filled with context")],
        # human-in-the-loop option
        # tools
    ):

    parsed_contexts = Contexts(contextf, delim)
    for context in parsed_contexts.contexts:
        print(context)
    # parsed_template = Context("template", template_f)

    
if __name__ == "__main__":
    app()
