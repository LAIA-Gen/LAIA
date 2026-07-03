from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
import boto3
from botocore.client import Config
from io import BytesIO

def CRUDStorageController(
    endpoint_url: str,
    access_key: str,
    secret_key: str,
):
    """
    Devuelve un router FastAPI con CRUD sobre objetos de MinIO/S3.
    El bucket se recibe como parámetro en la ruta.
    """
    router = APIRouter(tags=["Storage"])

    # Cliente S3
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
    )

    @router.get("/storage/{bucket}", response_model=List[dict])
    async def list_objects(bucket: str):
        """Lista objetos del bucket especificado."""
        try:
            resp = s3.list_objects_v2(Bucket=bucket)
            contents = []
            if "Contents" in resp:
                for obj in resp["Contents"]:
                    contents.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"]
                    })
            return contents
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/storage/{bucket}/upload")
    async def upload_object(bucket: str, file: UploadFile = File(...)):
        """Sube un archivo al bucket especificado."""
        try:
            body = await file.read()
            key = file.filename
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=file.content_type
            )
            return {"message": f"Archivo '{file.filename}' subido con éxito a '{bucket}'", "key": key}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/storage/{bucket}/download/{key:path}")
    async def download_object(bucket: str, key: str):
        """Descarga un objeto del bucket especificado."""
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            file_data = obj["Body"].read()
            return StreamingResponse(
                BytesIO(file_data),
                media_type=obj.get("ContentType", "application/octet-stream"),
                headers={"Content-Disposition": f"attachment; filename={key}"}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/storage/{bucket}/{key:path}")
    async def delete_object(bucket: str, key: str):
        """Borra un objeto del bucket especificado."""
        try:
            s3.delete_object(Bucket=bucket, Key=key)
            return {"message": f"Objeto '{key}' borrado con éxito del bucket '{bucket}'"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router