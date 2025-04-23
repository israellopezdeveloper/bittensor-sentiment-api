from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    auth_token: str
    datura_api_key: str
    chutes_api_key: str
    test_mnemonics: str
    test_wallet_name: str
    environment: str = 'development'
    blockchain_url: str
    blockchain_max_retries: int
    blockchain_retry_timeout: int
    ttl_cache: int

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
