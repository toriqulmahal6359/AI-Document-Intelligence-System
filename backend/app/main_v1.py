from fastapi import FastAPI
from app.api.document import router as documents_router

app = FastAPI(
    title="AI-Powered Document Intelligence System",
    description="Business document processing and financial intelligence",
    version="1.0.0",
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
