from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "TxLogPay API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Stellar
    STELLAR_NETWORK: Literal["testnet", "mainnet"] = "testnet"
    STELLAR_HORIZON_URL: str = "https://horizon-testnet.stellar.org"
    STELLAR_RPC_URL: str = "https://soroban-testnet.stellar.org"
    STELLAR_FRIENDBOT_URL: str = "https://friendbot.stellar.org"

    # Platform (TxLogPay) Stellar account
    PLATFORM_SECRET_KEY: str = ""
    PLATFORM_PUBLIC_KEY: str = ""

    # Contract addresses (set after deployment)
    FLAGS_CONTRACT_ID: str = ""
    ESCROW_CONTRACT_ID: str = ""
    TRADE_INFO_CONTRACT_ID: str = ""

    # Etherfuse
    ETHERFUSE_API_KEY: str = ""
    ETHERFUSE_BASE_URL: str = "https://api.etherfuse.com"
    ETHERFUSE_TEST_MODE: bool = True

    # Anthropic (for LlamaIndex LLM)
    ANTHROPIC_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://txlogpay:txlogpay@localhost:5432/txlogpay"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Platform fee
    PLATFORM_FEE_BPS: int = 200  # 2%


settings = Settings()
