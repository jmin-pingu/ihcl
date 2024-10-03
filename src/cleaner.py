from typing import Annotated, Literal, TypedDict, List

class ContextAgentState(TypedDict):
    descriptions: List[str]
    content: List[str]
    cleaned: List[bool]

class Contextifier:
    def __init__(self, model, tools, system=""):
        self.system = """You are a data cleaner, categorizer, and summarizer. \
                      a \
                      You are allowed to make multiple calls (either together or in sequence). \
                      """

        graph = StateGraph(ContextifierState)

        graph.add_node("cleaner", self.call_openai)
        graph.set_entry_point("cleaner")
        self.graph = graph.compile()

        # self.tools = {t.name: t for t in tools}
        # self.model = model.bind_tools(tools)

    def cleaner(self, state: ContextAgentState):
        messages = state['content']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return message
