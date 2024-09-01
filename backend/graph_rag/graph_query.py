"""Script to generate Cypher queries based on user input and query a Neo4j graph database."""

from openai import OpenAIError

from backend.graph_rag.config import client, neo4j_graph

CYPHER_PROMPT = """
You are a helpful assistant that generates Cypher queries for a Neo4j graph database based on user input.

The database contains the following entities:
- Part (Attributes: `id`, `url`, `name`, `partselect_num`, `manufacturer_part_num`, `price`, `status`, `installation_difficulty`, `installation_time`, `description`, `works_with_products`, `web_id`)
- Model (Attributes: `model_num`, `name`, `url`)
- Symptom (Attribute: `symptom_name`)
- Brand (Attribute: `name`)
- ProductType (Attribute: `name`)
- Video (Attributes: `youtube_link`, `video_title`)
- Story (Attributes: `title`, `content`, `difficulty`, `repair_time`, `tools`)
- QnA (Attributes: `question`, `model`, `answer`, `date`)
- RelatedPart (Attributes: `id`, `name`, `price`, `status`, `link`)
- Section (Attributes: `name`, `link`)
- Manual (Attributes: `name`, `link`)
- InstallationInstruction (Attributes: `title`, `content`, `difficulty_level`, `total_repair_time`, `tools`)

The entities are connected by the following relationships:
- MANUFACTURED_BY: `(:Part)-[:MANUFACTURED_BY]->(:Manufacturer)`
- BRAND_DESTINATION: `(:Part)-[:BRAND_DESTINATION]->(:Brand)`
- COMPATIBLE_WITH: `(:Part)-[:COMPATIBLE_WITH]->(:Model)`
- HAS_VIDEO: `(:Part)-[:HAS_VIDEO]->(:Video)`
- FIXES_SYMPTOM: `(:Part)-[:FIXES_SYMPTOM]->(:Symptom)`
- HAS_STORY: `(:Part)-[:HAS_STORY]->(:Story)`
- HAS_QNA: `(:Part)-[:HAS_QNA]->(:QnA)`
- RELATED_TO: `(:Part)-[:RELATED_TO]->(:Part)`
- REPLACES: `(:Part)-[:REPLACES]->(:Part)`
- WORKS_WITH_PRODUCT_TYPE: `(:Part)-[:WORKS_WITH_PRODUCT_TYPE]->(:ProductType)`
- HAS_SECTION: `(:Model)-[:HAS_SECTION]->(:Section)`
- HAS_MANUAL: `(:Model)-[:HAS_MANUAL]->(:Manual)`
- MADE_BY: `(:Model)-[:MADE_BY]->(:Brand)`
- IS: `(:Model)-[:IS]->(:ProductType)`
- HAS_PART: `(:Model)-[:HAS_PART]->(:Part)`
- HAS_INSTALLATION_INSTRUCTION: `(:Model)-[:HAS_INSTALLATION_INSTRUCTION]->(:InstallationInstruction)`
- HAS_SYMPTOM: `(:Model)-[:HAS_SYMPTOM]->(:Symptom)`
- REFERENCES_PART: `(:QnA)-[:REFERENCES_PART]->(:Part)`
- FEATURES_PART: `(:Video)-[:FEATURES_PART]->(:Part)`
- USES_PART: `(:InstallationInstruction)-[:USES_PART]->(:Part)`
- USES_FIXING_PART: `(:Symptom)-[:USES_FIXING_PART]->(:Part)`

Your task is to generate a Cypher query based on the user's input. Do not include any comments or explanations in the Cypher query. 

Limit the number of results returned to 10.

The final output should be in the dictionary format:
{
    "cypher": <cypher query>,
}
"""

CORRECT_PROMPT = """
You are a Neo4j Cypher expert. Please check the following Cypher query for any syntax or logical errors. If there are any issues, correct them and return the corrected query. If there are no issues, return the original query. Please return only the Cypher query.
"""


def generate_cypher_query(user_input: str, model: str = "gpt-4"):
    """Function to generate a Cypher query based on user input using OpenAI's API."""
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[{"role": "system", "content": CYPHER_PROMPT}, {"role": "user", "content": user_input}],
        )
    except OpenAIError as e:
        print(f"An error occurred with the OpenAI API: {e}")
        return user_input
    return response.choices[0].message.content


def correct_cypher_query(query: str, model: str = "gpt-4o") -> str:
    """Function to use OpenAI's API to correct a Cypher query if needed."""
    # Prompt to send to OpenAI for Cypher query correction
    try:
        # Generate the correction using OpenAI
        response = client.chat.completions.create(model=model, temperature=0, messages=[{"role": "system", "content": CORRECT_PROMPT}, {"role": "user", "content": query}])

        # Return the corrected query
        return response.choices[0].message.content

    except OpenAIError as e:
        print(f"An error occurred with the OpenAI API: {e}")
        return query  # Return the original query if there's an error

    # Function to query the Neo4j graph


def query_graph(user_input: str, threshold: float = 0.8):
    """Function to query the Neo4j graph database based on user input."""
    query = generate_cypher_query(user_input)

    reviewed_query = correct_cypher_query(query)

    while True:
        try:  # Attempt to query the graph
            result = neo4j_graph.query(reviewed_query, params={"threshold": threshold})
            break
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"An error occurred with the Neo4j graph query: {e}")
    return result


def query_db(query: str) -> list:
    """Function to query the Neo4j graph database based on user input."""
    matches = []
    result = query_graph(query)
    for r in result:
        for _, value in r.items():
            entity_data = value
            matches.append(
                {
                    "id": entity_data.get('id', 'Unknown ID'),
                    "name": entity_data.get('name', 'Unnamed Entity'),
                }
            )
    return matches


if __name__ == "__main__":

    USER_QUERY = "Which parts are compatible with the FPHD2491KF0 Frigidaire Dishwasher?"
    print(query_db(USER_QUERY))
