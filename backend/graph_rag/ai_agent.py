"""AI Agent to handle user queries and provide answers using a set of tools."""

import argparse
import json
from typing import Union
import re

from langchain.agents import Tool, AgentExecutor, AgentOutputParser, create_react_agent
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel


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

Here is the conversation history so far:
{chat_history}

Use the following format:

Question: the input prompt from the user
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action (include the raw tool output here, which will be a list of dictionaries representing parts, models, etc.)
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer based on the provided data
Final Answer: the final answer to the original input question

Rules to follow:

1. **Tool Selection**: Always start by carefully considering which tool to use based on the user's query. For instance:
   - If the user is asking about part compatibility, start with the Query tool.
   - If the Query tool does not provide a definitive answer or more context is needed, consider using the Similarity Search tool to find additional related information.

2. **Understand and Validate the Output**: After using a tool, carefully examine the list of dictionaries returned by the tool, which may include data such as parts, models, and their relationships. Your role is to interpret this data to answer the user's question.
   - For example, if the tool returns a list that includes the queried part along with the model, you should conclude that the part is compatible with the model.
   - If the tool returns relevant installation or troubleshooting data, use this information to provide the appropriate guidance.

3. **Decide Next Steps**: 
   - If the tool's output sufficiently answers the question, proceed to formulate the final answer.
   - If the output is incomplete, ambiguous, or does not fully answer the question, choose the next appropriate tool and repeat the process.

4. **If No Conclusive Answer**: If the tools return no results or if the data does not answer the question directly, do not attempt to create an answer on your own. Instead, clearly state "I do not know" or "I do not have this answer."

5. **Request More Context**: If you still cannot find the answer, ask the user for more context or clarification, such as specific part numbers, model numbers, or the exact issue they are facing.

6. **Iteration**: After gathering more context, repeat the process as needed, using the tools to gather new data. If you find results that answer the question, stop here.

7. **Final Answer**:
   - If the question is about part compatibility, confirm whether the part is compatible based on the presence of the part and model in the tool's returned data.
   - If the question is about installation, provide the relevant instructions or guide based on the returned data.
   - If the question is about troubleshooting, provide steps or advice on how to fix the issue using the provided data.
   - Always be concise and use the exact names and details from the tool's output where applicable.
   - Never fabricate information; rely strictly on the data retrieved by the tools.

If you find relevant results, reply with the answer in a clear format, and include the relevant part/model details as needed.

Include the raw tool outputs in your observations so that the decision-making process can be reviewed.

If the tools return no results, your final answer should be "I do not know" or "I do not have this answer."

User prompt:
{input}

{agent_scratchpad}
'''

PARALLEL_PROMPT_TEMPLATE = '''
Your goal is to answer the user's question as accurately as possible using the tools at your disposal. You have access to these tools:

{tools}

Here is the conversation history so far:
{chat_history}

Use the following format:

Question: the input prompt from the user
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}] (this step is handled by running the Query and Similarity Search tools in parallel)
Action Input: (no action input needed as both tools are run automatically)
Observation: the combined results from both the Query and Similarity Search tools
Thought: Review the combined results and provide the final answer based on the information retrieved.
Final Answer: the final answer to the original input question

Rules to follow:

1. Both the Query and Similarity Search tools will be run in parallel automatically.
   - If the combined results from these tools provide a clear answer to the user's question, use the information to formulate your final answer.
   - If the results are inconclusive or do not directly answer the question, state that the information is insufficient to provide a definitive answer.
2. If the combined results do not provide the needed information, ask the user for more context or clarification, such as specific part numbers, model numbers, or the exact issue they are facing.
3. After gathering more context, repeat the process if necessary.
4. If you still cannot find the answer after all attempts, tell the user that you are unable to help with the question by saying "I do not know" or "I do not have this answer."

When providing the final answer:
- If the question is about part compatibility, mention whether the part is compatible or not, based on the combined results.
- If the question is about installation, provide the relevant instructions or guide.
- If the question is about troubleshooting, provide the steps or advice on how to fix the issue.
- Always be concise and use the exact names and details from the database where applicable.
- Never fabricate information; rely strictly on the data retrieved by the tools.

