from minio import Minio
from minio.error import S3Error
from app.core.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, MINIO_SECURE

class MinioClient:
    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        if not self.client.bucket_exists(MINIO_BUCKET):
            self.client.make_bucket(MINIO_BUCKET)

    def upload_file(self, file_path: str, local_path: str) -> str:
        """Uploads a file to MinIO and returns the object path."""
        try:
            self.client.fput_object(MINIO_BUCKET, file_path, local_path)
            return file_path
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file to MinIO: {e}")

    def upload_bytes(self, file_path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Uploads bytes to MinIO."""
        import io
        try:
            self.client.put_object(
                MINIO_BUCKET, 
                file_path, 
                io.BytesIO(data), 
                len(data),
                content_type=content_type
            )
            return file_path
        except S3Error as e:
            raise RuntimeError(f"Failed to upload bytes to MinIO: {e}")

    def download_file(self, object_path: str, local_path: str):
        """Downloads a file from MinIO."""
        try:
            self.client.fget_object(MINIO_BUCKET, object_path, local_path)
        except S3Error as e:
            raise RuntimeError(f"Failed to download file from MinIO: {e}")

    def get_presigned_url(self, object_path: str) -> str:
        """Generates a presigned URL for downloading."""
        return self.client.presigned_get_object(MINIO_BUCKET, object_path)

minio_client = MinioClient()
