# Technical Documentation

## Architecture Overview

This multi-tenant FastAPI application implements a sophisticated database routing system that dynamically switches between core and tenant-specific databases based on request context.

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │    │   Core Database │    │ Tenant Database │
│                 │    │                 │    │                 │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │  X-TENANT │  │────│  │ CoreUser  │  │    │  │TenantUser │  │
│  │   Header  │  │    │  │Organization│  │    │  │   Data    │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────────┐
                    │  FastAPI App    │
                    │                 │
                    │ ┌─────────────┐ │
                    │ │ Middleware  │ │
                    │ │  Routing    │ │
                    │ └─────────────┘ │
                    └─────────────────┘
```

## Database Architecture

### Core Database Schema

The core database manages system-wide entities:

```sql
-- Core Users (System users and organization owners)
CREATE TABLE coreuser (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    is_owner BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    verification_token_created_at TIMESTAMPTZ
);

-- Organizations (Tenants)
CREATE TABLE organization (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER REFERENCES coreuser(id) ON DELETE CASCADE
);
```

### Tenant Database Schema

Each tenant gets its own database with:

```sql
-- Tenant Users (Organization-specific users)
CREATE TABLE tenantuser (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

## Request Flow Architecture

### 1. Tenant Context Middleware

```python
class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        x_tenant = request.headers.get("X-TENANT")
        request.state.tenant = x_tenant
        request.state.is_core = not x_tenant
        return await call_next(request)
```

**Purpose**: Extracts tenant context from HTTP headers and sets request state.

### 2. Database Connection Routing

The application uses context-aware database connections:

- **Core Operations**: No `X-TENANT` header → Core database
- **Tenant Operations**: `X-TENANT: <org_id>` header → Tenant database

### 3. Authentication Context

JWT tokens contain different payloads based on context:

**Core JWT Payload:**
```json
{
  "sub": "user_id",
  "is_owner": true,
  "exp": 1234567890
}
```

**Tenant JWT Payload:**
```json
{
  "sub": "user_id",
  "exp": 1234567890
}
```

## Core Components

### Models

#### Core Models (`app/models/core.py`)

- **CoreUser**: System users with ownership capabilities
- **Organization**: Tenant organizations
- **Token/Auth Models**: JWT and authentication schemas

#### Tenant Models (`app/models/tenant.py`)

- **TenantUser**: Organization-specific users
- **Profile Models**: User profile management schemas

### Services

#### Authentication Service (`app/services/auth.py`)

```python
async def get_current_user(request: Request, token: str):
    # Decode JWT token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    # Route to appropriate database based on context
    if request.state.is_core:
        user = await CoreUser.get_or_none(id=user_id)
    else:
        user = await TenantUser.get_or_none(id=user_id)
    
    return user
```

#### Tenant Service (`app/services/tenant.py`)

```python
async def create_tenant_database(organization_id: int):
    # Create new PostgreSQL database for tenant
    conn = await asyncpg.connect(settings.database_url)
    database_name = f"tenant_{organization_id}"
    await conn.execute(f'CREATE DATABASE "{database_name}"')
    await conn.close()
    return database_name
```

### Utilities

#### Authentication Utils (`app/utils/auth.py`)

- **Password Hashing**: bcrypt-based secure password handling
- **JWT Management**: Token creation and validation
- **User Authentication**: Core user authentication logic

## Security Implementation

### 1. Password Security

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### 2. JWT Authentication

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### 3. Authorization Layers

- **Owner-only operations**: Organization creation requires `is_owner=True`
- **Tenant isolation**: Users can only access their tenant's data
- **JWT scoping**: Tokens are scoped to specific contexts (core vs tenant)

## Critical Issues & Improvements Needed

### 🚨 High Priority Fixes

1. **Database Connection Routing**
   ```python
   # Current issue: Middleware sets context but doesn't route connections
   # Need to implement proper connection switching in dependencies
   
   async def get_db_connection(request: Request):
       if request.state.is_core:
           # Connect to core database
           return core_connection
       else:
           # Connect to tenant database
           tenant_id = request.state.tenant
           return get_tenant_connection(tenant_id)
   ```

2. **Tenant Database Initialization**
   ```python
   # After creating tenant database, need to run migrations
   async def create_tenant_database(organization_id: int):
       # Create database
       database_name = f"tenant_{organization_id}"
       await create_database(database_name)
       
       # Initialize schema
       await run_tenant_migrations(database_name)
       
       # Sync organization owner
       await sync_owner_to_tenant(organization_id)
   ```

3. **Core Login Route Fix**
   ```python
   # Current: @router.post("auth/login")  # Missing leading slash
   # Should be: @router.post("/auth/login")
   ```

### 🔧 Medium Priority Improvements

1. **Connection Pooling**: Implement database connection pools per tenant
2. **Caching**: Add Redis for session management and frequently accessed data
3. **Rate Limiting**: Implement per-tenant rate limiting
4. **Logging**: Add structured logging with tenant context
5. **Monitoring**: Add health checks and metrics collection

### 📋 Testing Strategy

```python
# Example test structure needed
class TestCoreOperations:
    async def test_user_registration(self):
        # Test core user registration
        pass
    
    async def test_organization_creation(self):
        # Test organization creation and tenant DB provisioning
        pass

class TestTenantOperations:
    async def test_tenant_user_registration(self):
        # Test tenant user registration with X-TENANT header
        pass
    
    async def test_tenant_isolation(self):
        # Test that tenants can't access each other's data
        pass
```

## Performance Considerations

### Database Connection Management

```python
# Implement connection pooling
from tortoise.contrib.postgres import PostgresConnection

class TenantConnectionManager:
    def __init__(self):
        self.connections = {}
    
    async def get_connection(self, tenant_id: str):
        if tenant_id not in self.connections:
            self.connections[tenant_id] = await create_tenant_connection(tenant_id)
        return self.connections[tenant_id]
```

### Caching Strategy

```python
# Cache tenant configurations
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def get_tenant_config(tenant_id: str):
    cached = redis_client.get(f"tenant:{tenant_id}:config")
    if cached:
        return json.loads(cached)
    
    config = await fetch_tenant_config(tenant_id)
    redis_client.setex(f"tenant:{tenant_id}:config", 3600, json.dumps(config))
    return config
```

## Deployment Architecture

### Docker Configuration

```dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/core
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: core
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
```

## Monitoring and Observability

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.get("/health/db")
async def db_health_check():
    try:
        await CoreUser.first()
        return {"database": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database unhealthy")
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    request_count.labels(method=request.method, endpoint=request.url.path).inc()
    request_duration.observe(duration)
    
    return response
```

This technical documentation provides a comprehensive overview of the current implementation, identifies critical issues, and outlines the path forward for a production-ready multi-tenant application.