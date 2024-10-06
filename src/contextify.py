from typing import Annotated, Literal, TypedDict, List, Union, Tuple, Dict, Optional
from rich import print
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
import operator
import concurrent.futures

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

class ContextifierAgentState(BaseModel):
    messages: Annotated[List[Union[HumanMessage,SystemMessage,AIMessage]], operator.add] = Field(description= "The history of messages")# messages: keeps track of history
    contexts: List[Context] = Field(description= "A list of Context objects")# descriptions: guidelines for acting on content
    template: Template = Field(description = "The template that we want to fill out with information in contexts")

class Contextifier:
    def __init__(self, model, system=""):
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

        self.__preprocess = Preprocess(model)

    def preprocessor(self, state: ContextifierAgentState):
        to_process_contexts = []
        processed_contexts = []
        messages = []

        print('Invoking [bold green]preprocessor[/bold green]')

        for context in state.contexts:
            if not context.metadata.processed:
                to_process_contexts.append(context)
            else: 
                processed_contexts.append(context)

        if len(to_process_contexts) > 0:
            result = self.__preprocess.invoke(to_process_contexts)
            to_process_contexts = result["contexts"]
            messages = result["messages"]

        return {
            "messages": messages + [AIMessage(content = "Preprocessed contexts.")],
            "contexts": processed_contexts + to_process_contexts
        }

    def extractor(self, state: ContextifierAgentState):
        class ToReplace(BaseModel):
            to_replace: List[str] = Field(description = "Text inside the template contained within the brackets, {brackets}".format(brackets = state.template.metadata.brackets))

        print('Invoking [bold purple]extractor[/bold purple]')
        EXTRACTOR_PROMPT = """You are an extractor whose role is to identify and extract text contained inside the specified brackets. 
        Here is an example
        INPUTS:
        Bracket: (<, >)
        Template: I am really craving some <insert a food>

        OUTPUT:
        [insert a food]
        """
        message = HumanMessage(content=f"Here is a template, a description about the information in the template, and the brackets to help identify text/content: \nDESCRIPTION: {state.template.description}\nTEMPLATE: {state.template.content}\nBRACKETS: {state.template.metadata.brackets}")
        messages = [SystemMessage(content=EXTRACTOR_PROMPT)] + [message]
        response = self.model.with_structured_output(ToReplace).invoke(messages)
            
        print('Done with [bold purple]extractor[/bold purple]')
        print(f'Output: {response.to_replace}')
        return response.to_replace
        
    # TODO: Improve the tagger
    def tagger(self, state: ContextifierAgentState):
        messages = state.messages
        extracted_template = self.extractor(state)

        class ToSubstitute(BaseModel):
            to_substitute: List[RelatedInformation] = Field(description= "The related information for each of the sections/areas that will be filled/replaced with information from contexts") 
        
        # TODO: improve system prompt
        TAGGER_PROMPT = """You are a data collector who will find content to replace each of words to replace. 
        Thus, your job is to find pieces of information that best correspond to the text/information from the template that we want to substitute, using the `content` from the Contexts. 

        Make sure to include ALL the information that can be used to replace the text that we want to substitute. We want to make sure that there are multiple options (if they exist, of course).
        """
        message = HumanMessage(content=f"\nCONTEXTS: {state.contexts}\nTEXT TO SUBSTITUTE: {extracted_template}")
        messages = [SystemMessage(content=TAGGER_PROMPT)] + [message]
        response = self.model.with_structured_output(ToSubstitute).invoke(messages)

        # TODO: update the state
        state.template.metadata.to_substitute = response.to_substitute
        return {
            "messages": [AIMessage(content= "Labeled descriptions")],
            "template": state.template
        }

    def contextifier(self, state: ContextifierAgentState, noutputs = 3):
        print('Invoking [bold dark_orange]contextifier[/bold dark_orange]')
        CONTEXTIFIER_PROMPT = """You are writer whose role is seamlessly blend and substitute information that we've extracted into the template. Prioritize the information that we have gathered like `to_substitute`. Feel free to make slight modifications around the areas which will be substituted to make sure that everything flows grammatically and syntactically. 
        """
        message = HumanMessage(content=f"Fill in the tagged areas in the template (which are identified by brackets) to complete the template, utilizing the contexts and template metadata to aid in this task. \nTEMPLATE: {state.template.content}\nBRACKETS: {state.template.metadata.brackets}\nContexts: {state.contexts}\n\nGive me {noutputs} versions of the filled template")
        messages = [SystemMessage(content=CONTEXTIFIER_PROMPT)] + [message]
        response = self.model.invoke(messages)
            
        print('Done with [bold dark_orange]contextifier[/bold dark_orange]')
        return {'messages': [response]}
        
    # TODO: Improve the tagger
    def tagger(self, state: ContextifierAgentState):
        print('Invoking [bold dodger_blue]tagger[/bold dodger_blue]')
        messages = state.messages
        extracted_template = self.extractor(state)

        class ToSubstitute(BaseModel):
            to_substitute: List[RelatedInformation] = Field(description= "The related information for each of the sections/areas that will be filled/replaced with information from contexts") 
        
        # TODO: improve system prompt
        TAGGER_PROMPT = """You are a data collector who will find content to replace each of words to replace. 
        Thus, your job is to find pieces of information that best correspond to the text/information from the template that we want to substitute, using the `content` from the Contexts. 

        Make sure to include ALL the information that can be used to replace the text that we want to substitute. We want to make sure that there are multiple options (if they exist, of course).
        """
        message = HumanMessage(content=f"\nCONTEXTS: {state.contexts}\nTEXT TO SUBSTITUTE: {extracted_template}")
        messages = [SystemMessage(content=TAGGER_PROMPT)] + [message]
        response = self.model.with_structured_output(ToSubstitute).invoke(messages)
        print('Done with [bold dodger_blue]tagger[/bold dodger_blue]')

        # TODO: update the state
        state.template.metadata.to_substitute = response.to_substitute
        return {
            "messages": [AIMessage(content= "Labeled descriptions")],
            "template": state.template
        }
        pass

    def gatherer(self, state: ContextifierAgentState):
        pass

    def is_missing_info(self):
        pass

