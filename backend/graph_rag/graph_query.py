"""Script to generate Cypher queries based on user input and query a Neo4j graph database."""

from openai import OpenAIError

from backend.graph_rag.config import client, neo4j_graph

CYPHER_PROMPT = """
You are a helpful assistant that generates Cypher queries for a Neo4j graph database based on user input.

The database contains the following entities:
- Part (Attributes: `id`, `url`, `name`, `partselect_num`, `manufacturer_part_num`, `price`, `status`, `difficulty`, `repair_time`, `description`, `works_with_products`, `web_id`)
- Model (Attributes: `model_num`, `name`, `url`)
- Symptom (Attribute: `name`)
- Brand (Attribute: `name`)
- ProductType (Attribute: `name`)
- Video (Attributes: `url`, `name`)
- Story (Attributes: `title`, `content`, `difficulty`, `repair_time`, `tools`)
- QnA (Attributes: `question`, `model`, `answer`, `date`)
- Section (Attributes: `name`, `url`)
- Manual (Attributes: `name`, `url`)
- InstallationInstruction (Attributes: `title`, `content`, `difficulty`, `repair_time`, `tools`)

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
            matche = {}
            if "id" in entity_data:
                matche["id"] = entity_data["id"]
            if "name" in entity_data:
                matche["name"] = entity_data["name"]
            if "description" in entity_data:
                matche["description"] = entity_data["description"]
            if "url" in entity_data:
                matche["url"] = entity_data["url"]
            if "price" in entity_data:
                matche["price"] = entity_data["price"]
            if "status" in entity_data:
                matche["status"] = entity_data["status"]
            if "difficulty" in entity_data:
                matche["difficulty"] = entity_data["difficulty"]
            if "repair_time" in entity_data:
                matche["repair_time"] = entity_data["repair_time"]
            if "works_with_products" in entity_data:
                matche["works_with_products"] = entity_data["works_with_products"]
            if "web_id" in entity_data:
                matche["web_id"] = entity_data["web_id"]
            if "model_num" in entity_data:
                matche["model_num"] = entity_data["model_num"]
            if "partselect_num" in entity_data:
                matche["partselect_num"] = entity_data["partselect_num"]
            if "manufacturer_part_num" in entity_data:
                matche["manufacturer_part_num"] = entity_data["manufacturer_part_num"]
            if "content" in entity_data:
                matche["content"] = entity_data["content"]
            if "tools" in entity_data:
                matche["tools"] = entity_data["tools"]
            if "question" in entity_data:
                matche["question"] = entity_data["question"]
            if "answer" in entity_data:
                matche["answer"] = entity_data["answer"]
            if "date" in entity_data:
                matche["date"] = entity_data["date"]

            matches.append(matche)
    return matches


if __name__ == "__main__":

    USER_QUERY = "Which parts are compatible with the FPHD2491KF0 Frigidaire Dishwasher?"
    print(query_db(USER_QUERY))
