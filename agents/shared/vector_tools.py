
import os
from typing import List, Dict, Any, Optional
from loguru import logger
import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform

# Initialize Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")

if PROJECT_ID:
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        logger.warning(f"Failed to initialize Vertex AI: {e}")

# Global models
_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise e
    return _embedding_model

def get_embedding(text: str) -> List[float]:
    """Generates vector embedding for the given text."""
    try:
        model = _get_embedding_model()
        embeddings = model.get_embeddings([text])
        return embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}")
        return []

def search_knowledge_base(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the Knowledge Base (Vector Store) for relevant negotiation tactics.
    
    Args:
        query: The search query (e.g., "how to handle stubborn driver").
        limit: Number of results to return.
        
    Returns:
        List of matched documents with metadata.
    """
    index_endpoint_id = os.getenv("VECTOR_INDEX_ENDPOINT_ID")
    deployed_index_id = os.getenv("VECTOR_DEPLOYED_INDEX_ID")
    
    if not index_endpoint_id or not deployed_index_id:
        logger.warning("⚠️ Vector Search not configured. Using mock results.")
        logger.warning("   Set VECTOR_INDEX_ENDPOINT_ID and VECTOR_DEPLOYED_INDEX_ID to use real search")
        return _mock_search(query)

    try:
        # Get query embedding
        query_embedding = get_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return _mock_search(query)
        
        # Connect to index endpoint
        endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=index_endpoint_id
        )
        
        # Perform vector search
        logger.info(f"🔍 Searching Vector Index for: '{query[:50]}...'")
        
        response = endpoint.find_neighbors(
            deployed_index_id=deployed_index_id,
            queries=[query_embedding],
            num_neighbors=limit,
        )
        
        # Parse results
        results = []
        if response and len(response) > 0:
            neighbors = response[0]
            
            for neighbor in neighbors:
                # Extract metadata
                metadata = neighbor.id  # The ID we stored
                distance = neighbor.distance
                
                # Reconstruct result object
                result = {
                    "id": metadata,
                    "distance": distance,
                    "score": 1 / (1 + distance),  # Convert distance to similarity score
                }
                
                # In production, metadata would contain the full tactic text
                # For now, we'll need to fetch it from Firestore or store it during indexing
                
                results.append(result)
            
            logger.info(f"✅ Found {len(results)} relevant tactics")
        else:
            logger.warning("No results found, using fallback")
            return _mock_search(query)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Vector search failed: {e}")
        logger.warning("Falling back to mock search")
        return _mock_search(query)

def _mock_search(query: str) -> List[Dict[str, Any]]:
    """Temporary mock search until Vector Search is fully provisioned."""
    logger.info(f"🔍 Mock searching for: {query}")
    
    # Simple keyword matching for demo
    tactics = [
        {
            "id": "tactic_001",
            "text": "If vendor is stubborn, mention 'market rate' and offer to book immediately.",
            "category": "stubborn_vendor"
        },
        {
            "id": "tactic_002",
            "text": "For long trips, emphasize 'return fare' is included or not applicable.",
            "category": "long_distance"
        },
        {
            "id": "tactic_003",
            "text": "Use 'DesiYatra corporate partner' status to build trust.",
            "category": "trust_building"
        }
    ]
    
    return [t for t in tactics if any(word in t['text'].lower() for word in query.lower().split())] or tactics[:1]

def add_tactic_to_kb(text: str, category: str) -> str:
    """
    Adds a new tactic to the knowledge base.
    In production, this would upload the embedding to the Vector Index.
    """
    embedding = get_embedding(text)
    if not embedding:
        return "❌ Failed to generate embedding"
        
    # TODO: Upload to Vector Search Index
    logger.info(f"Generated embedding for: {text[:30]}...")
    return "✅ Tactic added to indexing queue (simulated)"
