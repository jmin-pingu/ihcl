from typing import Annotated, Literal, TypedDict, List, Union, Optional
from rich import print
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
import operator
import concurrent.futures
from omegaconf import OmegaConf

from pydantic import BaseModel, Field

# Data Model
class ContextMetadata(BaseModel):
    processed: bool = Field(description="Whether the Context was completely processed or not")

class Context(BaseModel):
    description: str = Field(description="The description about what is contained in this Context object")
    content: Optional[str] = Field(description="The content of the context object")
    metadata: ContextMetadata = Field(description="Metadata about the context object")

class PreprocessAgentState(BaseModel):
    messages: Annotated[List[Union[HumanMessage,SystemMessage,AIMessage]], operator.add] = Field(description= "The history of messages")# messages: keeps track of history
    contexts: List[Context] = Field(description= "A list of Context objects")# descriptions: guidelines for acting on content

# Preprocess Graph
# NOTE: potentially cache instantiations of this class
class Preprocess:
    def __init__(self, model, system=None, logf=None):
        graph = StateGraph(PreprocessAgentState)

        graph.add_node("cleaner", self.cleaner)
        graph.add_node("categorizer", self.categorizer)
        graph.add_node("summarizer", self.summarizer)

        graph.set_entry_point("cleaner")
        graph.add_edge("cleaner", "categorizer")
        graph.add_edge("categorizer", "summarizer")

        # graph.add_conditional_edges(
        #     "categorizer", 
        #     valid_categories, 
        #     {"categorizer": "categorizer", "summarizer": "summarizer"}
        # )
        graph.add_edge("summarizer", END)

        self.graph = graph.compile()
        self.__prompts = OmegaConf.load('src/prompts.yaml')['preprocessor']

        # self.tools = {t.name: t for t in tools}
        self.model = model
        self.logf = logf

    def valid_categories(self):
        pass

    def summarizer(self, state: PreprocessAgentState, max_workers = 5):
        # Eventually multithread this to operate per CleanedContext
        print('Invoking [bold yellow]summarizer[/bold yellow]')
        SUMMARIZER_PROMPT = self.__prompts["components"]["summarizer"]["system_prompt"]

        grouped_cc = dict()
        for context in state.contexts:
            grouped_cc.setdefault(context.description, [])
            grouped_cc[context.description].append(context)
        
        def summarize_contexts(contexts):
            messages = [SystemMessage(content=SUMMARIZER_PROMPT)] + [HumanMessage(content=f"{contexts}")]
            return self.model.with_structured_output(Context).invoke(messages)

        summarized_contexts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers = max_workers) as executor:
            for cc in executor.map(summarize_contexts, grouped_cc.values()):
                summarized_contexts.append(cc)

        print('Done with [bold yellow]summarizer[/bold yellow]')
        for context in summarized_contexts:
            context.metadata.processed = True

        self.append_to_log(f'summarizer: summarized content in Contexts.\n{summarized_contexts}"')

        return {
            'contexts': summarized_contexts
        }

    def cleaner(self, state: PreprocessAgentState, max_workers = 5):
        # Eventually multithread this to operate per CleanedContext
        print('Invoking [bold red]cleaner[/bold red]')
        CLEANER_PROMPT = self.__prompts["components"]["cleaner"]["system_prompt"]

        def clean_context(context):
            messages = [SystemMessage(content=CLEANER_PROMPT)] + [HumanMessage(content=f"{context}")]
            return self.model.with_structured_output(Context).invoke(messages)

        cleaned_contexts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers = max_workers) as executor:
            for cc in executor.map(clean_context, state.contexts):
                cleaned_contexts.append(cc)


        cleaned_contexts = list(filter(lambda c: c.content != None, cleaned_contexts))
        print('Done with [bold red]cleaner[/bold red]')

        for context in cleaned_contexts:
            context.metadata.processed = False

        self.append_to_log(f'cleaner: cleaned content in Contexts unrelated to description.\n{cleaned_contexts}"')
        return {
            'contexts': cleaned_contexts
        }

    def categorizer(self, state: PreprocessAgentState, categories = None):
        print('Invoking [bold blue]categorizer[/bold blue]')
        # You will potentially rename the descriptions in the provided list of CleanedContext object which contains a `Context` object with an associated `cleaned` boolean indicator. \

        CATEGORIZER_PROMPT = self.__prompts["components"]["categorizer"]["system_prompt"]

        class Descriptions(BaseModel):
            descriptions: List[str] = Field(description= "A list of descriptions", min_length=len(state.contexts), max_length=len(state.contexts))

        descriptions = [context.description for context in state.contexts]
        messages = [SystemMessage(content=CATEGORIZER_PROMPT)] + [HumanMessage(content=f"{descriptions}")]
        response = self.model.with_structured_output(Descriptions).invoke(messages)

        for context, new_desc in zip(state.contexts, response.descriptions):
            context.description = new_desc
            
        print('Done with [bold blue]categorizer[/bold blue]')
        self.append_to_log(f'categorizer: identified categories for Contexts\n{response}"')
        return {
            'contexts': state.contexts
        }

    def invoke(self, contexts: List[Context]):
        content = "Preprocess the list of context objects."
        messages = [HumanMessage(content=content)]
        state: PreprocessAgentState = {
            "contexts": contexts
        }
        self.append_to_log(f'system: {content}"')
        return self.graph.invoke(state)

    def append_to_log(self, text):
        if self.logf == None:
            return  
        with open(self.logf, "a") as f:
            f.write(text + "\n") 
