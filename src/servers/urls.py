from fastapi import APIRouter

from src.models.servers import CreateServer, RequestServer, Server
from src.servers.services import create_server, delete_server, get_server, update_server

router = APIRouter(prefix="/server", tags=["server"])


@router.post("/get")
async def get_servers(payload: RequestServer):
    return get_server(server_id=payload.server_id)


@router.post("/create")
async def create_servers(payload: CreateServer):
    return create_server(server=payload)


@router.post("/update")
async def update_servers(payload: Server):
    return update_server(server=payload)


@router.post("/delete")
async def delete_servers(payload: RequestServer):
    return delete_server(server_id=payload.server_id)
