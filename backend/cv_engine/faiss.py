from ctypes import sizeof
import os
import json
import faiss
import numpy as np
from dotenv import load_dotenv
from django_redis import get_redis_connection

load_dotenv()

EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", ""))
FAISS_PATH = os.getenv("FAISS_PATH", "faiss")
CONFIDENCE = float(os.getenv("CONFIDENCE", ""))
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", ""))

redis = get_redis_connection("default")
faiss_global_index = None


def build_global_faiss():
    print("Building FAISS index")
    global faiss_global_index
    
    from reference_images.models import ReferenceImages
    refs = ReferenceImages.objects.select_related("user").all()

    vectors = []
    id_map = []

    for ref in refs:
        emb = ref.get_embedding()
        if emb is not None and len(emb) > 0:  # Add validation
            vectors.append(emb)
            id_map.append(ref.user.id)

    if not vectors:
        faiss_global_index = None
        print("No vectors found to build FAISS index")
        return

    vectors = np.array(vectors).astype("float32")

    # Normalize if using cosine similarity
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    

    index.add(vectors)  # type: ignore

    faiss_global_index = {
        "index": index,
        "id_map": id_map
    }


def faiss_save():
    if not faiss_global_index:
        return
    
    print("Saving FAISS index")

    os.makedirs(FAISS_PATH, exist_ok=True)

    tmp_index = os.path.join(FAISS_PATH, "global.index.tmp")
    final_index = os.path.join(FAISS_PATH, "global.index")
    tmp_meta = os.path.join(FAISS_PATH, "global_meta.npy.tmp")
    final_meta = os.path.join(FAISS_PATH, "global_meta.npy")

    faiss.write_index(faiss_global_index["index"], tmp_index)
    np.save(tmp_meta, np.array(faiss_global_index["id_map"]))

    os.replace(tmp_index, final_index)
    os.replace(tmp_meta + ".npy", final_meta)
    
    
def load_faiss_manager(is_update=False):
    lock = redis.lock("faiss_build_lock", timeout=300)
    if not lock.acquire(blocking=False):
        return  # another worker is building

    try:
        if is_update or not faiss_load():
            print("Building new FAISS index...")
            build_global_faiss()
            faiss_save()
        else:
            print("FAISS index loaded from disk.")
        
    except Exception as e:
        print(f"error: {e}")
    finally:
        lock.release()


def faiss_load():
    global faiss_global_index

    index_path = os.path.join(FAISS_PATH, "global.index")
    meta_path = os.path.join(FAISS_PATH, "global_meta.npy")

    if not os.path.exists(index_path):
        build_global_faiss()
    
    print("Loading FAISS index")

    index = faiss.read_index(index_path)
    id_map = np.load(meta_path).tolist()

    faiss_global_index = {
        "index": index,
        "id_map": id_map
    }
    return True


# only load FAISS when a task or endpoint needs it
def get_faiss_index():
    global faiss_global_index
    if faiss_global_index is None:
        faiss_load()
    return faiss_global_index


def find_cosine_similarity(query_embedding: np.ndarray, candidate_embedding: np.ndarray) -> np.float64:
    """
    Find cosine distance between two L2-normalized embeddings.
    Returns:
        np.float64: Cosine distance in [0, 1]
    """
    query_embedding = np.asarray(query_embedding, dtype=np.float32)
    candidate_embedding = np.asarray(candidate_embedding, dtype=np.float32)

    # embeddings are already L2-normalized
    cosine_similarity = np.dot(query_embedding, candidate_embedding)
    cosine_distance = 1.0 - cosine_similarity

    return np.float64(cosine_similarity)


