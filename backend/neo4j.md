## Entities

- **Part** (Attributes: `id`, `url`, `name`, `partselect_num`, `manufacturer_part_num`, `price`, `status`, `installation_difficulty`, `installation_time`, `description`, `works_with_products`)
- **Manufacturer** (Attribute: `name`)
- **Brand** (Attribute: `name`)
- **ProductType** (Attribute: `name`)
- **Model** (Attributes: `model_num`, `name`, `url`)
- **Video** (Attributes: `youtube_link`, `video_title`)
- **Symptom** (Attribute: `symptom_name`)
- **Story** (Attributes: `title`, `content`, `difficulty`, `repair_time`, `tools`)
- **QnA** (Attributes: `question`, `model`, `answer`, `date`)
- **RelatedPart** (Attributes: `id`, `name`, `price`, `status`, `link`)
- **Section** (Attributes: `name`, `link`)
- **Manual** (Attributes: `name`, `link`)
- **InstallationInstruction** (Attributes: `title`, `content`, `difficulty_level`, `total_repair_time`, `tools`)

## Relationships

- **MANUFACTURED_BY**: `(:Part)-[:MANUFACTURED_BY]->(:Manufacturer)`
- **BRAND_DESTINATION**: `(:Part)-[:BRAND_DESTINATION]->(:Brand)`
- **COMPATIBLE_WITH**: `(:Part)-[:COMPATIBLE_WITH]->(:Model)`
- **HAS_VIDEO**: `(:Part)-[:HAS_VIDEO]->(:Video)`
- **FIXES_SYMPTOM**: `(:Part)-[:FIXES_SYMPTOM]->(:Symptom)`
- **HAS_STORY**: `(:Part)-[:HAS_STORY]->(:Story)`
- **HAS_QNA**: `(:Part)-[:HAS_QNA]->(:QnA)`
- **RELATED_TO**: `(:Part)-[:RELATED_TO]->(:Part)`
- **REPLACES**: `(:Part)-[:REPLACES]->(:Part)`
- **WORKS_WITH_PRODUCT_TYPE**: `(:Part)-[:WORKS_WITH_PRODUCT_TYPE]->(:ProductType)`

- **HAS_SECTION**: `(:Model)-[:HAS_SECTION]->(:Section)`
- **HAS_MANUAL**: `(:Model)-[:HAS_MANUAL]->(:Manual)`
- **MADE_BY**: `(:Model)-[:MADE_BY]->(:Brand)`
- **IS**: `(:Model)-[:IS]->(:ProductType)`
- **HAS_PART**: `(:Model)-[:HAS_PART]->(:Part)`
- **HAS_QNA**: `(:Model)-[:HAS_QNA]->(:QnA)`
- **HAS_VIDEO**: `(:Model)-[:HAS_VIDEO]->(:Video)`
- **HAS_INSTALLATION_INSTRUCTION**: `(:Model)-[:HAS_INSTALLATION_INSTRUCTION]->(:InstallationInstruction)`
- **HAS_SYMPTOM**: `(:Model)-[:HAS_SYMPTOM]->(:Symptom)`

- **REFERENCES_PART**: `(:QnA)-[:REFERENCES_PART]->(:Part)`

- **FEATURES_PART**: `(:Video)-[:FEATURES_PART]->(:Part)`

- **USES_PART**: `(:InstallationInstruction)-[:USES_PART]->(:Part)`

- **USES_FIXING_PART**: `(:Symptom)-[:USES_FIXING_PART]->(:Part)`
