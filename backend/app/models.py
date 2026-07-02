from pydantic import BaseModel

class DocumentRequest(BaseModel):
    path: str
