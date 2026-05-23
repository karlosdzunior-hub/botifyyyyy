import os
import httpx
import json
import base64

RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"


def get_headers():
    return {
        "Authorization": f"Bearer {os.getenv('RAILWAY_API_TOKEN')}",
        "Content-Type": "application/json",
    }


async def deploy_bot(bot_name: str, bot_code: str, bot_token: str) -> dict:
    project_id = os.getenv("RAILWAY_PROJECT_ID")

    async with httpx.AsyncClient(timeout=60) as client:
        service_id = await _create_service(client, project_id, bot_name)
        await _set_env_variable(client, service_id, project_id, "BOT_TOKEN", bot_token)
        await _upload_code(client, service_id, bot_code)

        return {
            "service_id": service_id,
            "service_name": bot_name,
            "dashboard_url": f"https://railway.app/project/{project_id}/service/{service_id}",
        }


async def _create_service(client: httpx.AsyncClient, project_id: str, name: str) -> str:
    query = """
    mutation serviceCreate($input: ServiceCreateInput!) {
        serviceCreate(input: $input) {
            id
        }
    }
    """
    variables = {
        "input": {
            "projectId": project_id,
            "name": name,
        }
    }
    resp = await client.post(
        RAILWAY_API_URL,
        headers=get_headers(),
        json={"query": query, "variables": variables},
    )
    data = resp.json()
    return data["data"]["serviceCreate"]["id"]


async def _set_env_variable(
    client: httpx.AsyncClient,
    service_id: str,
    project_id: str,
    name: str,
    value: str,
):
    query = """
    mutation variableUpsert($input: VariableUpsertInput!) {
        variableUpsert(input: $input)
    }
    """
    variables = {
        "input": {
            "projectId": project_id,
            "serviceId": service_id,
            "name": name,
            "value": value,
        }
    }
    await client.post(
        RAILWAY_API_URL,
        headers=get_headers(),
        json={"query": query, "variables": variables},
    )


async def _upload_code(client: httpx.AsyncClient, service_id: str, code: str):
    requirements = "python-telegram-bot==20.7\nhttpx==0.27.0\n"
    procfile = "web: python main.py\n"

    files_b64 = {
        "main.py": base64.b64encode(code.encode()).decode(),
        "requirements.txt": base64.b64encode(requirements.encode()).decode(),
        "Procfile": base64.b64encode(procfile.encode()).decode(),
    }

    query = """
    mutation serviceSourceDeploy($input: ServiceSourceDeployInput!) {
        serviceSourceDeploy(input: $input)
    }
    """
    variables = {
        "input": {
            "serviceId": service_id,
            "files": [
                {"path": path, "content": content}
                for path, content in files_b64.items()
            ],
        }
    }
    await client.post(
        RAILWAY_API_URL,
        headers=get_headers(),
        json={"query": query, "variables": variables},
    )
