import logging
import httpx
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from backend.app.config import settings

logger = logging.getLogger("phoenix.supabase")

class SupabaseService:
    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)

    @classmethod
    def verify_supabase_jwt(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Validates a JWT issued by Supabase Auth using the server-only SUPABASE_JWT_SECRET.
        Extracts sub (user_id), email, and user role.
        """
        jwt_secret = settings.SUPABASE_JWT_SECRET or settings.SUPABASE_SERVICE_ROLE_KEY
        if not jwt_secret:
            return None

        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": bool(settings.SUPABASE_URL)}
            )
            return payload
        except JWTError as e:
            logger.debug(f"Supabase JWT validation failed: {e}")
            return None

    @classmethod
    def upload_storage_object(
        cls,
        bucket_name: str,
        object_path: str,
        content_bytes: bytes,
        content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """
        Uploads an artifact or archive directly to a private Supabase Storage bucket
        using the server-only service-role key.
        """
        if not cls.is_configured():
            return None

        url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket_name}/{object_path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Content-Type": content_type,
            "x-upsert": "true"
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, content=content_bytes, headers=headers)
                if res.status_code in (200, 201):
                    return f"{bucket_name}/{object_path}"
                else:
                    logger.warning(f"Supabase storage upload error ({res.status_code}): {res.text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to upload to Supabase storage: {e}")
            return None

    @classmethod
    def create_signed_download_url(
        cls,
        bucket_name: str,
        object_path: str,
        expires_in_seconds: int = 3600
    ) -> Optional[str]:
        """
        Generates a short-lived signed URL for safe artifact or patch downloads.
        """
        if not cls.is_configured():
            return None

        url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/sign/{bucket_name}/{object_path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Content-Type": "application/json"
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json={"expiresIn": expires_in_seconds}, headers=headers)
                if res.status_code == 200:
                    signed_url = res.json().get("signedURL")
                    if signed_url:
                        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1{signed_url}"
                return None
        except Exception as e:
            logger.error(f"Failed to generate Supabase signed URL: {e}")
            return None
