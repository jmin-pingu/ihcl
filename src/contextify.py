from typing import Annotated, Literal, TypedDict, List, Union
from rich import print
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
import operator
import concurrent.futures

from pydantic import BaseModel, Field

src_dir = os.path.join(project_root, 'src')
sys.path.append(src_dir)
from preprocess import Context, Preprocess

class ContextifierAgentState(BaseModel):
    messages: Annotated[List[Union[HumanMessage,SystemMessage,AIMessage]], operator.add] = Field(description= "The history of messages")# messages: keeps track of history
    contexts: List[Context] = Field(description= "A list of Context objects")# descriptions: guidelines for acting on content
    template: Template = Field(description = "The template that we want to fill out with information in contexts")

class Template(BaseModel):
    content: str = Field(description = "The content inside the template")
    description: str = Field(description = "A description about the template")
    metadata: TemplateMetadata = Field(description= "Metadata associated with the template")

class TemplateMetadata(BaseModel):
    tags: List[str] = Field(description= "The associated tags for each of the sections/areas that will be filled/replaced with contexts") 
    delimiter = Tuple[str, str] = Field(description="The left and right delimiters that identify sections/areas that will be replaced with contexts")

class Contextifier:
    def __init__(self, model, system=""):
        graph = StateGraph(ContextifierAgentState)

        graph.add_node("preprocessor", self.preprocessor)
        graph.add_node("tagger", self.tagger)
        graph.add_node("contextifier", self.contextifier)
        graph.add_node("gatherer", self.gatherer)

        graph.set_entry_point("tagger")

        # graph.add_conditional_edges(
        #     "categorizer", 
        #     valid_categories, 
        #     {"categorizer": "categorizer", "summarizer": "summarizer"}
        # )

        # graph.add_conditional_edges(
        #     "categorizer", 
        #     valid_categories, 
        #     {END: END, "summarizer": "summarizer"}
        # )

    def preprocessor(self, state: ContextifierAgentState):
        # TODO: filter by context.metadata.preprocessed
        abot = Preprocess(model)

        pass

    def tagger(self, state: ContextifierAgentState):
        pass

    def contextifier(self, state: ContextifierAgentState):
        pass

    def gatherer(self, state: ContextifierAgentState):
        pass

    def is_missing_info(self):
        pass

    def pass(self):
        pass

    def invoke(self, ...):
        pass

