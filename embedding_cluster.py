import os
from openai import OpenAI
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np
from typing import List, Dict, Optional, Tuple

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user

def get_openai_client():
    """Get OpenAI client with proper error handling."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def generate_embeddings(texts: List[str], model: str = "text-embedding-3-large") -> List[List[float]]:
    """
    Generate embeddings for a list of texts using OpenAI's embedding model.
    
    Args:
        texts: List of text strings to embed
        model: OpenAI embedding model to use (default: text-embedding-3-large)
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    client = get_openai_client()
    
    embeddings = []
    batch_size = 100
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model=model
        )
        batch_embeddings = [item.embedding for item in response.data]
        embeddings.extend(batch_embeddings)
    
    return embeddings


def determine_optimal_clusters(embeddings: np.ndarray, min_clusters: int = 2, max_clusters: int = 10) -> int:
    """
    Determine optimal number of clusters using silhouette score.
    
    Args:
        embeddings: Array of embedding vectors
        min_clusters: Minimum number of clusters to try
        max_clusters: Maximum number of clusters to try
    
    Returns:
        Optimal number of clusters
    """
    if len(embeddings) < min_clusters:
        return max(2, len(embeddings))
    
    max_clusters = min(max_clusters, len(embeddings) - 1)
    
    if max_clusters < min_clusters:
        return min_clusters
    
    best_score = -1
    best_k = min_clusters
    
    for k in range(min_clusters, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        if len(set(labels)) > 1:
            score = silhouette_score(embeddings, labels)
            if score > best_score:
                best_score = score
                best_k = k
    
    return best_k


def cluster_embeddings(embeddings: List[List[float]], n_clusters: Optional[int] = None) -> Tuple[List[int], np.ndarray]:
    """
    Cluster embeddings using K-means.
    
    Args:
        embeddings: List of embedding vectors
        n_clusters: Number of clusters (if None, will be determined automatically)
    
    Returns:
        Tuple of (cluster labels, cluster centers)
    """
    if not embeddings:
        return [], np.array([])
    
    embeddings_array = np.array(embeddings)
    
    if len(embeddings) == 1:
        return [0], embeddings_array
    
    if n_clusters is None:
        n_clusters = determine_optimal_clusters(embeddings_array)
    
    n_clusters = min(n_clusters, len(embeddings))
    n_clusters = max(2, n_clusters)
    
    if len(embeddings) < n_clusters:
        n_clusters = len(embeddings)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings_array)
    
    return labels.tolist(), kmeans.cluster_centers_


def prepare_texts_for_embedding(posts: List[Dict[str, str]]) -> List[str]:
    """
    Prepare blog post content for embedding generation.
    Combines title, summary, and main points into a single text for semantic analysis.
    
    Args:
        posts: List of blog post dictionaries with 'title', 'summary', 'main_points'
    
    Returns:
        List of prepared text strings
    """
    texts = []
    for post in posts:
        title = post.get('title', '')
        summary = post.get('summary', '')
        main_points = post.get('main_points', [])
        
        text_parts = [title]
        if summary:
            text_parts.append(summary)
        if main_points:
            text_parts.append("Key points: " + " ".join(main_points))
        
        text = "\n\n".join(text_parts)
        texts.append(text)
    
    return texts


def cluster_blog_posts(posts: List[Dict[str, str]], n_clusters: Optional[int] = None) -> Dict:
    """
    Full pipeline: embed and cluster blog posts.
    
    Args:
        posts: List of blog post dictionaries
        n_clusters: Number of clusters (if None, will be determined automatically)
    
    Returns:
        Dictionary with clustering results
    """
    if not posts:
        return {
            'clusters': [],
            'posts_with_clusters': [],
            'cluster_centers': []
        }
    
    texts = prepare_texts_for_embedding(posts)
    
    embeddings = generate_embeddings(texts)
    
    labels, centers = cluster_embeddings(embeddings, n_clusters)
    
    posts_with_clusters = []
    for i, post in enumerate(posts):
        post_copy = post.copy()
        post_copy['cluster_id'] = int(labels[i])
        posts_with_clusters.append(post_copy)
    
    clusters = {}
    for post in posts_with_clusters:
        cluster_id = post['cluster_id']
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(post)
    
    return {
        'clusters': clusters,
        'posts_with_clusters': posts_with_clusters,
        'cluster_centers': centers.tolist(),
        'n_clusters': len(clusters)
    }
