from fastapi import FastAPI

app = FastAPI()


@app.get("/items/{item_id}", name="get_item")
def read_item(item_id: int):
    return {"item_id": item_id}


@app.post("/users/", name="create_user")
def create_user(username: str):
    return {"username": username}
