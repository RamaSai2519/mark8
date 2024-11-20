import tiktoken
import numpy as np
from client import ADA_Client
from config import call_prompts_collection, transcripts_collection, constants_collection


class Embedder:
    def __init__(self) -> None:
        self.token_limit = 8192
        self.collection = call_prompts_collection
        self.ada_client = ADA_Client().get_ada_client()
        self.tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")

    def count_tokens(self, text: str) -> int:
        tokens = self.tokenizer.encode(text)
        return len(tokens)

    def split_text(self, text: str, max_tokens: int = 7500) -> list:
        words = text.split()
        chunks = []
        current_chunk = []

        for word in words:
            current_chunk.append(word)
            token_count = self.count_tokens(' '.join(current_chunk))
            if token_count > max_tokens:
                chunks.append(' '.join(current_chunk[:-1]))
                current_chunk = [word]

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def compute_embedding(self, text: str) -> list:
        token_count = self.count_tokens(text)
        if token_count > self.token_limit:
            raise ValueError(f"Limit crossed: {token_count} tokens")

        response = self.ada_client.embeddings.create(
            model="text-embedding-ada-002", input=text)
        return response.data[0].embedding

    def compute_transcript_embedding(self, transcript: str) -> list:
        token_count = self.count_tokens(transcript)
        if token_count > self.token_limit:
            chunks = self.split_text(transcript)
            embeddings = []
            for chunk in chunks:
                embedding = self.compute_embedding(chunk)
                embeddings.append(embedding)

            combined_embedding = np.mean(embeddings, axis=0).tolist()
            return combined_embedding
        else:
            return self.compute_embedding(transcript)

    def store_transcript_embedding(self, embedding: list, transcript: str) -> dict:
        transcript_hash = hash(transcript)
        doc = {"hash": transcript_hash}
        doc["embedding"] = embedding
        result = transcripts_collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def get_transcript_embedding(self, transcript: str) -> list:
        transcript_hash = hash(transcript)
        query = {"hash": transcript_hash}
        doc: dict = transcripts_collection.find_one(query)
        if doc and "embedding" in doc:
            return doc.get("embedding")

        embedding = self.compute_transcript_embedding(transcript)
        self.store_transcript_embedding(embedding, transcript)
        return embedding

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
        print(most_similar[1])
        return most_similar[0] if most_similar and most_similar[1] > 0.98 else None

    def store_prompt_embedding(self, embedding: list, prompt: str) -> dict:
        doc = {"prompt": prompt}
        doc["embedding"] = embedding
        result = constants_collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def get_prompt_embedding(self, prompt: str) -> list:
        query = {"prompt": prompt}
        doc: dict = constants_collection.find_one(query)
        if doc and "embedding" in doc:
            return doc.get("embedding")
        embedding = self.compute_embedding(prompt)
        self.store_prompt_embedding(embedding, prompt)
        return embedding
