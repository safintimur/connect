from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="connect-core", alias="PROJECT_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")

    database_url: str = Field(
        default="postgresql+psycopg://connect:connect@localhost:5432/connect_control",
        alias="DATABASE_URL",
    )

    base_subscription_url: str = Field(
        default="https://sub.example.com/s",
        alias="BASE_SUBSCRIPTION_URL",
    )
    api_bind_host: str = Field(default="0.0.0.0", alias="API_BIND_HOST")
    api_bind_port: int = Field(default=8080, alias="API_BIND_PORT")

    do_token: str = Field(default="", alias="DIGITALOCEAN_TOKEN")
    do_default_region: str = Field(default="lon1", alias="DO_DEFAULT_REGION")
    do_default_image: str = Field(default="ubuntu-24-04-x64", alias="DO_DEFAULT_IMAGE")
    do_default_size: str = Field(default="s-1vcpu-1gb", alias="DO_DEFAULT_SIZE")

    reality_public_key: str = Field(default="", alias="REALITY_PUBLIC_KEY")
    reality_private_key: str = Field(default="", alias="REALITY_PRIVATE_KEY")
    reality_short_id: str = Field(default="", alias="REALITY_SHORT_ID")
    reality_server_name: str = Field(default="www.cloudflare.com", alias="REALITY_SERVER_NAME")
    reality_dest: str = Field(default="www.cloudflare.com:443", alias="REALITY_DEST")
    vless_flow: str = Field(default="xtls-rprx-vision", alias="VLESS_FLOW")
    vless_fp: str = Field(default="chrome", alias="VLESS_FP")


settings = Settings()
