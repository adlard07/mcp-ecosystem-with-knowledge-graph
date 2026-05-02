from typing import Any

from pydantic import BaseModel, Field

from utils.utils import generate_uuid


class CreateServer(BaseModel):
    server_id: str = Field(default_factory=generate_uuid)
    server_name: str
    server_description: str
    server_type: str | None = None
    documentation: str | None = None
    server_icon: str | None = None
    health_check: str | None = None
    server_url: str
    server_sufixes: (
        dict[
            str,
            dict[str, str | dict[Any, Any]]
            | dict[str, str | dict[str, str] | dict[str, str | float]]
            | dict[str, str | dict[str, dict[str, str]] | dict[str, str]]
            | dict[str, str | dict[str, dict[str, str]]]
            | dict[str, str | dict[str, dict[str, str]] | dict[str, float | str]],
        ]
        | None
    ) = None
    # {suffix_name: {
    #      method: [api_method_type],
    #      description: [suffix_description],
    #      suffix: suffix_description,
    #      parameters: [suffix_parameters]
    #    }
    # }


class Server(BaseModel):
    server_id: str
    server_name: str | None = None
    server_description: str | None = None
    server_type: str | None = None
    documentation: str | None = None
    server_url: str
    server_sufixes: dict | None = None


class RequestServer(BaseModel):
    server_id: str