def faiss_search(embeddings: list[np.ndarray]):
    """
    Search embeddings in FAISS index with per-gate access control and strict majority voting.
    
    Returns:
        dict: {"status": "known"/"unknown", "label": employee_number or None, "similarity": between 0 to 1 or None}
    """
    top_k = 10
    predictions = []

    temp = get_faiss_index()
    faiss_index, true_labels = temp["index"], temp["id_map"] # type: ignore
    del temp

    for embedding in embeddings:
        embedding = np.array(embedding, dtype=np.float32)
        if embedding.ndim == 1:
            embedding = np.expand_dims(embedding, axis=0).astype(np.float32)

        faiss_distances, faiss_indices = faiss_index.search(embedding, top_k)
        top_k_indices = faiss_indices[0]
        top_k_distances = faiss_distances[0]

        valid_neighbors = [
            (idx, dist) for idx, dist in zip(top_k_indices, top_k_distances)
            if 0 <= idx < len(true_labels)
        ]

        if not valid_neighbors:
            predictions.append({"status": "unknown", "label": None, "similarity": None})
            continue

        # Weighted voting
        label_weight_sum = {}
        for idx, dist in valid_neighbors:
            label = true_labels[idx]
            score = 1 / (dist + 1e-8)
            label_weight_sum[label] = label_weight_sum.get(label, 0) + score

        winning_label = max(label_weight_sum, key=lambda k: label_weight_sum[k])
        winning_label_ratio = label_weight_sum[winning_label] / sum(label_weight_sum.values())

        # collect all candidate vectors with the winning label
        label_matches = [
            (idx, dist) 
            for idx, dist in valid_neighbors 
            if true_labels[idx] == winning_label
        ]
        
        cosine_scores = []
        for idx, dist in label_matches:
            candidate_vec = np.zeros(faiss_index.d, dtype=np.float32)
            faiss_index.reconstruct(int(idx), candidate_vec)
            cosine_sim = find_cosine_similarity(embedding[0], candidate_vec)
            cosine_scores.append(cosine_sim)
        max_similarity = max(cosine_scores)
        
        if winning_label_ratio < CONFIDENCE or max_similarity < MIN_SIMILARITY:
            predictions.append({"status": "unknown", "label": None, "similarity": None})
        else:
            predictions.append({"status": "known", "label": winning_label, "similarity": max_similarity})

    # Count votes per category
    vote_counts = {"unknown": {}, "known": {}}
    for p in predictions:
        status = p["status"]
        label = p["label"]
        
        # unkown is only can be one person, but known prediction can have diffrent id
        if status == "unknown":
            vote_counts["unknown"]["unknown"] = vote_counts["unknown"].get("unknown", 0) + 1
        else:
            vote_counts["known"][label] = vote_counts["known"].get(label, 0) + 1
    
    # Get majority for each category
    max_votes = {}
    for status, counts in vote_counts.items():
        if counts:
            label, count = max(counts.items(), key=lambda x: x[1])
            max_votes[status] = {"label": label, "count": count}
        else:
            max_votes[status] = {"label": None, "count": -1}

    # Determine final result
    counts_only = {k: v["count"] for k, v in max_votes.items()}
    sorted_counts = sorted(counts_only.items(), key=lambda x: x[1], reverse=True)

    # Check for tie
    if len(sorted_counts) > 1 and sorted_counts[0][1] == sorted_counts[1][1]:
        return {"status": "unknown", "label": None, "similarity": None}

    # Otherwise, return the top category
    top_status = sorted_counts[0][0]
    winning_label = max_votes[top_status]["label"]
    
    # Get max similarity for the winning label/status
    if top_status == "unknown":
        final_similarity = None
    else:
        matching_similarities = [
            p["similarity"] for p in predictions 
            if p["status"] == top_status and p["label"] == winning_label and p["similarity"] is not None
        ]
        final_similarity = float(max(matching_similarities))
    
    return {"status": top_status, "label": winning_label, "similarity": final_similarity}

    # ---------------------------------------------
    # Aggregate predictions across all embeddings
    # ---------------------------------------------
    # We have two possible statuses per embedding prediction:
    #   2. "known" -> user exists with good confident
    #   3. "unknown"     -> no confident match
    #
    # Step 1: Count votes per status and per label
    #   - For "known", we track counts per user.id number.
    #   - For "unknown", we just count total unknown occurrences.
    #
    # Step 2: Determine the majority (max votes) for each status
    #   - For each category, find the label with the highest votes and store its count.
    #   - If a category has no votes, we set count to -1 to differentiate from zero votes.
    #
    # Step 3: Compare top vote counts across all statuses
    #   - Sort the categories by their max vote counts descending.
    #   - If there’s a tie between the top two categories, we cannot decide confidently,
    #     so we return "unknown" to indicate uncertainty.
    #
    # Step 4: If there is a clear winner (no tie), return its status and the corresponding label.
    #   - "known", will include the user.id number with the highest votes.
    #   - "unknown", simply indicates no confident match across embeddings.
    #
    # This logic ensures that:
    #   - Majority voting is applied per category and across embeddings.
    #   - Ties or ambiguous situations default to "unknown" to prevent false positives.