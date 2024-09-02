"""Configuration file for the backend application."""

import os
import logging

from openai import OpenAI
from langchain_community.graphs import Neo4jGraph

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

EMBEDDINGS_MODEL = "text-embedding-3-small"


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

neo4j_graph = Neo4jGraph(
    url=os.environ.get("NEO4J_CURRENT_URI"),
    username=os.environ.get("NEO4J_CURRENT_USERNAME"),
    password=os.environ.get("NEO4J_CURRENT_PASSWORD"),
)

ENTITY_TYPES = {
    "part": "The specific part or component of a product, for example 'Silverware Basket', 'Detergent Dispenser'",
    "model": "The model number or name, for example 'FPHD2491KF0', 'Dishwasher Model XYZ'",
    "symptom": "The issue or symptom associated with a part or model, for example 'Leaking', 'Not cleaning dishes properly'",
    "brand": "The brand associated with the part or model, for example 'Frigidaire', 'Kenmore'",
    "product_type": "The type of product, for example 'Dishwasher', 'Refrigerator'",
    "video": "The title of a video related to the part or model, for example 'Replacing the Silverware Basket'",
    "installation_instruction": "Instructions for installing a part, for example 'Install Silverware Basket', 'Replace Detergent Dispenser'",
    "story": "A user story or repair story related to a part or model",
    "qna": "Questions and answers related to a part or model",
}

RELATION_TYPES = {
    "MANUFACTURED_BY": "A part is manufactured by a specific manufacturer",
    "BRAND_DESTINATION": "A part is related to a specific brand",
    "COMPATIBLE_WITH": "A part is compatible with a specific model",
    "HAS_VIDEO": "A part or model is associated with a specific video",
    "FIXES_SYMPTOM": "A part fixes a specific symptom",
    "HAS_STORY": "A part or model has a related story",
    "HAS_QNA": "A part or model has related Q&A",
    "RELATED_TO": "A part is related to another part",
    "REPLACES": "A part replaces another part",
    "WORKS_WITH_PRODUCT_TYPE": "A part works with a specific product type",
    "HAS_SECTION": "A model has specific sections",
    "HAS_MANUAL": "A model has a specific manual",
    "MADE_BY": "A model or part is made by a specific brand",
    "IS": "A model is of a specific product type",
    "HAS_PART": "A model has specific parts",
    "HAS_INSTALLATION_INSTRUCTION": "A model or part has related installation instructions",
    "HAS_SYMPTOM": "A model has related symptoms",
    "REFERENCES_PART": "A Q&A references a specific part",
    "FEATURES_PART": "A video features a specific part",
    "USES_PART": "Installation instructions use specific parts",
    "USES_FIXING_PART": "A symptom can be fixed using a specific part",
}

ENTITY_RELATIONSHIP_MATCH = {
    "part": ["HAS_PART"],
    "model": ["HAS_PART"],
    "symptom": ["HAS_SYMPTOM", "FIXES_SYMPTOM"],
    "brand": ["BRAND_DESTINATION", "MANUFACTURED_BY", "MADE_BY"],
    "product_type": ["WORKS_WITH_PRODUCT_TYPE", "IS"],
    "video": ["HAS_VIDEO", "FEATURES_PART"],
    "installation_instruction": ["HAS_INSTALLATION_INSTRUCTION", "USES_PART"],
    "story": ["HAS_STORY"],
    "qna": ["HAS_QNA", "REFERENCES_PART"],
}
