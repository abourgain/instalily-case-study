"""AI Agent to handle user queries and provide answers using a set of tools."""

import argparse
import json
from typing import Union
import re

from langchain.agents import Tool, AgentExecutor, AgentOutputParser, create_react_agent
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate


from backend.graph_rag.config import ENTITY_TYPES
from backend.graph_rag.graph_query import query_db
from backend.graph_rag.similarity_query import similarity_search


TOOLS = [
    Tool(name="Query", func=query_db, description="Use this tool to find entities in the user prompt that can be used to generate queries"),
    Tool(name="Similarity Search", func=similarity_search, description="Use this tool to perform a similarity search in the database"),
]

TOOL_NAMES = [f"{tool.name}: {tool.description}" for tool in TOOLS]

PROMPT_TEMPLATE = '''
Your goal is to answer the user's question as accurately as possible using the tools at your disposal. You have access to these tools:

{tools}

Use the following format:

Question: the input prompt from the user
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}] (refer to the rules below)
Action Input: the input to the action
Observation: the result of the action (include the raw tool output here)
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Rules to follow:

1. Always start by using the Query tool with the prompt as a parameter to retrieve relevant information from the database, such as part details, compatibility, installation instructions, or troubleshooting steps. 
   - If the Query tool returns a result that answers the user's question, validate the information and proceed to the final answer.
   - If the result is ambiguous, incomplete, or not directly related to the user's query, proceed to step 2.
2. If the Query tool does not provide a conclusive answer, use the Similarity Search tool with the full initial user prompt to find additional information. Validate the results against the query.
3. If the tools return no results or if the raw tool output does not provide a definitive answer, do not attempt to create an answer on your own. Instead, clearly state "I do not know" or "I do not have this answer."
4. If you still cannot find the answer, ask the user for more context or clarification, such as specific part numbers, model numbers, or the exact issue they are facing.
5. After gathering more context, repeat Step 1 and Step 2 as needed. If you found results, stop here.
6. If you cannot find the final answer after all attempts, tell the user that you are unable to help with the question by saying "I do not know" or "I do not have this answer."

When providing the final answer:
- If the question is about part compatibility, mention whether the part is compatible or not.
- If the question is about installation, provide the relevant instructions or guide.
- If the question is about troubleshooting, provide the steps or advice on how to fix the issue.
- Always be concise and use the exact names and details from the database where applicable.
- Never fabricate information; rely strictly on the data retrieved by the tools.

If you found relevant results, reply with the answer in a clear format, and include the relevant part/model details as needed.

Include the raw tool outputs in your observations so that the decision-making process can be reviewed.

If the tools return no results, your final answer should be "I do not know" or "I do not have this answer."

User prompt:
{input}

{agent_scratchpad}
'''


class CustomPromptTemplate(StringPromptTemplate):
    """Custom prompt template for the agent."""

    template: str

    def format(self, **kwargs) -> str:
        # Get the intermediate steps (AgentAction, Observation tuples)
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "

        # Set the agent_scratchpad variable to that value
        kwargs["agent_scratchpad"] = thoughts

        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in TOOLS])

        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in TOOLS])
        kwargs["entity_types"] = json.dumps(ENTITY_TYPES, indent=4)

        return self.template.format(**kwargs)


class CustomOutputParser(AgentOutputParser):
    """Custom output parser for the agent."""

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:  # pylint: disable=arguments-renamed
        """Parse the LLM output and return an AgentAction or AgentFinish object."""

        # Check if agent should finish
        if "Final Answer:" in llm_output:
            return AgentFinish(
                # Return values is generally always a dictionary with a single `output` key
                # It is not recommended to try anything else at the moment :)
                return_values={"output": llm_output.split("Final Answer:")[-1].strip()},
                log=llm_output,
            )

        # Parse out the action and action input
        regex = r"Action: (.*?)[\n]*Action Input:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)

        # If it can't parse the output it raises an error
        # You can add your own logic here to handle errors in a different way i.e. pass to a human, give a canned response
        if not match:
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)

        # Return the action and action input
        return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)


class Agent:
    """Agent class to handle the agent execution."""

    def __init__(self):
        self.agent_executor = self._init_agent_executor()

    def _init_agent_executor(self) -> AgentExecutor:
        # prompt = CustomPromptTemplate(
        #     template=PROMPT_TEMPLATE,
        #     tools=TOOLS,
        #     input_variables=["input", "intermediate_steps"],
        # )
        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
        )
        llm = ChatOpenAI(temperature=0, model="gpt-4")
        output_parser = CustomOutputParser()

        agent = create_react_agent(
            llm=llm,
            tools=TOOLS,
            prompt=prompt,
            output_parser=output_parser,
            stop_sequence=["\nObservation:"],
        )

        agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=TOOLS, verbose=True)
        return agent_executor

    def invoke(self, user_input: str) -> str:
        """Invoke the agent with the user input."""
        result = self.agent_executor.invoke({"input": user_input})

        return result["output"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed entities in the Neo4j graph")
    parser.add_argument("--message", type=str, help="The message to send to the agent")
    args = parser.parse_args()
    # USER_INPUT = "How can I install part number PS11752778?"
    # USER_INPUT = "How can I install part number PS2?"
    # USER_INPUT = "What parts compose the FPHD2491KF0 model number?"

    agent_exe = Agent()
    print(f"\n\n--->Result: \n{agent_exe.invoke(args.message)}\n\n")
