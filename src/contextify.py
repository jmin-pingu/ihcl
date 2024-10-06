from typing import Annotated, Literal, TypedDict, List, Union, Tuple, Dict, Optional
from rich import print
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
import operator
import concurrent.futures
from omegaconf import OmegaConf

from pydantic import BaseModel, Field

import os
import sys
# Get the absolute path of the project's root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add the 'src' directory to the Python path
src_dir = os.path.join(project_root, 'src')
sys.path.append(src_dir)
from preprocess import Context, Preprocess

class RelatedInformation(BaseModel):
    information_of_interest: str = Field(description = "This is information of interest.")
    information_to_substitute: Optional[List[str]] =  Field(description = "Information which will be used for replacing the information of interest. Thus, the information to substitute must be related to the information of interest.")

class TemplateMetadata(BaseModel):
    to_substitute: List[RelatedInformation] = Field(description= "The related information for each of the sections/areas that will be filled/replaced with information from contexts") 
    brackets: Tuple[str, str] = Field(description="The left and right brackets that identify sections/areas that will be replaced with contexts")

class Template(BaseModel):
    content: str = Field(description = "The content inside the template")
    description: str = Field(description = "A description about the template")
    metadata: TemplateMetadata = Field(description= "Metadata associated with the template")

class FilledTemplates(BaseModel):
    filled_templates: List[str] = Field(description= "A list of templates filled with information from the Contexts object")

class ContextifierAgentState(BaseModel):
    contexts: List[Context] = Field(description= "A list of Context objects")# descriptions: guidelines for acting on content
    template: Template = Field(description = "The template that we want to fill out with information in contexts")
    output: Optional[FilledTemplates] = Field(description = "The final output to the contextifier agent")

class Contextifier:
    def __init__(self, model, system=None, logf=None):
        self.__prompts = OmegaConf.load('src/prompts.yaml')['contextifier']

        if system != None:
            self.system = [SystemMessage(content = system)]
        else:
            self.system = [SystemMessage(content = self.__prompts['main_system_prompt'])]
        graph = StateGraph(ContextifierAgentState)

        graph.add_node("preprocessor", self.preprocessor)
        graph.add_node("tagger", self.tagger)
#        graph.add_node("gather_information", self.gather_information)
        graph.add_node("contextifier", self.contextifier)
#        graph.add_node("gatherer", self.gatherer)
#
        graph.add_edge("preprocessor", "tagger")
        graph.add_edge("tagger", "contextifier")
        graph.add_edge("contextifier", END)

        graph.set_entry_point("preprocessor")

        # graph.add_conditional_edges(
        #     "tagger" 
        #     is_missing_info, 
        #     {"gatherer": "gatherer", "contextifier": "contextifier"}
        # )

        # graph.add_conditional_edges(
        #     "...", 
        #     valid_categories, 
        #     {END: END, "...": "..."}
        # )

        self.graph = graph.compile()
        self.model = model
        self.logf = logf
        if self.logf != None:
             with open(self.logf, "w") as f:
                 pass

        self.__preprocess = Preprocess(model, logf=self.logf)

    def preprocessor(self, state: ContextifierAgentState):
        to_process_contexts = []
        processed_contexts = []

        print('Invoking [bold green]preprocessor[/bold green]')

        for context in state.contexts:
            if not context.metadata.processed:
                to_process_contexts.append(context)
            else: 
                processed_contexts.append(context)

        if len(to_process_contexts) > 0:
            result = self.__preprocess.invoke(to_process_contexts)
            to_process_contexts = result["contexts"]

        self.append_to_log(f'preprocessor: preprocessed contexts.\n{processed_contexts + to_process_contexts}')
        return {
            "contexts": processed_contexts + to_process_contexts
        }

    def extractor(self, state: ContextifierAgentState):
        class ToReplace(BaseModel):
            to_replace: List[str] = Field(description = "Text inside the template contained within the brackets, {brackets}".format(brackets = state.template.metadata.brackets))

        print('Invoking [bold purple]extractor[/bold purple]')
        EXTRACTOR_PROMPT = self.__prompts["components"]["extractor"]["system_prompt"]

        message = HumanMessage(content=self.__prompts["components"]["extractor"]["human_prompt"].format(description=state.template.description, template=state.template.content, brackets=state.template.metadata.brackets))
        messages = self.system + [SystemMessage(content=EXTRACTOR_PROMPT)] + [message]
        response = self.model.with_structured_output(ToReplace).invoke(messages)
            
        print('Done with [bold purple]extractor[/bold purple]')

        self.append_to_log(f'extractor: identified and extracted text to replace in template.\n{response.to_replace}"')
        return response.to_replace
        
    # TODO: Improve the tagger
    def tagger(self, state: ContextifierAgentState):
        extracted_template = self.extractor(state)

        class ToSubstitute(BaseModel):
            to_substitute: List[RelatedInformation] = Field(description= "The related information for each of the sections/areas that will be filled/replaced with information from contexts") 
        
        # TODO: improve system prompt
        TAGGER_PROMPT = self.__prompts["components"]["tagger"]["system_prompt"]


        message = HumanMessage(content=self.__prompts["components"]["tagger"]["human_prompt"].format(contexts = state.contexts, text_to_substitute=extracted_template))
        messages = self.system + [SystemMessage(content=TAGGER_PROMPT)] + [message]
        response = self.model.with_structured_output(ToSubstitute).invoke(messages)

        # TODO: update the state
        state.template.metadata.to_substitute = response.to_substitute

        # Log changes
        self.append_to_log(f'tagger: tagged each string to replace in the template with related information from Contexts.\n{response}"')
        return {
            "template": state.template
        }

    def append_to_log(self, text):
        if self.logf == None:
            return  
        with open(self.logf, "a") as f:
            f.write(text + "\n") 

    def contextifier(self, state: ContextifierAgentState, noutputs = 3):
        print('Invoking [bold dark_orange]contextifier[/bold dark_orange]')
        CONTEXTIFIER_PROMPT = self.__prompts["components"]["contextifier"]["system_prompt"]

        message = HumanMessage(content=self.__prompts["components"]["contextifier"]["human_prompt"].format(template = state.template.content, brackets = state.template.metadata.brackets, contexts = state.contexts, noutputs = noutputs))
        messages = [SystemMessage(content=CONTEXTIFIER_PROMPT)] + [message]
        response = self.model.with_structured_output(FilledTemplates).invoke(messages)
        print('Done with [bold dark_orange]contextifier[/bold dark_orange]')

        self.append_to_log(f'contextifier: state of template.\n{state.template}"')
        self.append_to_log(f'contextifier: created {noutputs} filled templates with information in the contexts.\n{response}"')
        return {'output': response}         

    def gatherer(self, state: ContextifierAgentState):
        pass

    def is_missing_info(self):
        pass

