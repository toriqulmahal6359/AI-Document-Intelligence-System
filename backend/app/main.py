from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from app.api.document import router as documents_router

app = FastAPI(
    title="AI-Powered Document Intelligence System",
    description="Business document processing and financial intelligence",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "application": "Document Intelligence System",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(documents_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Make Swagger UI recognize multiple uploaded files.
    request_body = (
        openapi_schema["paths"]["/api/documents/upload"]["post"]
        ["requestBody"]["content"]["multipart/form-data"]["schema"]
    )

    schema_name = request_body["$ref"].split("/")[-1]

    files_schema = (
        openapi_schema["components"]["schemas"][schema_name]
        ["properties"]["files"]
    )

    files_schema["items"]["format"] = "binary"
    files_schema["items"].pop("contentMediaType", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
