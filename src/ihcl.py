from rich import print
import typer
from typing_extensions import Annotated
from typing import Optional, Tuple, List
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage

import concurrent.futures

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
from omegaconf import OmegaConf

# TODO: eventually switch to an ollama model 

app = typer.Typer()

@app.command()
def contextify(
        contextf: Annotated[str, typer.Argument(help="The yaml file that contains ...")], # TODO: fill out description
        templatef: Annotated[str, typer.Argument(help="The template file which contains fields surrounded by a bracket that will be filled based on context and the template")],
        bracket: Annotated[Tuple[str, str], typer.Argument(help="The pair of brackets which identify fields in the template that will be filled with context")],
        hitl: Annotated[bool, typer.Option("--hitl", "-h", help= "Option for human in the loop workflow")] = False,
        logf: Annotated[str, typer.Option("--log", "-l", help= "Filename for log")] = None
        # human-in-the-loop option
        # tools
    ):

    assert os.path.splitext(contextf)[1] == ".yaml", ValueError("The contextf must be a .yaml file")

    # Retrieve user-provided contexts form contextf
    parsedf = OmegaConf.load(contextf)
    fixed_contexts = parsedf['fixed_contexts']
    variable_contexts = parsedf['variable_contexts']
    parsed_contexts_list = []

    # Append each variable context to the fixed contexts and then create a contexts object
    for contexts in variable_contexts:
        parsed_contexts_list.append(Contexts(fixed_contexts + contexts))

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

    def run_contextifier(parsed_contexts):
        contexts = [context.to_dict() | {"metadata": {"processed": False}} for context in parsed_contexts.contexts]    
        state: ContextifierAgentState = {
            "contexts": contexts,
            "template": template,
            "output": None
        }
        result = Contextifier(model, logf=logf).graph.invoke(state)
        response = result["output"].filled_templates
        return response

    model = ChatOpenAI(model="gpt-4o-mini")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for pid, response in enumerate(executor.map(run_contextifier, parsed_contexts_list)):
            for i, txt in enumerate(response):
                with open("output/{}_filled_template_{}.txt".format(pid, i), "w") as f:
                    f.write(txt)


    
if __name__ == "__main__":
    app()
