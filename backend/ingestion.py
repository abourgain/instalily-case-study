"""This script loads part and model data into the Neo4j database."""

import argparse
import json
import os
from py2neo import Graph, Node, Relationship

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


# Connect to Neo4j
graph = Graph(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))


def load_part_data(part_data: dict):  # pylint: disable=too-many-branches
    """Load part data into the Neo4j database."""
    part = Node(
        "Part",
        id=part_data['id'],
        url=part_data['url'],
        name=part_data['name'],
        partselect_num=part_data['partselect_num'],
        manufacturer_part_num=part_data['manufacturer_part_num'],
        price=part_data['price'] if 'price' in part_data else None,
        status=part_data['status'] if 'status' in part_data else None,
        installation_difficulty=part_data['installation_difficulty'] if 'installation_difficulty' in part_data else None,
        installation_time=part_data['installation_time'] if 'installation_time' in part_data else None,
        description=part_data['description'] if 'description' in part_data else None,
    )
    graph.merge(part, "Part", "id")

    # Create Manufacturer node and relationship
    manufacturer = Node("Manufacturer", name=part_data['manufacturer'])
    graph.merge(manufacturer, "Manufacturer", "name")
    graph.merge(Relationship(part, "MANUFACTURED_BY", manufacturer))

    # Create Brand nodes and relationships
    for brand_name in part_data['brand_destination']:
        if brand_name:
            brand = Node("Brand", name=brand_name)
            graph.merge(brand, "Brand", "name")
            graph.merge(Relationship(part, "BRAND_DESTINATION", brand))

    # Handle Compatible Models
    if "compatible_models" in part_data:
        for model in part_data["compatible_models"]:
            model_node = Node("Model", model_num=model['model_num'], name=model['description'])
            graph.merge(model_node, "Model", "model_num")
            graph.merge(Relationship(part, "COMPATIBLE_WITH", model_node))

    # Handle Videos
    if "videos" in part_data:
        for video in part_data['videos']:
            video_node = Node("Video", youtube_link=video['youtube_link'], video_title=video['video_title'])
            graph.merge(video_node, "Video", "youtube_link")
            graph.merge(Relationship(part, "HAS_VIDEO", video_node))

    # Handle Symptoms
    if "troubleshooting" in part_data and "symptoms_fixed" in part_data['troubleshooting']:
        for symptom_name in part_data['troubleshooting']['symptoms_fixed']:
            symptom_node = Node("Symptom", symptom_name=symptom_name)
            graph.merge(symptom_node, "Symptom", "symptom_name")
            graph.merge(Relationship(part, "FIXES_SYMPTOM", symptom_node))

    # Handle Stories
    if "repair_stories" in part_data:
        for story in part_data['repair_stories']:
            story_node = Node("Story", title=story['title'], content=story['content'], difficulty=story['difficulty'], repair_time=story['repair_time'], tools=story.get('tools', ''))
            graph.merge(story_node, "Story", "title")
            graph.merge(Relationship(part, "HAS_STORY", story_node))

    # Handle QnAs
    if "qnas" in part_data:
        for qna in part_data['qnas']:
            qna_node = Node("QnA", question=qna['question'], model=qna['model'], answer=qna['answer'], date=qna['date'])
            graph.merge(qna_node, "QnA", "question")
            graph.merge(Relationship(part, "HAS_QNA", qna_node))

            # Handle REFERENCES_PART relationship
            if "related_parts" in qna:
                for related_part in qna['related_parts']:
                    part_node = graph.evaluate(f"MATCH (p:Part {{id: '{related_part['part_id']}'}}) RETURN p")
                    if part_node:
                        graph.merge(Relationship(qna_node, "REFERENCES_PART", part_node))

    # Handle Related Parts
    if "related_parts" in part_data:
        for related_part in part_data['related_parts']:
            related_part_node = Node("Part", id=related_part['id'], name=related_part['name'], price=related_part['price'], status=related_part['status'], link=related_part['link'])
            graph.merge(related_part_node, "Part", "id")
            graph.merge(Relationship(part, "RELATED_TO", related_part_node))

    # Handle Part Replacements
    if "troubleshooting" in part_data and "replaces_manufacturer_part_nums" in part_data['troubleshooting']:
        for replacement_num in part_data['troubleshooting']['replaces_manufacturer_part_nums']:
            query = f"MATCH (p:Part {{manufacturer_part_num: '{replacement_num}'}}) RETURN p"
            replaced_part = graph.evaluate(query)
            if replaced_part:
                graph.merge(Relationship(part, "REPLACES", replaced_part))

    # Handle WORKS_WITH_PRODUCT_TYPE relationship
    if "troubleshooting" in part_data and "works_with_products" in part_data["troubleshooting"]:
        for product_type_name in part_data["troubleshooting"]['works_with_products']:
            if product_type_name:
                product_type_node = Node("ProductType", name=product_type_name)
                graph.merge(product_type_node, "ProductType", "name")
                graph.merge(Relationship(part, "WORKS_WITH_PRODUCT_TYPE", product_type_node))


