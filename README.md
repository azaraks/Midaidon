
## Introduction
This tool automates the process of bulk-writing GitHub issues, a functionality not supported by GitHub's web UI.

## Requirements
This application is containerized for easy deployment using Docker.
If you don't want to use Docker, install Redis and Python 3.9 on your machine.

## Installation
First, modify `.env.sample` with your configuration details and rename it to `.env`.
Then, deploy the application using one of the following methods.

### Docker
Run the following command to build and start the application using Docker Compose:
```bash
docker compose build
docker compose up -d
```

### Local Machine
Ensure your Redis server is running.
Update `REDIS_HOST` and `REDIS_PORT` in the `.env` file to match your Redis server's settings.
Then, install the dependencies and start the application:
```bash
pip install -r requirements.txt
uvicorn main:app --host "0.0.0.0"
```

## Usage
Navigate to `http://localhost:8000` in your web browser (replace 'localhost' with your machine's IP address if necessary). 
Then type your repository as `author/repository` form, and upload your issue file (in CSV, JSON, XLSX, or XML format).
Push submit to create GitHub issues. You'll see the progress on the screen.

## TODO
- [ ] Automatically retrieve the repository list from the user's account
- [ ] Implement CSS for better UI design
- [ ] Add functionality to assign labels to issues
