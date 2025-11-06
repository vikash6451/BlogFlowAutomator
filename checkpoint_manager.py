"""
Checkpoint management for resilient blog post processing.
Handles saving and loading incremental progress to enable resume functionality.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from storage_adapter import Client
import uuid

# Storage is always available with the adapter
REPLIT_STORAGE_AVAILABLE = True


class CheckpointManager:
    """Manages checkpoints for blog post analysis runs"""
    
    CHECKPOINT_PREFIX = "checkpoint_"
    CHECKPOINT_INTERVAL = 10  # Save every N posts
    
    def __init__(self):
        self.storage_client = Client()
        self.current_checkpoint = None
    
    def create_checkpoint(
        self,
        url: str,
        scraped_links: List[Dict],
        processed_results: List[Dict],
        last_index: int,
        total_posts: int,
        run_id: Optional[str] = None
    ) -> str:
        """Create a new checkpoint"""
        if not run_id:
            run_id = str(uuid.uuid4())[:8]
        
        checkpoint_data = {
            'run_id': run_id,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'scraped_links': scraped_links,
            'processed_results': processed_results,
            'last_index': last_index,
            'total_posts': total_posts,
            'status': 'in_progress'
        }
        
        checkpoint_key = f"{self.CHECKPOINT_PREFIX}{run_id}.json"
        
        try:
            self.storage_client.upload_from_text(
                checkpoint_key,
                json.dumps(checkpoint_data, indent=2)
            )
            self.current_checkpoint = checkpoint_data
            return run_id
        except Exception as e:
            print(f"Failed to save checkpoint: {e}")
            return run_id
    
    def load_checkpoint(self, run_id: str) -> Optional[Dict]:
        """Load a checkpoint by run ID"""
        checkpoint_key = f"{self.CHECKPOINT_PREFIX}{run_id}.json"
        
        try:
            checkpoint_json = self.storage_client.download_as_text(checkpoint_key)
            return json.loads(checkpoint_json)
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
            return None
    
    def list_incomplete_checkpoints(self) -> List[Dict]:
        """List all incomplete checkpoint runs"""
        incomplete = []
        
        try:
            files = self.storage_client.list()
            
            for file in files:
                if file.name.startswith(self.CHECKPOINT_PREFIX):
                    try:
                        checkpoint_json = self.storage_client.download_as_text(file.name)
                        checkpoint = json.loads(checkpoint_json)
                        
                        if checkpoint.get('status') == 'in_progress':
                            incomplete.append({
                                'run_id': checkpoint['run_id'],
                                'url': checkpoint['url'],
                                'timestamp': checkpoint['timestamp'],
                                'progress': f"{checkpoint['last_index']}/{checkpoint['total_posts']}",
                                'processed_count': checkpoint['last_index'],
                                'total_count': checkpoint['total_posts']
                            })
                    except Exception as e:
                        print(f"Error reading checkpoint {file.name}: {e}")
                        continue
            
            # Sort by timestamp, newest first
            incomplete.sort(key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            print(f"Failed to list checkpoints: {e}")
        
        return incomplete
    
    def mark_complete(self, run_id: str) -> bool:
        """Mark a checkpoint as complete"""
        checkpoint_key = f"{self.CHECKPOINT_PREFIX}{run_id}.json"
        
        try:
            checkpoint = self.load_checkpoint(run_id)
            if checkpoint:
                checkpoint['status'] = 'completed'
                checkpoint['completed_at'] = datetime.now().isoformat()
                
                self.storage_client.upload_from_text(
                    checkpoint_key,
                    json.dumps(checkpoint, indent=2)
                )
                return True
        except Exception as e:
            print(f"Failed to mark checkpoint complete: {e}")
        
        return False
    
    def delete_checkpoint(self, run_id: str) -> bool:
        """Delete a checkpoint"""
        checkpoint_key = f"{self.CHECKPOINT_PREFIX}{run_id}.json"
        
        try:
            self.storage_client.delete(checkpoint_key)
            return True
        except Exception as e:
            print(f"Failed to delete checkpoint: {e}")
            return False
    
    def should_save_checkpoint(self, current_index: int) -> bool:
        """Check if we should save a checkpoint at this index"""
        return (current_index + 1) % self.CHECKPOINT_INTERVAL == 0
    
    def cleanup_old_checkpoints(self, max_age_days: int = 7):
        """Delete completed checkpoints older than max_age_days"""
        try:
            files = self.storage_client.list()
            now = datetime.now()
            
            for file in files:
                if file.name.startswith(self.CHECKPOINT_PREFIX):
                    try:
                        checkpoint_json = self.storage_client.download_as_text(file.name)
                        checkpoint = json.loads(checkpoint_json)
                        
                        if checkpoint.get('status') == 'completed':
                            completed_at = datetime.fromisoformat(checkpoint.get('completed_at', checkpoint['timestamp']))
                            age_days = (now - completed_at).days
                            
                            if age_days > max_age_days:
                                self.storage_client.delete(file.name)
                                print(f"Cleaned up old checkpoint: {file.name}")
                    except Exception as e:
                        print(f"Error cleaning checkpoint {file.name}: {e}")
                        continue
        except Exception as e:
            print(f"Failed to cleanup checkpoints: {e}")