If you found relevant results, reply with the answer in a clear format, and include the relevant part/model details as needed.

Include the raw combined tool outputs in your observations so that the decision-making process can be reviewed.

If the combined tools return no useful results, your final answer should be "I do not know" or "I do not have this answer."

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
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.agent_executor = self._init_agent_executor()

    def _init_agent_executor(self) -> AgentExecutor:
        prompt = CustomPromptTemplate(
            template=PROMPT_TEMPLATE,
        )
        llm = ChatOpenAI(temperature=0, model="gpt-4")
        output_parser = CustomOutputParser()

        agent = create_react_agent(llm=llm, tools=TOOLS, prompt=prompt, output_parser=output_parser, stop_sequence=["\nObservation:"])

        agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=TOOLS, verbose=True)
        return agent_executor

    def invoke(self, user_input: str) -> str:
        """Invoke the agent with the user input."""
        # Add the user input to the memory
        self.memory.save_context({"input": user_input}, {})

        # Prepare the input with memory for the agent
        chat_history = self.memory.load_memory_variables({})["chat_history"]

        # Prepare the input with the history for the agent
        result = self.agent_executor.invoke({"input": user_input, "chat_history": chat_history})

        # Save the agent's response in memory
        self.memory.save_context({}, {"output": result["output"]})

        return result["output"]


class CombinedQueryTool(Tool):
    """Tool to run Query and Similarity Search in parallel and return combined results."""

    def __init__(self):
        super().__init__(name="Combined Query Tool", func=self._run, description="Runs Query and Similarity Search in parallel and returns combined results.")  # Use the method defined in this class

    def _run(self, input):  # pylint: disable=arguments-differ, redefined-builtin
        # Implement the parallel execution
        parallel_chain = RunnableParallel({"query_result": query_db, "similarity_result": similarity_search})

        results = parallel_chain.invoke(input)
        # Combine the results as needed, e.g., concatenate, merge, etc.
        combined_results = results["query_result"] + results["similarity_result"]
        return combined_results

    async def _arun(self, input):  # pylint: disable=arguments-differ, redefined-builtin
        # If you need async handling, implement it here.
        raise NotImplementedError("CombinedQueryTool does not support async")


# You would then use CombinedQueryTool as one of the tools in your agent
PARALLEL_TOOLS = [
    CombinedQueryTool(),
    # Other tools if necessary
]


class ParallelAgent:
    """Agent class to handle the agent execution."""

    def __init__(self):
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.agent_executor = self._init_agent_executor()

    def _init_agent_executor(self) -> AgentExecutor:
        prompt = PromptTemplate(
            template=PARALLEL_PROMPT_TEMPLATE,
        )
        llm = ChatOpenAI(temperature=0, model="gpt-4")
        output_parser = CustomOutputParser()

        agent = create_react_agent(
            llm=llm,
            tools=PARALLEL_TOOLS,
            prompt=prompt,
            output_parser=output_parser,
            stop_sequence=["\nObservation:"],
        )

        agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=PARALLEL_TOOLS, verbose=True)
        return agent_executor

    def invoke(self, user_input: str) -> str:
        """Invoke the agent with the user input."""
        # Add the user input to the memory
        self.memory.save_context({"input": user_input}, {})

        # Prepare the input with memory for the agent
        chat_history = self.memory.load_memory_variables({})["chat_history"]

        # Prepare the input with the history for the agent
        result = self.agent_executor.invoke({"input": user_input, "chat_history": chat_history})

        # Save the agent's response in memory
        self.memory.save_context({}, {"output": result["output"]})

        return result["output"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed entities in the Neo4j graph")
    parser.add_argument("--message", type=str, help="The message to send to the agent")
    parser.add_argument("--parallel", action="store_true", help="Whether to run the agent in parallel mode")
    args = parser.parse_args()

    agent_exe = ParallelAgent() if args.parallel else Agent()
    print(f"Using {'parallel' if args.parallel else 'sequential'} agent mode")
    print(f"\n\n--->Result: \n{agent_exe.invoke(args.message)}\n\n")
