"""
Universal storage adapter for BlogFlowAutomator.
Works with local filesystem and cloud storage (S3, GCS, Azure).
Auto-detects environment and uses appropriate backend.
"""

import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class FileItem:
    """Represents a file in storage"""
    def __init__(self, name: str):
        self.name = name


class LocalFileStorage:
    """Local filesystem storage adapter"""
    
    def __init__(self, storage_dir: str = "./storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Using local storage at: {self.storage_dir.absolute()}")
    
    def upload_from_text(self, filename: str, content: str):
        """Save text content to a file"""
        filepath = self.storage_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def download_as_text(self, filename: str) -> str:
        """Read text content from a file"""
        filepath = self.storage_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def list(self) -> List[FileItem]:
        """List all files in storage"""
        return [
            FileItem(f.name) 
            for f in self.storage_dir.iterdir() 
            if f.is_file()
        ]
    
    def delete(self, filename: str):
        """Delete a file"""
        filepath = self.storage_dir / filename
        if filepath.exists():
            filepath.unlink()


class S3Storage:
    """AWS S3 storage adapter"""
    
    def __init__(self, bucket_name: str, prefix: str = ""):
        try:
            import boto3
            self.s3 = boto3.client('s3')
            self.bucket = bucket_name
            self.prefix = prefix
            logger.info(f"Using S3 storage: s3://{bucket_name}/{prefix}")
        except ImportError:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
    
    def _get_key(self, filename: str) -> str:
        """Get full S3 key with prefix"""
        if self.prefix:
            return f"{self.prefix}/{filename}"
        return filename
    
    def upload_from_text(self, filename: str, content: str):
        """Upload text content to S3"""
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self._get_key(filename),
            Body=content.encode('utf-8')
        )
    
    def download_as_text(self, filename: str) -> str:
        """Download text content from S3"""
        response = self.s3.get_object(
            Bucket=self.bucket,
            Key=self._get_key(filename)
        )
        return response['Body'].read().decode('utf-8')
    
    def list(self) -> List[FileItem]:
        """List all files in S3 bucket"""
        prefix = f"{self.prefix}/" if self.prefix else ""
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix
        )
        
        files = []
        for obj in response.get('Contents', []):
            # Remove prefix from key to get filename
            key = obj['Key']
            if self.prefix:
                key = key.replace(f"{self.prefix}/", "", 1)
            files.append(FileItem(key))
        
        return files
    
    def delete(self, filename: str):
        """Delete a file from S3"""
        self.s3.delete_object(
            Bucket=self.bucket,
            Key=self._get_key(filename)
        )


class GCSStorage:
    """Google Cloud Storage adapter"""
    
    def __init__(self, bucket_name: str, prefix: str = ""):
        try:
            from google.cloud import storage
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            self.prefix = prefix
            logger.info(f"Using GCS storage: gs://{bucket_name}/{prefix}")
        except ImportError:
            raise ImportError("google-cloud-storage is required. Install with: pip install google-cloud-storage")
    
    def _get_blob_name(self, filename: str) -> str:
        """Get full blob name with prefix"""
        if self.prefix:
            return f"{self.prefix}/{filename}"
        return filename
    
    def upload_from_text(self, filename: str, content: str):
        """Upload text content to GCS"""
        blob = self.bucket.blob(self._get_blob_name(filename))
        blob.upload_from_string(content, content_type='text/plain')
    
    def download_as_text(self, filename: str) -> str:
        """Download text content from GCS"""
        blob = self.bucket.blob(self._get_blob_name(filename))
        return blob.download_as_text()
    
    def list(self) -> List[FileItem]:
        """List all files in GCS bucket"""
        prefix = f"{self.prefix}/" if self.prefix else None
        blobs = self.bucket.list_blobs(prefix=prefix)
        
        files = []
        for blob in blobs:
            name = blob.name
            if self.prefix:
                name = name.replace(f"{self.prefix}/", "", 1)
            files.append(FileItem(name))
        
        return files
    
    def delete(self, filename: str):
        """Delete a file from GCS"""
        blob = self.bucket.blob(self._get_blob_name(filename))
        blob.delete()


def get_storage_client():
    """
    Factory function to get appropriate storage client based on environment.
    
    Environment variables:
    - STORAGE_TYPE: 'local', 's3', 'gcs' (default: 'local')
    - STORAGE_DIR: Local directory path (default: './storage')
    - S3_BUCKET: S3 bucket name
    - S3_PREFIX: Optional S3 key prefix
    - GCS_BUCKET: GCS bucket name
    - GCS_PREFIX: Optional GCS blob prefix
    
    Returns:
        Storage client instance
    """
    storage_type = os.getenv('STORAGE_TYPE', 'local').lower()
    
    if storage_type == 's3':
        bucket = os.getenv('S3_BUCKET')
        if not bucket:
            logger.warning("S3_BUCKET not set, falling back to local storage")
            return LocalFileStorage()
        prefix = os.getenv('S3_PREFIX', '')
        return S3Storage(bucket, prefix)
    
    elif storage_type == 'gcs':
        bucket = os.getenv('GCS_BUCKET')
        if not bucket:
            logger.warning("GCS_BUCKET not set, falling back to local storage")
            return LocalFileStorage()
        prefix = os.getenv('GCS_PREFIX', '')
        return GCSStorage(bucket, prefix)
    
    else:  # local or default
        storage_dir = os.getenv('STORAGE_DIR', './storage')
        return LocalFileStorage(storage_dir)


# For backward compatibility with Replit
def Client():
    """Alias for get_storage_client() to match Replit API"""
    return get_storage_client()
