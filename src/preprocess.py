from typing import Annotated, Literal, TypedDict, List, Union
from rich import print
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
import operator
import concurrent.futures

from pydantic import BaseModel, Field

# Data Model
class ContextMetadata(BaseModel):
    processed: bool = Field(description="Whether the Context was completely processed or not")

class Context(BaseModel):
    description: str = Field(description="The description about what is contained in this Context object")
    content: str = Field(description="The content of the context object")
    metadata: ContextMetadata = Field(description="Metadata about the context object")

class PreprocessAgentState(BaseModel):
    messages: Annotated[List[Union[HumanMessage,SystemMessage,AIMessage]], operator.add] = Field(description= "The history of messages")# messages: keeps track of history
    contexts: List[Context] = Field(description= "A list of Context objects")# descriptions: guidelines for acting on content

# Preprocess Graph
# NOTE: potentially cache instantiations of this class
class Preprocess:
    def __init__(self, model, system=""):
        graph = StateGraph(PreprocessAgentState)

        graph.add_node("cleaner", self.cleaner)
        # graph.add_node("categorizer", self.categorizer)
        # graph.add_node("summarizer", self.summarizer)

        graph.set_entry_point("cleaner")
        # graph.add_edge("cleaner", "categorizer")
        # graph.add_edge("categorizer", "summarizer")

        # graph.add_conditional_edges(
        #     "categorizer", 
        #     valid_categories, 
        #     {"categorizer": "categorizer", "summarizer": "summarizer"}
        # )
        graph.add_edge("cleaner", END)

        self.graph = graph.compile()

        # self.tools = {t.name: t for t in tools}
        self.model = model

    def valid_categories(self):
        pass

    def summarizer(self, state: PreprocessAgentState, max_workers = 5):
        # Eventually multithread this to operate per CleanedContext
        print('Invoking [bold yellow]summarizer[/bold yellow]')
        messages = state.messages
        SUMMARIZER_PROMPT = """You are a summarizer tasked with intelligently combining the provided list of CleanedContext objects with the SAME description. \
        Your role is to intelligently combine information from the `content` while being aligned with the intention of the description. \
        You are allowed to make syntactic or grammatical changes to maintain the flow of content. \
        Make sure to return the whole `Context` object, only summarizing the `content` based on `description` and `summarized` attribute of `metadata`.
        """

        grouped_cc = dict()
        for context in state.contexts:
            grouped_cc.setdefault(context.description, [])
            grouped_cc[context.description].append(context)
        
        def summarize_contexts(contexts):
            message = HumanMessage(
                content=f"{contexts}"
            )
            messages = [SystemMessage(content=SUMMARIZER_PROMPT)] + [message]
            return self.model.with_structured_output(Context).invoke(messages)

        summarized_contexts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers = max_workers) as executor:
            for cc in executor.map(summarize_contexts, grouped_cc.values()):
                summarized_contexts.append(cc)

        print('Done with [bold yellow]summarizer[/bold yellow]')

        for context in summarized_contexts:
            context.metadata.processed = True

        return {
            # TODO: think about a better use for messages. What do I want to log?
            'messages': [AIMessage(content = f"Summarized contexts: {summarized_contexts}")],
            'contexts': summarized_contexts
        }
        pass

    def cleaner(self, state: PreprocessAgentState, max_workers = 5):
        # Eventually multithread this to operate per CleanedContext
        print('Invoking [bold red]cleaner[/bold red]')
        messages = state.messages
        CLEANER_PROMPT = """You are a text extractor and data cleaner tasked with cleaning the provided Context object.\
        Your role is to clean/remove information from the `content` that is not related to the `description`.\
        Only making syntactic or grammatical changes to maintain the flow of content. \
        Make sure to return the whole `Context` object, only updating the `content` based on `description` and `cleaned` attribute of `metadata`.
        """

        def clean_context(context):
            message = HumanMessage(
                content=f"{context}"
            )
            messages = [SystemMessage(content=CLEANER_PROMPT)] + [message]
            return self.model.with_structured_output(Context).invoke(messages)

        cleaned_contexts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers = max_workers) as executor:
            for cc in executor.map(clean_context, state.contexts):
                cleaned_contexts.append(cc)

        print('Done with [bold red]cleaner[/bold red]')

        for context in cleaned_contexts:
            context.metadata.processed = False

        return {
            'messages': [AIMessage(content = f"Cleaned contexts: {cleaned_contexts}")],
            'contexts': cleaned_contexts
        }

    def categorizer(self, state: PreprocessAgentState, categories = None):
        print('Invoking [bold blue]categorizer[/bold blue]')

        messages = state.messages
        # You will potentially rename the descriptions in the provided list of CleanedContext object which contains a `Context` object with an associated `cleaned` boolean indicator. \

        CATEGORIZER_PROMPT = """You are a categorizer, finding similarities between provided descriptions and giving them a common category if it makes sense. \
        Your job is to find commonalities between the `description`s and rename them into categories so that we can combine their information in the future. \
        You will be operating over a list of descriptions and you can only modify them in-place. \
        If there is no need to rename the `description`s, then keep the existing descriptions.
        """

        class Descriptions(BaseModel):
            descriptions: List[str] = Field(description= "A list of descriptions", min_length=len(state.contexts), max_length=len(state.contexts))

        descriptions = [context.description for context in state.contexts]
        message = HumanMessage(content=f"{descriptions}")
        messages = [SystemMessage(content=CATEGORIZER_PROMPT)] + [message]
        response = self.model.with_structured_output(Descriptions).invoke(messages)

        for context, new_desc in zip(state.contexts, response.descriptions):
            context.description = new_desc
            
        print('Done with [bold blue]categorizer[/bold blue]')
        print(f'Output: {response.descriptions}')
        return {
            'messages': [AIMessage(content = f"New description categories: {response.descriptions}")],
        }

    def invoke(self, contexts: List[Context]):
        content = "Clean and categorize the list of context objects."
        messages = [HumanMessage(content=content)]
        state: PreprocessAgentState = {
            "messages": messages,
            "contexts": contexts
        }
        return self.graph.invoke(state)

