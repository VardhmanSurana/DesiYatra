"""
Vertex AI Vector Search Setup Script

Deploys a Vector Search index endpoint for the negotiation knowledge base.

Prerequisites:
- GOOGLE_CLOUD_PROJECT environment variable set
- gcloud auth configured
- Vertex AI API enabled

Run: python scripts/setup_vector_search.py
"""
import os
import time
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
from loguru import logger

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")
INDEX_DISPLAY_NAME = "desiyatra-negotiation-tactics"
ENDPOINT_DISPLAY_NAME = "desiyatra-kb-endpoint"
DEPLOYED_INDEX_ID = "desiyatra_tactics_deployed"

# Initialize
aiplatform.init(project=PROJECT_ID, location=LOCATION)


def create_vector_index():
    """
    Create a Vector Search index.
    
    This creates an empty index that we'll populate with negotiation tactics.
    """
    logger.info("📦 Creating Vector Search index...")
    
    try:
        index = MatchingEngineIndex.create_tree_ah_index(
            display_name=INDEX_DISPLAY_NAME,
            dimensions=768,  # text-embedding-004 produces 768-dimensional vectors
            approximate_neighbors_count=10,
            distance_measure_type="DOT_PRODUCT_DISTANCE",
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=10,
            description="Negotiation tactics and objection handlers for DesiYatra",
            labels={"app": "desiyatra", "type": "knowledge_base"},
        )
        
        logger.info(f"✅ Index created: {index.resource_name}")
        logger.info(f"   Index ID: {index.name}")
        
        return index.resource_name
        
    except Exception as e:
        logger.error(f"❌ Failed to create index: {e}")
        raise


def create_index_endpoint():
    """
    Create an Index Endpoint for serving queries.
    """
    logger.info("🚀 Creating Index Endpoint...")
    
    try:
        endpoint = MatchingEngineIndexEndpoint.create(
            display_name=ENDPOINT_DISPLAY_NAME,
            description="Endpoint for DesiYatra negotiation knowledge base",
            public_endpoint_enabled=True,
            labels={"app": "desiyatra"},
        )
        
        logger.info(f"✅ Endpoint created: {endpoint.resource_name}")
        logger.info(f"   Endpoint ID: {endpoint.name}")
        
        return endpoint
        
    except Exception as e:
        logger.error(f"❌ Failed to create endpoint: {e}")
        raise


def deploy_index_to_endpoint(index_resource_name: str, endpoint):
    """
    Deploy the index to the endpoint.
    """
    logger.info("🔗 Deploying index to endpoint...")
    
    try:
        endpoint.deploy_index(
            index=index_resource_name,
            deployed_index_id=DEPLOYED_INDEX_ID,
            display_name="desiyatra-tactics-v1",
            machine_type="e2-standard-2",
            min_replica_count=1,
            max_replica_count=2,
        )
        
        logger.info("✅ Index deployed successfully!")
        logger.info(f"   Deployed Index ID: {DEPLOYED_INDEX_ID}")
        
    except Exception as e:
        logger.error(f"❌ Failed to deploy index: {e}")
        raise


