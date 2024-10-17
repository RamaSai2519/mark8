import hashlib
import numpy as np
from pymongo.collection import Collection
from openai import AzureOpenAI

class Embedder:
    def __init__(self, ada_client: AzureOpenAI) -> None:
        self.ada_client = ada_client

    def generate_embedding(self, text: str) -> list:
        """Generates an embedding for the given text using the ADA model."""
        response = self.ada_client.embeddings.create(model="ada-002", input=text)
        return response['data'][0]['embedding']

    def store_embedding(self, collection: Collection, embedding: list, doc: dict) -> None:
        """Stores the embedding in the specified collection along with the related document."""
        collection.insert_one({
            "embedding": embedding,
            "data": doc
        })

    def get_similar_embedding(self, collection: Collection, query_embedding: list, threshold=0.85) -> dict | None:
        """Retrieves a document from the collection that has an embedding similar to the query embedding."""
        # This is a simple placeholder method that retrieves documents based on a text search.
        # In practice, you should use cosine similarity or vector-based search optimized for embeddings.

        all_docs = collection.find()
        for doc in all_docs:
            stored_embedding = doc.get('embedding')
            if stored_embedding:
                similarity = self.calculate_cosine_similarity(
                    query_embedding, stored_embedding)
                if similarity >= threshold:
                    return doc["data"]
        return None

    def calculate_cosine_similarity(self, embedding1: list, embedding2: list) -> float:
        """Calculates cosine similarity between two embeddings."""
        # Convert lists to numpy arrays for cosine similarity computation
        embedding1 = np.array(embedding1)
        embedding2 = np.array(embedding2)

        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        return dot_product / (norm1 * norm2)

    def combine_embeddings(self, embedding1: list, embedding2: list) -> list:
        """Combines two embeddings into a single embedding by averaging them."""
        combined_embedding = np.mean([embedding1, embedding2], axis=0)
        return combined_embedding.tolist()

    def generate_transcript_hash(self, transcript: str) -> str:
        """Generates a unique hash for the given transcript."""
        return hashlib.sha256(transcript.encode()).hexdigest()