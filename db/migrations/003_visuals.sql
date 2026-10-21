CREATE TABLE knowledge_documents (
 document_id text PRIMARY KEY, source_url text NOT NULL, revision text NOT NULL, sha256 char(64) NOT NULL,
 rights_note text NOT NULL, type text NOT NULL, applicability jsonb NOT NULL DEFAULT '{}', approval_status text NOT NULL
);
CREATE TABLE knowledge_passages (
 document_id text NOT NULL REFERENCES knowledge_documents(document_id), passage_id text NOT NULL,
 locators jsonb NOT NULL, exact_text text NOT NULL, PRIMARY KEY(document_id,passage_id)
);
CREATE TABLE components (
 component_id text PRIMARY KEY, parent_id text REFERENCES components(component_id), canonical_name text NOT NULL,
 synonyms jsonb NOT NULL DEFAULT '[]', knowledge_source_ids jsonb NOT NULL DEFAULT '[]', review_status text NOT NULL
);
CREATE TABLE visual_assets (
 asset_id text PRIMARY KEY, file_hash char(64) NOT NULL, license text NOT NULL, attribution text NOT NULL,
 applicability jsonb NOT NULL DEFAULT '{}', illustrative boolean NOT NULL DEFAULT true
);
CREATE TABLE visual_mappings (
 asset_id text NOT NULL REFERENCES visual_assets(asset_id), component_id text NOT NULL REFERENCES components(component_id),
 hotspot_id text NOT NULL, mapping_kind text NOT NULL, source text NOT NULL, reviewer text NOT NULL,
 PRIMARY KEY(asset_id,component_id,hotspot_id)
);
