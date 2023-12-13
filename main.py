from fastapi import FastAPI, UploadFile, Form, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import logging
import dotenv
import asyncio
import httpx
from typing import Optional
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError
import pandas as pd
from pandas.errors import ParserError

dotenv.load_dotenv('.env')
logging.basicConfig(level=logging.INFO)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
http_client = httpx.AsyncClient()
redis_client: Optional[aioredis.Redis] = None


async def log_info(message):
    if redis_client:
        try:
            await redis_client.rpush('logs', message)
        except ConnectionError:
            logging.warning("Could not connect to Redis, using console logging instead")
            logging.info(message)
    else:
        logging.info(message)


async def create_issue(repo, token, title, body, assignees):
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    data = {"title": title, "body": body, "assignees": assignees}

    max_retries = 3
    num_retries = 0
    while num_retries < max_retries:
        response = await http_client.post(url, json=data, headers=headers)
        await log_info(f'Creating issue: {title} - Status: {response.status_code}')

        if response.status_code == 201:
            await log_info(f'Issue created successfully: {title}')
            return response.status_code == 201

        if response.status_code == 403 and 'X-RateLimit-Reset' in response.headers:
            reset_time = int(response.headers['X-RateLimit-Reset'])
            await log_info(f'Rate limit exceeded, waiting {reset_time} seconds')
            await asyncio.sleep(reset_time)
        else:
            await log_info(f'Error: {response.text}')
            num_retries += 1
            raise HTTPException(status_code=400, detail="Error in issue creation")

    raise HTTPException(status_code=400, detail="Error in issue creation")


@app.post("/upload/")
async def create_upload_file(file: UploadFile, repo: str = Form(...)):
    token = os.getenv("GITHUB_TOKEN")
    filename = file.filename.lower()
    reader = {
        ".csv": pd.read_csv,
        ".xlsx": pd.read_excel,
        ".json": pd.read_json,
        ".xml": pd.read_xml
    }
    try:
        if not token:
            raise HTTPException(status_code=400, detail="Missing GitHub token")

        file_extension = os.path.splitext(filename)[1]
        if file_extension in reader:
            try:
                df = await asyncio.to_thread(reader[file_extension], file.file)
            except ParserError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            await log_info(f'Unsupported file format: {filename}')
            raise HTTPException(status_code=400, detail="Unsupported file format")

        for _, row in df.iterrows():
            assignees = row['assignees'].split(',') if 'assignees' in row and row['assignees'] else []
            await create_issue(repo, token, row['title'], row['body'], assignees)

        return {"message": "Issues created successfully"}
    except Exception as e:
        await log_info(f'Error: {str(e)}')
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    last_index = -1
    while True:
        if last_index == -1:
            new_last_index, logs = await get_recent_logs(30)
        else:
            logs = await redis_client.lrange('logs', last_index + 1, -1)
            new_last_index = last_index + len(logs)
        if logs:
            await websocket.send_text('\n'.join(logs))
            last_index = new_last_index
        await asyncio.sleep(1)


async def get_recent_logs(n):
    total = await redis_client.llen('logs')
    start = max(0, total - n)
    logs = await redis_client.lrange('logs', start, -1)
    return start + len(logs), logs


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
async def startup_event():
    global redis_client
    redis_client = aioredis.Redis(host=os.getenv("REDIS_HOST"),
                                  port=os.getenv("REDIS_PORT"),
                                  encoding="utf-8", decode_responses=True)


@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()
    await http_client.aclose()
