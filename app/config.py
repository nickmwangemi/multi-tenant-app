from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	database_url: str
	secret_key: str
	algorithm: str
	access_token_expire_minutes: int
	verification_token_expire_hours: int
	core_database_url: str = ""
	tenant_database_base: str = ""

	class Config:
		env_file = ".env"
		extra = "ignore"

	def __init__(self, **values):
		super().__init__(**values)
		if not self.core_database_url:
			self.core_database_url = self.database_url
		if not self.tenant_database_base:
			self.tenant_database_base = self.database_url.rsplit('/', 1)[0]


settings = Settings()