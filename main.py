from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import db_helper

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class WebhookRequest(BaseModel):
    responseId: str
    queryResult: dict


def handle_order_add(params: dict, session_id: str):
    # Your logic to handle order.add intent
    return f"Adding {params['item']} to order for session {session_id}"


def handle_order_remove(params: dict, session_id: str):
    # Your logic to handle order.remove intent
    return f"Removing {params['item']} from order for session {session_id}"


@app.post("/webhook")
async def webhook_handler(request: WebhookRequest):
    query_result = request.queryResult
    intent_name = query_result["intent"]["displayName"]
    session_id = (
        query_result.get("outputContexts",
                         [{}])[0].get("name", "").split("/")[-1]
    )

    if intent_name == "order.add":
        params = query_result["parameters"]
        return {"fulfillmentText": handle_order_add(params, session_id)}
    elif intent_name == "order.remove":
        params = query_result["parameters"]
        return {"fulfillmentText": handle_order_remove(params, session_id)}
    elif intent_name == "track.order - context: ongoing-tracking":
        params = query_result["parameters"]
        return {"fulfillmentText": track_order(params)}

    else:
        raise HTTPException(status_code=400, detail="Invalid intent")


def track_order(params: dict):
    order_id = int(params["number"])
    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fullfillmentText = (
            f"Your order status for order id {order_id} is: {order_status}"
        )
    else:
        fullfillmentText = f"Sorry, no order found for order id: {order_id}"
    return fullfillmentText


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
