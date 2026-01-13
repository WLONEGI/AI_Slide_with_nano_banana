import logging
import uuid
from google.cloud import storage
from src.config.env import GCS_BUCKET_NAME

logger = logging.getLogger(__name__)

def upload_to_gcs(file_data: bytes, content_type: str = "image/png") -> str:
    """
    Uploads binary data to Google Cloud Storage and returns the public URL.
    
    Args:
        file_data: The binary content to upload
        content_type: The MIME type of the content which helps getting browser to render it correctly.
        
    Returns:
        str: The authenticated public URL of the uploaded blob.
    
    Raises:
        ValueError: If GCS_BUCKET_NAME is not set.
    """
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME environment variable is not set.")

    try:
        # Initialize client
        # Implicitly uses GOOGLE_APPLICATION_CREDENTIALS
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        # Generate unique filename
        filename = f"generated_assets/{uuid.uuid4()}"
        if content_type == "image/png":
            filename += ".png"
        elif content_type == "image/jpeg":
            filename += ".jpg"
            
        blob = bucket.blob(filename)
        
        # Upload
        blob.upload_from_string(file_data, content_type=content_type)
        
        # Note: public_url might require the bucket to be public or signed URLs.
        # For simplicity in this protected internal tool, we return the selfLink or public URL
        # assuming the bucket or object is made readable or authenticated access is used elsewhere.
        # Ideally, use blob.generate_signed_url() for private buckets.
        

        # Returning public URL (assuming public read or suitable access context)
        return blob.public_url

    except Exception as e:
        logger.error(f"Failed to upload to GCS: {e}")
        raise e

def download_blob_as_bytes(url: str) -> bytes | None:
    """
    Downloads a blob from a URL (e.g., GCS public URL).
    """
    import httpx
    try:
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Failed to download from {url}: {e}")
        return None
