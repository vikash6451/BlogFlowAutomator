# Storage Configuration

BlogFlowAutomator uses a universal storage adapter that works in any environment.

## Local Development (Default)

No configuration needed. Files are stored in `./storage/` directory.

```bash
streamlit run app.py
```

Storage location: `BlogFlowAutomator/storage/`

## Cloud Deployment

### Option 1: AWS S3

**Setup:**
```bash
# Install boto3
pip install boto3

# Configure AWS credentials (one of these methods):
# 1. Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# 2. Or use AWS CLI
aws configure
```

**Environment variables:**
```bash
export STORAGE_TYPE=s3
export S3_BUCKET=your-bucket-name
export S3_PREFIX=blog-automation  # optional subfolder
```

**For Streamlit Cloud:** Add to `.streamlit/secrets.toml`:
```toml
STORAGE_TYPE = "s3"
S3_BUCKET = "your-bucket-name"
S3_PREFIX = "blog-automation"
AWS_ACCESS_KEY_ID = "your_key"
AWS_SECRET_ACCESS_KEY = "your_secret"
AWS_DEFAULT_REGION = "us-east-1"
```

### Option 2: Google Cloud Storage

**Setup:**
```bash
# Install GCS library
pip install google-cloud-storage

# Authenticate (one of these methods):
# 1. Service account key file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# 2. Or use gcloud
gcloud auth application-default login
```

**Environment variables:**
```bash
export STORAGE_TYPE=gcs
export GCS_BUCKET=your-bucket-name
export GCS_PREFIX=blog-automation  # optional subfolder
```

**For Streamlit Cloud:** Add to `.streamlit/secrets.toml`:
```toml
STORAGE_TYPE = "gcs"
GCS_BUCKET = "your-bucket-name"
GCS_PREFIX = "blog-automation"
# Also upload service account JSON as secret
```

### Option 3: Custom Local Path

Useful for Docker or specific deployment scenarios:

```bash
export STORAGE_TYPE=local
export STORAGE_DIR=/app/persistent-storage
```

## Testing Storage Configuration

```python
from storage_adapter import get_storage_client

# Test connection
client = get_storage_client()

# Upload test file
client.upload_from_text("test.txt", "Hello World")

# List files
files = client.list()
print(f"Found {len(files)} files")

# Download file
content = client.download_as_text("test.txt")
print(content)

# Clean up
client.delete("test.txt")
```

## Cost Considerations

### Local Storage
- **Cost**: Free
- **Persistence**: Lost when container restarts (unless volume mounted)
- **Best for**: Development, testing

### AWS S3
- **Cost**: ~$0.023/GB/month + requests
- **Free tier**: 5GB storage, 20k GET, 2k PUT requests/month (first 12 months)
- **Best for**: Production with AWS infrastructure

### Google Cloud Storage
- **Cost**: ~$0.020/GB/month + requests
- **Free tier**: 5GB storage, 5k operations/month (always free)
- **Best for**: Production with GCP infrastructure

## Recommended Setup by Environment

| Environment | Storage Type | Why |
|------------|--------------|-----|
| Local dev | `local` | Simple, fast, free |
| Streamlit Cloud | `local` or `s3` | Local for demos, S3 for production |
| Render/Railway | `s3` or `gcs` | Containers are ephemeral |
| Heroku | `s3` or `gcs` | Ephemeral filesystem |
| Docker | `local` with volume | Persistent across restarts |
| AWS deployment | `s3` | Native integration |
| GCP deployment | `gcs` | Native integration |

## Troubleshooting

**"Storage unavailable" warning:**
- Check environment variables are set correctly
- Verify cloud credentials are configured
- Ensure bucket exists and is accessible
- Check IAM permissions for cloud storage

**Files not persisting:**
- Local storage: Check if `./storage/` directory exists
- Cloud: Verify bucket name and permissions
- Streamlit Cloud: Consider using S3/GCS instead of local

**Permission errors:**
- AWS: Ensure IAM user has `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `s3:DeleteObject`
- GCS: Ensure service account has "Storage Object Admin" role
