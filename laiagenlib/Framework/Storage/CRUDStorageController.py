import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional, List

import boto3
from botocore.client import Config
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import (APIRouter, Body, Depends, File, Form, HTTPException, Query, Security, UploadFile, status)
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

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
):
    """
    Controlador de almacenamiento para LAIA con las funciones y endpoints de MinIO:
    - cargar_minio_client()
    - cargar_public_minio_client()
    - get_current_user_data()
    - get_current_user_id()
    - POST /upload
    - POST /upload/confirm-temp
    - GET /download/{image_id:path}
    - GET /admin/files/explorer
    - Operaciones básicas /storage/{bucket}
    """
    router = APIRouter(tags=["Storage"])

    backend_jwt_secret_key = jwtSecretKey
    collection_name = storage_collection or os.getenv("STORAGE_COLLECTION", "user_photos")

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

        raw_folder = folder or folder_form or "users"
        clean_folder = raw_folder.strip().strip("/").lower()
        if not clean_folder:
            clean_folder = "users"

        raw_id = id or id_form
        clean_id = raw_id.strip().strip("/") if raw_id else None

        if clean_folder in ["users", "user"]:
            target_id = clean_id or user_id
            image_uuid = f"users/{target_id}/{uuid.uuid4()}.{extension}"
        else:
            if clean_id:
                target_id = clean_id
                image_uuid = f"{clean_folder}/{target_id}/{uuid.uuid4()}.{extension}"
            else:
                target_id = "temp"
                image_uuid = f"temp/{clean_folder}/{uuid.uuid4()}.{extension}"

        try:
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
                    "created_at": datetime.now(timezone.utc),
                }
                db[collection_name].insert_one(record)
                if collection_name != "user_photos":
                    db["user_photos"].insert_one(record)

            return JSONResponse(
                {
                    "id": image_uuid,
                    "path": image_uuid,
                    "image_url": image_uuid,
                    "url": image_uuid,
                    "folder": clean_folder,
                    "entity_id": target_id,
                },
                status_code=201,
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"MINIO ERROR: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload image to MinIO")

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
        folder: Optional[str] = Query(None),
        user_data: dict = Depends(get_current_user_data),
    ):
        current_user_id = user_data["user_id"]
        is_admin = user_data["is_admin"]

        clean_image_id = image_id.lstrip("/")

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

        # 2. Determinar la carpeta / clase
        file_folder = photo.get("folder") if photo else (clean_image_id.split("/")[0] if "/" in clean_image_id else "")
        if not file_folder and folder:
            file_folder = folder.strip("/").lower()

        # 3. Control de permisos:
        # Solo para fotos privadas de usuario ('users') se exige ser propietario o admin.
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

        # 4. Generar URL prefirmada
        try:
            MINIO_BUCKET_ORIGINAL = os.getenv("MINIO_BUCKET_ORIGINALS", bucket_originals)

            if not photo:
                s3_internal = cargar_minio_client()
                try:
                    s3_internal.head_object(Bucket=MINIO_BUCKET_ORIGINAL, Key=clean_image_id)
                except Exception:
                    raise HTTPException(status_code=404, detail="Imagen no encontrada")

            s3_public_client = cargar_public_minio_client()
            presigned_url = s3_public_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": MINIO_BUCKET_ORIGINAL, "Key": clean_image_id},
                ExpiresIn=900,
            )

            return JSONResponse({"url": presigned_url, "expires_in": 900}, status_code=200)
        except HTTPException:
            raise
        except Exception as e:
            print(f"ERROR GENERANDO PRESIGNED URL: {e}")
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

        # 2. Validar que el bucket solicitado exista/esté permitido
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

        # 3. Eliminar de MinIO y de MongoDB
        try:
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