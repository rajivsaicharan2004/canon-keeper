from fastapi import FastAPI

app = FastAPI(title="Canon Keeper API")

@app.get("/")
def read_root():
    return {"message": "Canon Keeper backend is running"}