def load_model_data(model_data: dict):  # pylint: disable=too-many-branches, too-many-statements
    """Load model data into the Neo4j database."""
    model = Node(
        "Model",
        model_num=model_data['model_num'],
        name=model_data['name'],
        url=model_data['url'],
    )
    graph.merge(model, "Model", "model_num")

    # Create Brand node and relationship
    brand = Node("Brand", name=model_data['brand'])
    graph.merge(brand, "Brand", "name")
    graph.merge(Relationship(model, "MADE_BY", brand))

    # Create ProductType node and relationship
    product_type = Node("ProductType", name=model_data['model_type'])
    graph.merge(product_type, "ProductType", "name")
    graph.merge(Relationship(model, "IS", product_type))

    # Handle Sections
    if "sections" in model_data:
        for section in model_data['sections']:
            section_node = Node("Section", name=section['name'], link=section['link'])
            graph.merge(section_node, "Section", "name")
            graph.merge(Relationship(model, "HAS_SECTION", section_node))

    # Handle Manuals
    if "manuals" in model_data:
        for manual in model_data['manuals']:
            manual_node = Node("Manual", name=manual['name'], link=manual['link'])
            graph.merge(manual_node, "Manual", "name")
            graph.merge(Relationship(model, "HAS_MANUAL", manual_node))

    # Handle Parts
    if "parts" in model_data:
        for part in model_data['parts']:
            part_node = Node("Part", id=part['id'], name=part['name'], price=part['price'], status=part['status'])
            graph.merge(part_node, "Part", "id")
            graph.merge(Relationship(model, "HAS_PART", part_node))

    # Handle QnAs
    if "qnas" in model_data:
        for qna in model_data['qnas']:
            qna_node = Node("QnA", question=qna['question'], answer=qna['answer'], date=qna['date'])
            graph.merge(qna_node, "QnA", "question")
            graph.merge(Relationship(model, "HAS_QNA", qna_node))

            # Handle REFERENCES_PART relationship
            if "related_parts" in qna:
                for related_part in qna['related_parts']:
                    part_node = graph.evaluate(f"MATCH (p:Part {{id: '{related_part['id']}'}}) RETURN p")
                    if part_node:
                        graph.merge(Relationship(qna_node, "REFERENCES_PART", part_node))

    # Handle Videos
    if "videos" in model_data:
        for video in model_data['videos']:
            video_node = Node("Video", youtube_link=video['youtube_link'], video_title=video['video_title'])
            graph.merge(video_node, "Video", "youtube_link")
            graph.merge(Relationship(model, "HAS_VIDEO", video_node))
            # Link video to parts
            if "parts" in video:
                for part in video['parts']:
                    part_node = graph.evaluate(f"MATCH (p:Part {{id: '{part['id']}'}}) RETURN p")
                    if part_node:
                        graph.merge(Relationship(video_node, "FEATURES_PART", part_node))

    # Handle Installation Instructions
    if "installation_instructions" in model_data:
        for instruction in model_data['installation_instructions']:
            instruction_node = Node(
                "InstallationInstruction",
                title=instruction['title'],
                content=instruction['content'],
                difficulty_level=instruction['difficulty_level'],
                total_repair_time=instruction['total_repair_time'],
                tools=instruction['tools'],
            )
            graph.merge(instruction_node, "InstallationInstruction", "title")
            graph.merge(Relationship(model, "HAS_INSTALLATION_INSTRUCTION", instruction_node))
            # Link installation instruction to parts
            if "parts_used" in instruction:
                for part in instruction['parts_used']:
                    part_node = graph.evaluate(f"MATCH (p:Part {{id: '{part['id']}'}}) RETURN p")
                    if part_node:
                        graph.merge(Relationship(instruction_node, "USES_PART", part_node))

    # Handle Symptoms
    if "common_symptoms" in model_data:
        for symptom in model_data['common_symptoms']:
            symptom_node = Node("Symptom", symptom_name=symptom['symptom_name'])
            graph.merge(symptom_node, "Symptom", "symptom_name")
            graph.merge(Relationship(model, "HAS_SYMPTOM", symptom_node))
            # Link symptom to fixing parts
            if "fixing_parts" in symptom:
                for fixing_part in symptom['fixing_parts']:
                    part_node = graph.evaluate(f"MATCH (p:Part {{id: '{fixing_part['id']}'}}) RETURN p")
                    if part_node:
                        graph.merge(Relationship(symptom_node, "USES_FIXING_PART", part_node))


def main(collection: str = None):
    """Load part and model data into the Neo4j database."""

    parts_dir = f"./backend/scraper/data/parts.{collection}" if collection else "./backend/scraper/data/parts"
    models_dir = f"./backend/scraper/data/models.{collection}" if collection else "./backend/scraper/data/models"

    for part_file in tqdm(os.listdir(parts_dir), desc="Uploading part data to Neo4j"):
        if part_file.endswith(".json"):
            with open(os.path.join(parts_dir, part_file), "r", encoding="utf-8") as part_file:
                part_data = json.load(part_file)
                load_part_data(part_data)

    for model_file in tqdm(os.listdir(models_dir), desc="Uploading model data to Neo4j"):
        if model_file.endswith(".json"):
            with open(os.path.join(models_dir, model_file), "r", encoding="utf-8") as model_file:
                model_data = json.load(model_file)
                load_model_data(model_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load part and model data into the Neo4j database.")
    parser.add_argument("--collection", type=str, help="Specify the collection of data to load.")
    args = parser.parse_args()

    main(args.collection)
