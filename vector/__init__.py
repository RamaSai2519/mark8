import numpy as np
from client import ADA_Client
from config import call_prompts_collection, transcripts_collection, constants_collection


class Embedder:
    def __init__(self) -> None:
        self.collection = call_prompts_collection
        self.ada_client = ADA_Client().get_ada_client()

    def compute_embedding(self, text: str) -> list:
        response = self.ada_client.embeddings.create(
            model="text-embedding-ada-002", input=text)
        return response.data[0].embedding

    def store_embedding(self, prompt: str, embedding: list, response) -> None:
        document = {"embedding": embedding, "prompt": prompt}
        document['response'] = response
        self.collection.insert_one(document)

    def get_most_similar_prompt(self, embedding: list, prompt: str) -> dict:
        query = {"prompt": prompt}
        all_embeddings = list(self.collection.find(query))
        if not all_embeddings:
            return None

        similarities = []
        for entry in all_embeddings:
            stored_embedding = entry['embedding']
            similarity = np.dot(embedding, stored_embedding) / \
                (np.linalg.norm(embedding) * np.linalg.norm(stored_embedding))
            similarities.append((entry, similarity))

        most_similar = max(
            similarities, key=lambda x: x[1]) if similarities else None
        return most_similar[0] if most_similar and most_similar[1] > 0.97 else None

    def store_transcript_embedding(self, embedding: list, transcript: str) -> dict:
        transcript_hash = hash(transcript)
        doc = {"hash": transcript_hash}
        doc["embedding"] = embedding
        result = transcripts_collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def store_prompt_embedding(self, embedding: list, prompt: str) -> dict:
        doc = {"prompt": prompt}
        doc["embedding"] = embedding
        result = constants_collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def get_transcript_embedding(self, transcript: str) -> list:
        transcript_hash = hash(transcript)
        query = {"hash": transcript_hash}
        doc: dict = transcripts_collection.find_one(query)
        if doc and "embedding" in doc:
            return doc.get("embedding")
        embedding = self.compute_embedding(transcript)
        self.store_transcript_embedding(embedding, transcript)
        return embedding

    def get_prompt_embedding(self, prompt: str) -> list:
        query = {"prompt": prompt}
        doc: dict = constants_collection.find_one(query)
        if doc and "embedding" in doc:
            return doc.get("embedding")
        embedding = self.compute_embedding(prompt)
        self.store_prompt_embedding(embedding, prompt)
        return embedding
