from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_tenantuser_usernam_138e0a";
        CREATE TABLE IF NOT EXISTS "organization" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "owner_id" INT NOT NULL REFERENCES "coreuser" ("id") ON DELETE CASCADE
);
        ALTER TABLE "tenantuser" ADD "is_active" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "tenantuser" ADD "email" VARCHAR(255) NOT NULL UNIQUE;
        ALTER TABLE "tenantuser" DROP COLUMN "username";
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_tenantuser_email_e716a7" ON "tenantuser" ("email");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_tenantuser_email_e716a7";
        ALTER TABLE "tenantuser" ADD "username" VARCHAR(50) NOT NULL UNIQUE;
        ALTER TABLE "tenantuser" DROP COLUMN "is_active";
        ALTER TABLE "tenantuser" DROP COLUMN "email";
        DROP TABLE IF EXISTS "organization";
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_tenantuser_usernam_138e0a" ON "tenantuser" ("username");"""
