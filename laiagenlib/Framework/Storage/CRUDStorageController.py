import base64
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional, List, Dict, Any

import boto3
from botocore.client import Config
from bson import ObjectId
from dotenv import load_dotenv
import urllib.request
from fastapi import (APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, Security, UploadFile, status)
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.utils
    import cloudinary.api
    HAS_CLOUDINARY = True
except ImportError:
    HAS_CLOUDINARY = False

try:
    from ...Domain.Shared.Utils.logger import _logger
except Exception:
    import logging
    _logger = logging.getLogger("LAIA")

load_dotenv()

security_scheme = HTTPBearer()

# Lista de extensiones ejecutables no permitidas
DISALLOWED_EXTENSIONS = {
    "exe", "bat", "cmd", "sh", "bin", "msi", "dll", "com", "scr", "vbs",
    "ps1", "apk", "jar", "app", "action", "run", "gadget", "cpl", "pif",
    "wsf", "hta", "vbe", "jse", "reg"
}



def CRUDStorageController(
    endpoint_url: str = "",
    access_key: str = "",
    secret_key: str = "",
    public_endpoint_url: str = "",
    secure: bool = False,
    db=None,
    jwtSecretKey: str = "secret_key",
    bucket_originals: str = "originals",
    storage_collection: str = "user_photos",
    imgproxy_endpoint: str = "",
):
    """
    Controlador de almacenamiento para LAIA con las funciones y endpoints de MinIO e Imgproxy:
    - cargar_minio_client()
    - cargar_public_minio_client()
    - generar_imgproxy_url()
    - get_current_user_data()
    - get_current_user_id()
    - POST /upload
    - POST /upload/confirm-temp
    - GET /download/{image_id:path} (con soporte para medidas y formas vía imgproxy)
    - GET /admin/files/explorer
    - Operaciones básicas /storage/{bucket}
    """
    router = APIRouter(tags=["Storage"])

    backend_jwt_secret_key = jwtSecretKey
    collection_name = os.getenv("STORAGE_COLLECTION") or storage_collection or "user_photos"
    bucket_originals = os.getenv("MINIO_BUCKET_ORIGINALS") or bucket_originals or "originals"

    # Configuración de Imgproxy
    IMGPROXY_BASE_URL = os.getenv("IMGPROXY_BASE_URL") or imgproxy_endpoint or "http://localhost:7000"
    IMGPROXY_INTERNAL_URL = os.getenv("IMGPROXY_INTERNAL_URL") or "http://imgproxy:8080"

    def get_active_storage_provider() -> str:
        provider_env = os.getenv("STORAGE_PROVIDER", "").strip().lower()
        if provider_env in ["cloudinary", "minio", "s3"]:
            return "cloudinary" if provider_env == "cloudinary" else "minio"

        if os.getenv("MINIO_ENDPOINT") or os.getenv("MINIO_ACCESS_KEY"):
            return "minio"
        elif os.getenv("CLOUDINARY_CLOUD_NAME") and os.getenv("CLOUDINARY_API_KEY"):
            return "cloudinary"
        return "minio"

    _logger.info(f"[STORAGE] Proveedor activo: {get_active_storage_provider().upper()}")

    def init_cloudinary() -> bool:
        if not HAS_CLOUDINARY:
            return False
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        if cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True,
            )
            return True
        return False

    def generar_cloudinary_url(
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        resizing_type: Optional[str] = None,
        gravity: Optional[str] = None,
        format: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        init_cloudinary()
        clean_pid = public_id.strip()
        if "res.cloudinary.com" in clean_pid and "/upload/" in clean_pid:
            parts = clean_pid.split("/upload/")
            after_upload = parts[1]
            subparts = after_upload.split("/")
            if subparts[0].startswith("v") and subparts[0][1:].isdigit():
                clean_pid = "/".join(subparts[1:])
            elif any(subparts[0].startswith(p) for p in ["w_", "h_", "c_", "g_"]):
                clean_pid = "/".join(subparts[2:]) if len(subparts) > 2 and subparts[1].startswith("v") else "/".join(subparts[1:])

        if "." in clean_pid:
            clean_pid = clean_pid.rsplit(".", 1)[0]

        trans = {}
        if width: trans["width"] = width
        if height: trans["height"] = height
        if resizing_type:
            trans["crop"] = "fill" if resizing_type.lower() == "fill" else "fit"
        elif width or height:
            trans["crop"] = "fill"

        if gravity:
            trans["gravity"] = "face" if gravity.lower() in ["sm", "face"] else "center"

        if format and format.lower() != "original":
            trans["format"] = format.lstrip(".").lower()

        if quality:
            trans["quality"] = quality

        url, _ = cloudinary.utils.cloudinary_url(clean_pid, **trans)
        return url

    def generar_imgproxy_url(
        source_url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        resizing_type: Optional[str] = None,
        gravity: Optional[str] = None,
        format: Optional[str] = None,
        quality: Optional[int] = None,
        enlarge: int = 0,
        extend: int = 0,
        base_url: Optional[str] = None,
    ) -> str:
        options = []
        if width is not None or height is not None or resizing_type:
            rt = (resizing_type or "fit").lower()
            w = width if width is not None else 0
            h = height if height is not None else 0
            options.append(f"resize:{rt}:{w}:{h}")

        if gravity:
            options.append(f"gravity:{gravity.lower()}")

        if quality:
            options.append(f"quality:{quality}")

        if format and format.lower() != "original":
            options.append(f"format:{format.lstrip('.').lower()}")

        options_path = "/".join(options) if options else "resize:fill:0:0"
        clean_source = source_url.strip()
        target_base = (base_url or IMGPROXY_BASE_URL).rstrip('/')

        return f"{target_base}/insecure/{options_path}/plain/{clean_source}"

    def fetch_imgproxy_stream(url: str):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "LAIA-Storage-Proxy/1.0"}
        )
        return urllib.request.urlopen(req, timeout=12)

    def cargar_minio_client():
        load_dotenv()

        MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT") or endpoint_url or "minio:9000"
        MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY") or access_key or "minioadmin"
        MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY") or secret_key or "minioadmin"
        MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true" or secure

        protocol = "https" if MINIO_SECURE else "http"
        endpoint = MINIO_ENDPOINT if "://" in MINIO_ENDPOINT else f"{protocol}://{MINIO_ENDPOINT}"

        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="eu-south-2",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def cargar_public_minio_client():
        load_dotenv()

        MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT") or public_endpoint_url or "localhost:9000"
        MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY") or access_key or "minioadmin"
        MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY") or secret_key or "minioadmin"
        MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true" or secure

        protocol = "https" if MINIO_SECURE else "http"
        endpoint = MINIO_PUBLIC_ENDPOINT if "://" in MINIO_PUBLIC_ENDPOINT else f"{protocol}://{MINIO_PUBLIC_ENDPOINT}"

        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="eu-south-2",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def get_current_user_data(
        credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    ) -> dict:
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token no proporcionado",
            )

        token = credentials.credentials
        try:
            payload = jwt.decode(token, backend_jwt_secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=401, detail="Token invalido: falta el ID de usuario"
                )

            user_id = str(user_id)
            is_admin = False

            user_name = str(payload.get("user_name", "")).lower()
            if user_name == "admin":
                is_admin = True

            if not is_admin:
                name = str(payload.get("name", "")).lower()
                if name == "admin":
                    is_admin = True

            if not is_admin:
                username = str(payload.get("username", "")).lower()
                if username == "admin":
                    is_admin = True

            if not is_admin:
                role = str(payload.get("role", "")).lower()
                if role == "admin":
                    is_admin = True

            if not is_admin:
                roles = payload.get("roles", [])
                if isinstance(roles, list) and "admin" in [str(r).lower() for r in roles]:
                    is_admin = True

            if not is_admin:
                user_roles = payload.get("user_roles", [])
                if isinstance(user_roles, list) and "admin" in [str(r).lower() for r in user_roles]:
                    is_admin = True

            if not is_admin and db is not None:
                query = (
                    {"_id": ObjectId(user_id)}
                    if ObjectId.is_valid(user_id)
                    else {"_id": user_id}
                )
                user_doc = db["user"].find_one(query)
                if user_doc:
                    doc_user_name = str(user_doc.get("user_name", "")).lower()
                    if doc_user_name == "admin":
                        is_admin = True

                    if not is_admin:
                        doc_name = str(user_doc.get("name", "")).lower()
                        if doc_name == "admin":
                            is_admin = True

                    if not is_admin:
                        doc_email = str(user_doc.get("email", "")).lower()
                        if doc_email.startswith("admin"):
                            is_admin = True

                    if not is_admin:
                        doc_role = str(user_doc.get("role", "")).lower()
                        if doc_role == "admin":
                            is_admin = True

                    if not is_admin:
                        doc_roles = user_doc.get("roles", [])
                        if isinstance(doc_roles, list) and "admin" in [str(r).lower() for r in doc_roles]:
                            is_admin = True

            return {"user_id": user_id, "is_admin": is_admin}
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="El token ha expirado")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token invalido")

    optional_security_scheme = HTTPBearer(auto_error=False)

    def get_current_user_data_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security_scheme),
        token_query: Optional[str] = Query(None, alias="token"),
    ) -> Optional[dict]:
        token = None
        if credentials and credentials.credentials:
            token = credentials.credentials
        elif token_query:
            token = token_query

        if not token:
            return None

        try:
            payload = jwt.decode(token, backend_jwt_secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id") or payload.get("sub")
            if not user_id:
                return None

            user_id = str(user_id)
            is_admin = False

            user_name = str(payload.get("user_name", "")).lower()
            if user_name == "admin":
                is_admin = True

            if not is_admin:
                name = str(payload.get("name", "")).lower()
                if name == "admin":
                    is_admin = True

            if not is_admin:
                username = str(payload.get("username", "")).lower()
                if username == "admin":
                    is_admin = True

            if not is_admin:
                role = str(payload.get("role", "")).lower()
                if role == "admin":
                    is_admin = True

            if not is_admin:
                roles = payload.get("roles", [])
                if isinstance(roles, list) and "admin" in [str(r).lower() for r in roles]:
                    is_admin = True

            if not is_admin:
                user_roles = payload.get("user_roles", [])
                if isinstance(user_roles, list) and "admin" in [str(r).lower() for r in user_roles]:
                    is_admin = True

            if not is_admin and db is not None:
                query = (
                    {"_id": ObjectId(user_id)}
                    if ObjectId.is_valid(user_id)
                    else {"_id": user_id}
                )
                user_doc = db["user"].find_one(query)
                if user_doc:
                    doc_user_name = str(user_doc.get("user_name", "")).lower()
                    if doc_user_name == "admin":
                        is_admin = True
                    if not is_admin:
                        doc_name = str(user_doc.get("name", "")).lower()
                        if doc_name == "admin":
                            is_admin = True
                    if not is_admin:
                        doc_email = str(user_doc.get("email", "")).lower()
                        if doc_email.startswith("admin"):
                            is_admin = True
                    if not is_admin:
                        doc_role = str(user_doc.get("role", "")).lower()
                        if doc_role == "admin":
                            is_admin = True
                    if not is_admin:
                        doc_roles = user_doc.get("roles", [])
                        if isinstance(doc_roles, list) and "admin" in [str(r).lower() for r in doc_roles]:
                            is_admin = True

            return {"user_id": user_id, "is_admin": is_admin}
        except Exception:
            return None

    def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    ) -> str:
        return get_current_user_data(credentials)["user_id"]

    @router.post("/upload")
    def post_upload(
        file: UploadFile = File(...),
        folder: Optional[str] = Query(None),
        folder_form: Optional[str] = Form(None, alias="folder"),
        id: Optional[str] = Query(None),
        id_form: Optional[str] = Form(None, alias="id"),
        user_id: str = Depends(get_current_user_id),
    ):
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        if "." in (file.filename or ""):
            extension = file.filename.split(".")[-1].lower()
        else:
            guessed_ext = mimetypes.guess_extension(file.content_type or "")
            extension = guessed_ext.lstrip(".").lower() if guessed_ext else "jpg"

        # Rechazar archivos ejecutables
        if extension in DISALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido: los ejecutables (.{extension}) estan restringidos.",
            )

        raw_folder = folder or folder_form or "user"
        clean_folder = raw_folder.strip().strip("/").lower()
        if not clean_folder:
            clean_folder = "user"

        raw_id = id or id_form
        clean_id = raw_id.strip().strip("/") if raw_id else None

        if clean_id:
            target_id = clean_id
            image_uuid = f"{clean_folder}/{target_id}/{uuid.uuid4()}.{extension}"
        else:
            target_id = "temp"
            image_uuid = f"temp/{clean_folder}/{uuid.uuid4()}.{extension}"

        active_provider = get_active_storage_provider()
        secure_url = ""

        try:
            if active_provider == "cloudinary":
                if not HAS_CLOUDINARY:
                    raise HTTPException(
                        status_code=500,
                        detail="Librería 'cloudinary' no instalada. Ejecuta: pip install cloudinary",
                    )
                if not init_cloudinary():
                    raise HTTPException(
                        status_code=500,
                        detail="Faltan credenciales de Cloudinary (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)",
                    )
                file.file.seek(0)
                clean_public_id = image_uuid.rsplit(".", 1)[0]
                upload_res = cloudinary.uploader.upload(
                    file.file,
                    public_id=clean_public_id,
                    resource_type="auto",
                    overwrite=True,
                )
                image_uuid = upload_res.get("public_id") or clean_public_id
                secure_url = upload_res.get("secure_url") or ""
            else:
                s3_client = cargar_minio_client()
                MINIO_BUCKET_ORIGINAL = os.getenv("MINIO_BUCKET_ORIGINALS", bucket_originals)

                s3_client.upload_fileobj(
                    file.file,
                    MINIO_BUCKET_ORIGINAL,
                    image_uuid,
                    ExtraArgs={"ContentType": file.content_type},
                )

            if db is not None:
                record = {
                    "image_id": image_uuid,
                    "file_id": image_uuid,
                    "owner_id": user_id,
                    "entity_id": target_id,
                    "folder": clean_folder,
                    "class_name": clean_folder,
                    "filename": file.filename,
                    "provider": active_provider,
                    "secure_url": secure_url,
                    "created_at": datetime.now(timezone.utc),
                }
                db[collection_name].insert_one(record)
                if collection_name != "user_photos":
                    db["user_photos"].insert_one(record)

            return JSONResponse(
                {
                    "id": image_uuid,
                    "path": image_uuid,
                    "image_url": secure_url or image_uuid,
                    "url": secure_url or image_uuid,
                    "folder": clean_folder,
                    "entity_id": target_id,
                    "provider": active_provider,
                },
                status_code=201,
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"STORAGE ERROR ({active_provider}): {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload image to {active_provider.capitalize()}: {str(e)}")

    @router.post("/upload/confirm-temp")
    def post_confirm_temp(
        source_key: str = Body(..., embed=True),
        entity_id: str = Body(..., embed=True),
        folder: Optional[str] = Body(None, embed=True),
        user_data: dict = Depends(get_current_user_data),
    ):
        clean_source = source_key.strip().lstrip("/")
        clean_entity_id = entity_id.strip().strip("/")
        if not (clean_source.startswith("temp/") or clean_source.startswith("tmp/")):
            return JSONResponse({"id": clean_source, "status": "already_permanent"}, status_code=200)

        parts = clean_source.split("/")
        class_folder = folder.strip().strip("/").lower() if folder else (parts[1] if len(parts) > 2 else "files")
        filename = parts[-1]
        target_key = f"{class_folder}/{clean_entity_id}/{filename}"

        try:
            active_provider = get_active_storage_provider()
            existing_rec = None
            if db is not None:
                existing_rec = db[collection_name].find_one(
                    {"$or": [{"image_id": clean_source}, {"file_id": clean_source}]}
                )
            if existing_rec and existing_rec.get("provider"):
                active_provider = existing_rec.get("provider")

            if active_provider == "cloudinary":
                if HAS_CLOUDINARY and init_cloudinary():
                    try:
                        clean_src_pid = clean_source.rsplit(".", 1)[0]
                        clean_tgt_pid = target_key.rsplit(".", 1)[0]
                        cloudinary.uploader.rename(clean_src_pid, clean_tgt_pid, overwrite=True)
                    except Exception:
                        pass
            else:
                s3_client = cargar_minio_client()
                MINIO_BUCKET_ORIGINAL = os.getenv("MINIO_BUCKET_ORIGINALS", bucket_originals)
                s3_client.copy_object(
                    Bucket=MINIO_BUCKET_ORIGINAL,
                    CopySource={"Bucket": MINIO_BUCKET_ORIGINAL, "Key": clean_source},
                    Key=target_key,
                )
                s3_client.delete_object(Bucket=MINIO_BUCKET_ORIGINAL, Key=clean_source)

            if db is not None:
                update_fields = {
                    "$set": {
                        "image_id": target_key,
                        "file_id": target_key,
                        "entity_id": clean_entity_id,
                        "folder": class_folder,
                        "class_name": class_folder,
                    }
                }
                db[collection_name].update_one(
                    {"$or": [{"image_id": clean_source}, {"file_id": clean_source}]},
                    update_fields,
                )
                if collection_name != "user_photos":
                    db["user_photos"].update_one(
                        {"$or": [{"image_id": clean_source}, {"file_id": clean_source}]},
                        update_fields,
                    )

            return JSONResponse(
                {
                    "id": target_key,
                    "path": target_key,
                    "image_url": target_key,
                    "url": target_key,
                    "folder": class_folder,
                    "entity_id": clean_entity_id,
                    "status": "moved",
                },
                status_code=200,
            )
        except Exception as e:
            print(f"ERROR CONFIRM TEMP: {e}")
            raise HTTPException(status_code=500, detail=f"Error confirming temp file: {str(e)}")

    @router.get("/download/{image_id:path}")
    def get_download(
        image_id: str,
        request: Request,
        raw: Optional[bool] = Query(False, description="Entregar los bytes de la imagen directamente (Streaming)"),
        folder: Optional[str] = Query(None),
        width: Optional[int] = Query(None, description="Ancho de la imagen (imgproxy)"),
        height: Optional[int] = Query(None, description="Alto de la imagen (imgproxy)"),
        resizing_type: Optional[str] = Query(None, description="Modo: fit, fill, auto, fill-down, force"),
        gravity: Optional[str] = Query(None, description="Gravedad/enfoque para recorte: ce, sm, no, so, ea, we"),
        format: Optional[str] = Query(None, description="Formato de salida: webp, png, jpeg, avif"),
        quality: Optional[int] = Query(None, description="Calidad de imagen (1-100)"),
        enlarge: Optional[int] = Query(0, description="Permitir ampliar la imagen (0 o 1)"),
        redirect: Optional[bool] = Query(False, description="Redirigir directamente a la URL de imagen"),
        user_data: Optional[dict] = Depends(get_current_user_data_optional),
    ):
        current_user_id = user_data["user_id"] if user_data else ""
        is_admin = user_data["is_admin"] if user_data else False

        clean_image_id = image_id.lstrip("/")
        if "$query" in clean_image_id:
            clean_image_id = clean_image_id.replace("$query", "")
        if clean_image_id.endswith("$"):
            clean_image_id = clean_image_id[:-1]

        is_transform_requested = any([
            width is not None,
            height is not None,
            resizing_type is not None,
            gravity is not None,
            format is not None,
            quality is not None,
        ])

        # 1. Buscar metadatos en MongoDB
        photo = None
        if db is not None:
            photo = db[collection_name].find_one(
                {"$or": [{"image_id": clean_image_id}, {"file_id": clean_image_id}]}
            )
            if not photo and collection_name != "user_photos":
                photo = db["user_photos"].find_one(
                    {"$or": [{"image_id": clean_image_id}, {"file_id": clean_image_id}]}
                )

            # Si no se encuentra y se especifico carpeta, intentar con prefijo de carpeta
            if not photo and folder and not clean_image_id.startswith(f"{folder.strip('/')}/"):
                candidate_id = f"{folder.strip('/')}/{clean_image_id}"
                photo = db[collection_name].find_one(
                    {"$or": [{"image_id": candidate_id}, {"file_id": candidate_id}]}
                )
                if not photo and collection_name != "user_photos":
                    photo = db["user_photos"].find_one(
                        {"$or": [{"image_id": candidate_id}, {"file_id": candidate_id}]}
                    )
                if photo:
                    clean_image_id = candidate_id

            # Si aun no se encuentra y no contiene barra, buscar por filename o terminacion de id
            if not photo and "/" not in clean_image_id:
                query_cond = {
                    "$or": [
                        {"filename": clean_image_id},
                        {"image_id": {"$regex": f"{re.escape(clean_image_id)}$"}},
                        {"file_id": {"$regex": f"{re.escape(clean_image_id)}$"}},
                    ]
                }
                photo = db[collection_name].find_one(query_cond)
                if not photo and collection_name != "user_photos":
                    photo = db["user_photos"].find_one(query_cond)
                if photo:
                    clean_image_id = photo.get("image_id") or photo.get("file_id")

        file_folder = photo.get("folder") if photo else (clean_image_id.split("/")[0] if "/" in clean_image_id else "")
        if not file_folder and folder:
            file_folder = folder.strip("/").lower()

        if file_folder in ["users", "user"] or clean_image_id.startswith("users/") or clean_image_id.startswith("user/"):
            owner_id = str(photo.get("owner_id")) if (photo and photo.get("owner_id")) else None
            entity_id = str(photo.get("entity_id")) if (photo and photo.get("entity_id")) else None
            path_user_id = None
            if clean_image_id.startswith("users/") or clean_image_id.startswith("user/"):
                parts = clean_image_id.split("/")
                if len(parts) >= 2:
                    path_user_id = parts[1]

            is_authorized = (
                is_admin
                or (current_user_id and current_user_id in [owner_id, entity_id, path_user_id])
            )

            if not is_authorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acceso denegado: Solo el propietario o un administrador pueden acceder a esta imagen",
                )

        active_provider = get_active_storage_provider()
        image_provider = active_provider

        if photo and photo.get("provider"):
            image_provider = photo.get("provider")
        elif "res.cloudinary.com" in clean_image_id:
            image_provider = "cloudinary"
        elif "/" in clean_image_id and (clean_image_id.startswith("activity/") or clean_image_id.startswith("users/") or clean_image_id.startswith("temp/")):
            if not photo or photo.get("provider") != "cloudinary":
                image_provider = "minio"

        try:
            if image_provider == "cloudinary" and HAS_CLOUDINARY and init_cloudinary():
                target_public_id = photo.get("file_id") if photo else clean_image_id
                target_cloudinary_url = generar_cloudinary_url(
                    public_id=target_public_id,
                    width=width,
                    height=height,
                    resizing_type=resizing_type,
                    gravity=gravity,
                    format=format,
                    quality=quality,
                )
                original_cloudinary_url = (photo.get("secure_url") if photo else None) or generar_cloudinary_url(public_id=target_public_id)

                if raw or redirect:
                    return RedirectResponse(
                        url=target_cloudinary_url if is_transform_requested else original_cloudinary_url,
                        status_code=307,
                    )

                return JSONResponse(
                    {
                        "url": target_cloudinary_url if is_transform_requested else original_cloudinary_url,
                        "original_url": original_cloudinary_url,
                        "provider": "cloudinary",
                        "expires_in": 86400,
                    },
                    status_code=200,
                )
                
            MINIO_BUCKET_ORIGINAL = os.getenv("MINIO_BUCKET_ORIGINALS", bucket_originals)

            # Si se solicita la imagen directa (raw=True)
            if raw:
                # 4.1. Si se pidio transformacion, obtenerla de imgproxy internamente
                if is_transform_requested:
                    target_imgproxy_url = generar_imgproxy_url(
                        source_url=f"s3://{MINIO_BUCKET_ORIGINAL}/{clean_image_id}",
                        width=width,
                        height=height,
                        resizing_type=resizing_type,
                        gravity=gravity,
                        format=format,
                        quality=quality,
                        enlarge=enlarge or 0,
                        base_url=IMGPROXY_INTERNAL_URL,
                    )
                    try:
                        resp = fetch_imgproxy_stream(target_imgproxy_url)
                        content_type = resp.headers.get("Content-Type", f"image/{format or 'jpeg'}")
                        filename = clean_image_id.split("/")[-1]
                        if format and "." in filename:
                            filename = f"{filename.rsplit('.', 1)[0]}.{format.lstrip('.')}"
                        return StreamingResponse(
                            resp,
                            media_type=content_type,
                            headers={
                                "Cache-Control": "public, max-age=86400",
                                "Content-Disposition": f'inline; filename="{filename}"',
                            },
                        )
                    except Exception as e:
                        print(f"Error fetching from imgproxy ({target_imgproxy_url}): {e}")
                        # Fallback a IMGPROXY_BASE_URL si IMGPROXY_INTERNAL_URL no respondio (por ejemplo en desarrollo local fuera de Docker)
                        if IMGPROXY_BASE_URL and IMGPROXY_BASE_URL.rstrip('/') != IMGPROXY_INTERNAL_URL.rstrip('/'):
                            try:
                                fallback_url = generar_imgproxy_url(
                                    source_url=f"s3://{MINIO_BUCKET_ORIGINAL}/{clean_image_id}",
                                    width=width,
                                    height=height,
                                    resizing_type=resizing_type,
                                    gravity=gravity,
                                    format=format,
                                    quality=quality,
                                    enlarge=enlarge or 0,
                                    base_url=IMGPROXY_BASE_URL,
                                )
                                resp = fetch_imgproxy_stream(fallback_url)
                                content_type = resp.headers.get("Content-Type", f"image/{format or 'jpeg'}")
                                filename = clean_image_id.split("/")[-1]
                                if format and "." in filename:
                                    filename = f"{filename.rsplit('.', 1)[0]}.{format.lstrip('.')}"
                                return StreamingResponse(
                                    resp,
                                    media_type=content_type,
                                    headers={
                                        "Cache-Control": "public, max-age=86400",
                                        "Content-Disposition": f'inline; filename="{filename}"',
                                    },
                                )
                            except Exception as e2:
                                print(f"Error fetching from fallback imgproxy ({IMGPROXY_BASE_URL}): {e2}")

                # 4.2. Si no hay transformacion o fallo imgproxy, entregar original directamente desde MinIO
                try:
                    s3_client = cargar_minio_client()
                    s3_obj = s3_client.get_object(Bucket=MINIO_BUCKET_ORIGINAL, Key=clean_image_id)
                    content_type = s3_obj.get("ContentType", "image/jpeg")
                    filename = clean_image_id.split("/")[-1]
                    return StreamingResponse(
                        s3_obj["Body"].iter_chunks(),
                        media_type=content_type,
                        headers={
                            "Cache-Control": "public, max-age=86400",
                            "Content-Disposition": f'inline; filename="{filename}"',
                        },
                    )
                except Exception as e:
                    raise HTTPException(status_code=404, detail=f"Imagen no encontrada: {e}")

            # 4.3. Si raw=False, devolver la URL limpia de la propia API
            query_params = ["raw=true"]
            if width is not None: query_params.append(f"width={width}")
            if height is not None: query_params.append(f"height={height}")
            if resizing_type: query_params.append(f"resizing_type={resizing_type}")
            if gravity: query_params.append(f"gravity={gravity}")
            if format: query_params.append(f"format={format}")
            if quality: query_params.append(f"quality={quality}")
            if enlarge: query_params.append(f"enlarge={enlarge}")

            # Obtener token de la petición actual para incluirlo en la URL devuelta a Image.network
            auth_header = request.headers.get("authorization", "") if request else ""
            raw_token = ""
            if auth_header.lower().startswith("bearer "):
                raw_token = auth_header[7:].strip()
            elif request and "token" in request.query_params:
                raw_token = request.query_params.get("token", "")

            if raw_token:
                query_params.append(f"token={raw_token}")

            qs = "&".join(query_params)
            base_api = str(request.base_url).rstrip('/') if request else ""
            clean_url = f"{base_api}/download/{clean_image_id}?{qs}"
            clean_original_url = f"{base_api}/download/{clean_image_id}?raw=true" + (f"&token={raw_token}" if raw_token else "")

            if redirect:
                return RedirectResponse(url=clean_url, status_code=307)

            return JSONResponse(
                {
                    "url": clean_url if is_transform_requested else clean_original_url,
                    "original_url": clean_original_url,
                    "expires_in": 86400,
                },
                status_code=200,
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"ERROR EN DOWNLOAD: {e}")
            raise HTTPException(status_code=500, detail="Error al generar acceso a la imagen")


    @router.get("/admin/files/explorer")
    def get_backoffice_files_explorer(
        bucket: str = "originals",
        prefix: str = "",
        recursive: bool = True,
        user_data: dict = Depends(get_current_user_data),
    ):
        # 1. Seguridad: Solo administradores de backoffice
        if not user_data.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso restringido: Se requieren permisos de administrador de backoffice",
            )

        # 2. Si el proveedor activo es Cloudinary, explorar recursos de Cloudinary
        active_provider = get_active_storage_provider()
        if active_provider == "cloudinary":
            if not HAS_CLOUDINARY:
                raise HTTPException(
                    status_code=500,
                    detail="Librería 'cloudinary' no instalada.",
                )
            if not init_cloudinary():
                raise HTTPException(
                    status_code=500,
                    detail="Faltan credenciales de Cloudinary.",
                )

            clean_prefix = prefix.strip().strip("/")
            folders = []
            files = []

            # 1. Intentar obtener carpetas desde Cloudinary API
            try:
                if clean_prefix:
                    f_res = cloudinary.api.subfolders(clean_prefix)
                else:
                    f_res = cloudinary.api.root_folders()
                folders = [f["name"] + "/" for f in f_res.get("folders", [])]
            except Exception:
                pass

            # 2. Obtener recursos desde Cloudinary API
            resources = []
            try:
                res_params = {"type": "upload", "max_results": 500}
                if clean_prefix:
                    res_params["prefix"] = clean_prefix
                c_res = cloudinary.api.resources(**res_params)
                resources = c_res.get("resources", [])
            except Exception:
                if db is not None:
                    mongo_query = {"provider": "cloudinary"}
                    if clean_prefix:
                        mongo_query["$or"] = [
                            {"image_id": {"$regex": f"^{re.escape(clean_prefix)}"}},
                            {"file_id": {"$regex": f"^{re.escape(clean_prefix)}"}},
                            {"folder": clean_prefix},
                        ]
                    for doc in db[collection_name].find(mongo_query):
                        resources.append({
                            "public_id": doc.get("image_id") or doc.get("file_id"),
                            "format": (doc.get("filename") or "").split(".")[-1] if "." in (doc.get("filename") or "") else "jpg",
                            "bytes": 0,
                            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                            "secure_url": doc.get("secure_url") or "",
                        })

            # Extraer subcarpetas implícitas si folders está vacío y no es recursivo
            if not recursive and clean_prefix:
                subfolder_set = set(folders)
                prefix_with_slash = f"{clean_prefix}/"
                for item in resources:
                    pid = item.get("public_id", "")
                    if pid.startswith(prefix_with_slash):
                        rel = pid[len(prefix_with_slash):]
                        if "/" in rel:
                            subfolder_set.add(rel.split("/")[0] + "/")
                folders = sorted(list(subfolder_set))
            elif not recursive and not clean_prefix:
                subfolder_set = set(folders)
                for item in resources:
                    pid = item.get("public_id", "")
                    if "/" in pid:
                        subfolder_set.add(pid.split("/")[0] + "/")
                folders = sorted(list(subfolder_set))

            pids = [r.get("public_id") for r in resources if r.get("public_id")]
            db_records = {}
            if pids and db is not None:
                for col in [collection_name, "user_photos"]:
                    for doc in db[col].find(
                        {"$or": [{"image_id": {"$in": pids}}, {"file_id": {"$in": pids}}]}
                    ):
                        k = doc.get("image_id") or doc.get("file_id")
                        if k and k not in db_records:
                            db_records[k] = doc

            for item in resources:
                pid = item.get("public_id", "")
                fmt = item.get("format", "")
                full_filename = (db_records.get(pid, {}).get("filename")) or (pid.split("/")[-1] + (f".{fmt}" if fmt and not pid.endswith(f".{fmt}") else ""))
                preview_url = item.get("secure_url") or item.get("url") or generar_cloudinary_url(pid)
                created_at_val = item.get("created_at")
                if isinstance(created_at_val, datetime):
                    created_at_val = created_at_val.isoformat()

                if not recursive:
                    if clean_prefix:
                        rel = pid[len(clean_prefix):].lstrip("/")
                        if "/" in rel:
                            continue
                    elif "/" in pid:
                        continue

                files.append(
                    {
                        "id": pid,
                        "key": pid,
                        "filename": full_filename,
                        "size": item.get("bytes", 0),
                        "last_modified": created_at_val,
                        "owner_id": db_records.get(pid, {}).get("owner_id"),
                        "created_at_db": (
                            db_records.get(pid, {}).get("created_at").isoformat()
                            if db_records.get(pid, {}).get("created_at")
                            else None
                        ),
                        "preview_url": preview_url,
                        "url": preview_url,
                    }
                )

            return JSONResponse(
                {
                    "bucket": "cloudinary",
                    "current_prefix": prefix,
                    "folders": folders,
                    "total_files": len(files),
                    "files": files,
                    "items": files,
                },
                status_code=200,
            )

        # 3. Proveedor MinIO / S3
        allowed_buckets = [
            os.getenv("MINIO_BUCKET_ORIGINALS", bucket_originals),
            os.getenv("MINIO_BUCKET_PUBLIC", "public"),
            os.getenv("MINIO_BUCKET_PROCESSED", "processed"),
        ]
        if bucket not in allowed_buckets:
            bucket = allowed_buckets[0]

        try:
            s3_client = cargar_minio_client()
            s3_public_client = cargar_public_minio_client()

            list_params = {"Bucket": bucket, "Prefix": prefix}
            if not recursive:
                list_params["Delimiter"] = "/"

            response = s3_client.list_objects_v2(**list_params)

            folders = [cp["Prefix"] for cp in response.get("CommonPrefixes", [])]
            contents = response.get("Contents", [])

            file_keys = [item["Key"] for item in contents if not item["Key"].endswith("/")]
            db_records = {}
            if file_keys and db is not None:
                for col in [collection_name, "user_photos"]:
                    for doc in db[col].find(
                        {"$or": [{"image_id": {"$in": file_keys}}, {"file_id": {"$in": file_keys}}]}
                    ):
                        k = doc.get("image_id") or doc.get("file_id")
                        if k and k not in db_records:
                            db_records[k] = doc

            files = []
            for item in contents:
                key = item["Key"]
                if key.endswith("/"):
                    continue

                presigned_url = s3_public_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=3600,
                )

                meta = db_records.get(key, {})

                files.append(
                    {
                        "id": key,
                        "key": key,
                        "filename": meta.get("filename") or key.split("/")[-1],
                        "size": item["Size"],
                        "last_modified": item["LastModified"].isoformat(),
                        "owner_id": meta.get("owner_id"),
                        "created_at_db": (
                            meta.get("created_at").isoformat() if meta.get("created_at") else None
                        ),
                        "preview_url": presigned_url,
                        "url": presigned_url,
                    }
                )

            return JSONResponse(
                {
                    "bucket": bucket,
                    "current_prefix": prefix,
                    "folders": folders,
                    "total_files": len(files),
                    "files": files,
                    "items": files,
                },
                status_code=200,
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"ERROR BACKOFFICE EXPLORER: {e}")
            raise HTTPException(status_code=500, detail=f"Error en explorador de archivos: {str(e)}")

    @router.delete("/download/{image_id:path}")
    def delete_file(
        image_id: str,
        folder: Optional[str] = Query(None),
        user_data: dict = Depends(get_current_user_data),
    ):
        current_user_id = user_data["user_id"]
        is_admin = user_data["is_admin"]

        clean_image_id = image_id.lstrip("/")

        # 1. Buscar metadatos en MongoDB si db está disponible
        photo = None
        if db is not None:
            photo = db[collection_name].find_one(
                {"$or": [{"image_id": clean_image_id}, {"file_id": clean_image_id}]}
            )
            if not photo and collection_name != "user_photos":
                photo = db["user_photos"].find_one(
                    {"$or": [{"image_id": clean_image_id}, {"file_id": clean_image_id}]}
                )

            if not photo and folder and not clean_image_id.startswith(f"{folder.strip('/')}/"):
                candidate_id = f"{folder.strip('/')}/{clean_image_id}"
                photo = db[collection_name].find_one(
                    {"$or": [{"image_id": candidate_id}, {"file_id": candidate_id}]}
                )
                if not photo and collection_name != "user_photos":
                    photo = db["user_photos"].find_one(
                        {"$or": [{"image_id": candidate_id}, {"file_id": candidate_id}]}
                    )
                if photo:
                    clean_image_id = candidate_id

        file_folder = photo.get("folder") if photo else (clean_image_id.split("/")[0] if "/" in clean_image_id else "")
        if not file_folder and folder:
            file_folder = folder.strip("/").lower()

        # 2. Control de permisos
        if file_folder in ["users", "user"] or clean_image_id.startswith("users/"):
            owner_id = photo.get("owner_id") if photo else None
            if not owner_id and clean_image_id.startswith("users/"):
                parts = clean_image_id.split("/")
                if len(parts) >= 2:
                    owner_id = parts[1]

            if not is_admin and owner_id and owner_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acceso denegado: No eres el propietario de esta imagen",
                )

        # 3. Eliminar del proveedor correspondiente (Cloudinary o MinIO) y de MongoDB
        try:
            image_provider = photo.get("provider") if photo else get_active_storage_provider()
            if image_provider == "cloudinary":
                if HAS_CLOUDINARY and init_cloudinary():
                    try:
                        clean_pid = (photo.get("file_id") if photo else clean_image_id).rsplit(".", 1)[0]
                        cloudinary.uploader.destroy(clean_pid)
                    except Exception as e:
                        print(f"ERROR BORRANDO CLOUDINARY: {e}")
            else:
                s3_client = cargar_minio_client()
                MINIO_BUCKET_ORIGINAL = os.getenv("MINIO_BUCKET_ORIGINALS", bucket_originals)
                s3_client.delete_object(Bucket=MINIO_BUCKET_ORIGINAL, Key=clean_image_id)

            if db is not None:
                db[collection_name].delete_one(
                    {"$or": [{"image_id": clean_image_id}, {"file_id": clean_image_id}]}
                )
                if collection_name != "user_photos":
                    db["user_photos"].delete_one(
                        {"$or": [{"image_id": clean_image_id}, {"file_id": clean_image_id}]}
                    )

            return JSONResponse(
                {"message": "Archivo eliminado con éxito", "id": clean_image_id},
                status_code=200,
            )
        except Exception as e:
            print(f"ERROR BORRANDO ARCHIVO: {e}")
            raise HTTPException(status_code=500, detail=f"Error al eliminar archivo: {str(e)}")

    return router