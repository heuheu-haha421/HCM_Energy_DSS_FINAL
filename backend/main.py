import asyncio
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from init_db import InitDataBase
from app.api import register_routers
from app.errors import AppException

from app.core import Prediction


# ======================
# LIFESPAN
# ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    db           = InitDataBase.init_db()
    app.state.db = db

    loop = asyncio.get_event_loop()

    manager    = register_routers(app)
    prediction = Prediction(db, manager, loop)
    
    app.state.predictor = prediction

    yield

    if prediction.bRun:
        prediction.stop()

    db.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ======================
# APP EXCEPTION HANDLER
# ======================
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):

    return JSONResponse(
        status_code = exc.status_code,
        content     = {
            "success"    : False,
            "error"      : exc.message,
            "code"       : exc.code,
            "status_code": exc.status_code
        }
    )

# ======================
# GLOBAL EXCEPTION HANDLER
# ======================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    return JSONResponse(
        status_code = 500,
        content     = {
            "success"    : False,
            "error"      : "Internal Server Error",
            "status_code": 500
        }
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