def populate_initial_tactics(index_resource_name: str):
    """
    Populate the index with initial negotiation tactics.
    """
    from vertexai.language_models import TextEmbeddingModel
    import json
    
    logger.info("📝 Populating index with initial tactics...")
    
    # Initial knowledge base
    tactics = [
        {
            "id": "tactic_001",
            "text": "If vendor is stubborn and won't budge, mention the market rate authoritatively: 'भैया, मार्केट रेट तो ₹X ही चल रहा है। हम रेगुलर कस्टमर हैं।' Then offer to book immediately if they match it.",
            "category": "stubborn_vendor",
            "vendor_types": ["taxi", "hotel"],
        },
        {
            "id": "tactic_002",
            "text": "For long-distance trips, clarify return fare upfront: 'वापसी का किराया अलग से लेना है क्या?' This prevents last-minute price increases.",
            "category": "long_distance",
            "vendor_types": ["taxi"],
        },
        {
            "id": "tactic_003",
            "text": "Build trust by mentioning DesiYatra partnership: 'हम DesiYatra के साथ काम करते हैं, आपका रेटिंग अच्छा है इसलिए आपको कॉल किया।' This makes vendors cooperative.",
            "category": "trust_building",
            "vendor_types": ["taxi", "hotel", "homestay"],
        },
        {
            "id": "tactic_004",
            "text": "When vendor quotes very high (>20% above market), show surprise: 'अरे! ये तो बहुत ज्यादा है। हमने तो सुना था ₹X में हो जाता है।' Then pause for their response.",
            "category": "high_initial_quote",
            "vendor_types": ["taxi", "hotel"],
        },
        {
            "id": "tactic_005",
            "text": "For budget hotels/homestays, emphasize you only need basics: 'हमें बस सोने के लिए चाहिए, खाना बाहर खा लेंगे। क्लीन रूम और बाथरूम काफी है।' This justifies lower price.",
            "category": "budget_negotiation",
            "vendor_types": ["hotel", "homestay"],
        },
        {
            "id": "tactic_006",
            "text": "If vendor refuses and says 'nahi hoga', politely end: 'ठीक है भैया, कोई बात नहीं। धन्यवाद।' Don't waste time arguing. Move to next vendor.",
            "category": "rejection_handling",
            "vendor_types": ["taxi", "hotel", "homestay"],
        },
        {
            "id": "tactic_007",
            "text": "For group bookings, leverage group discount: 'हम {party_size} लोग हैं, ग्रुप रेट में कुछ डिस्काउंट मिलेगा?' Vendors often reduce per-person cost.",
            "category": "group_discount",
            "vendor_types": ["hotel", "restaurant", "activity"],
        },
        {
            "id": "tactic_008",
            "text": "When vendor is flexible but hesitant, add urgency: 'हमें कल सुबह चलना है, अभी बुक कर लेते हैं तो confirm हो जाए।' Creates FOMO.",
            "category": "closing_tactic",
            "vendor_types": ["taxi", "hotel"],
        },
    ]
    
    # Generate embeddings
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    # Format data for upload
    datapoints = []
    for tactic in tactics:
        embedding = model.get_embeddings([tactic["text"]])[0].values
        
        datapoint = {
            "id": tactic["id"],
            "embedding": embedding,
            "metadata": {
                "text": tactic["text"],
                "category": tactic["category"],
                "vendor_types": ",".join(tactic["vendor_types"]),
            }
        }
        datapoints.append(datapoint)
    
    # Save to GCS (required for Vertex AI Vector Search)
    # Note: This requires setting up a GCS bucket
    logger.info(f"Generated {len(datapoints)} embeddings")
    logger.info("💡 To complete setup:")
    logger.info("   1. Upload datapoints to GCS bucket")
    logger.info("   2. Update index with GCS path")
    logger.info("   3. Set VECTOR_INDEX_ENDPOINT_ID in .env")
    
    return datapoints


def main():
    """Main setup workflow."""
    logger.info("=" * 60)
    logger.info("DesiYatra Vector Search Setup")
    logger.info("=" * 60)
    
    if not PROJECT_ID:
        logger.error("❌ GOOGLE_CLOUD_PROJECT not set!")
        return
    
    logger.info(f"📍 Project: {PROJECT_ID}")
    logger.info(f"📍 Location: {LOCATION}")
    
    try:
        # Step 1: Create index
        logger.info("\n" + "=" * 60)
        logger.info("Step 1: Creating Vector Index")
        logger.info("=" * 60)
        index_resource_name = create_vector_index()
        
        # Step 2: Create endpoint  
        logger.info("\n" + "=" * 60)
        logger.info("Step 2: Creating Index Endpoint")
        logger.info("=" * 60)
        endpoint = create_index_endpoint()
        
        # Step 3: Deploy index
        logger.info("\n" + "=" * 60)
        logger.info("Step 3: Deploying Index to Endpoint")
        logger.info("=" * 60)
        deploy_index_to_endpoint(index_resource_name, endpoint)
        
        # Step 4: Prepare initial data
        logger.info("\n" + "=" * 60)
        logger.info("Step 4: Preparing Initial Tactics")
        logger.info("=" * 60)
        datapoints = populate_initial_tactics(index_resource_name)
        
        # Final instructions
        logger.info("\n" + "=" * 60)
        logger.success("✅ Vector Search Setup Complete!")
        logger.info("=" * 60)
        logger.info("\n📝 Next Steps:")
        logger.info("1. Add to .env file:")
        logger.info(f"   VECTOR_INDEX_ENDPOINT_ID={endpoint.resource_name}")
        logger.info(f"   VECTOR_DEPLOYED_INDEX_ID={DEPLOYED_INDEX_ID}")
        logger.info("\n2. Upload tactics to GCS and update index")
        logger.info("3. Test with: python scripts/test_vector_search.py")
        
    except Exception as e:
        logger.error(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
