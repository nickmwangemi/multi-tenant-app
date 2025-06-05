# API Documentation

## Base URL
```
http://localhost:8000/api
```

## Authentication

This API uses JWT Bearer token authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Tenant Context

For tenant-specific operations, include the tenant identifier in the header:
```
X-TENANT: <organization_id>
```

---

## Core Operations (No X-TENANT Header)

These operations work with the core database and manage organizations and their owners.

### 🔐 Authentication

#### Register User
```http
POST /api/auth/register
```

Register a new user in the core database.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "is_owner": false
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "created_at": "2025-06-05T21:30:00Z",
    "is_verified": false,
    "is_owner": false
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "verification_token": "abc123def456..."
}
```

**Error Responses:**
- `400 Bad Request`: Email already registered
- `422 Unprocessable Entity`: Invalid input data

---

#### Verify Email
```http
GET /api/auth/verify?token=<verification_token>
```

Verify user email with the token received during registration.

**Query Parameters:**
- `token` (required): Email verification token

**Response (200 OK):**
```json
{
  "message": "Email verified successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Token expired or missing
- `404 Not Found`: Invalid token

---

#### Login
```http
POST /api/auth/login
```

Authenticate user and receive access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Email not verified

---

### 🏢 Organizations

#### Create Organization
```http
POST /api/organizations
```

Create a new organization (requires authentication and owner privileges).

**Headers:**
```
Authorization: Bearer <owner_jwt_token>
```

**Request Body:**
```json
{
  "name": "My Organization"
}
```

**Response (200 OK):**
```json
{
  "message": "Organization created successfully",
  "organization_id": 1,
  "tenant_db_name": "tenant_1"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token
- `403 Forbidden`: User is not an owner
- `400 Bad Request`: Invalid organization data

---

## Tenant Operations (With X-TENANT Header)

These operations work with tenant-specific databases and require the `X-TENANT` header.

### 🔐 Tenant Authentication

#### Register Tenant User
```http
POST /api/auth/register
```

Register a new user in a specific tenant database.

**Headers:**
```
X-TENANT: 1
```

**Request Body:**
```json
{
  "email": "tenant.user@example.com",
  "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "email": "tenant.user@example.com",
  "created_at": "2025-06-05T21:30:00Z",
  "is_active": true
}
```

**Error Responses:**
- `400 Bad Request`: Email already registered in tenant
- `422 Unprocessable Entity`: Invalid input data

---

#### Tenant User Login
```http
POST /api/auth/login
```

Authenticate tenant user and receive access token.

**Headers:**
```
X-TENANT: 1
Content-Type: application/x-www-form-urlencoded
```

**Request Body (form data):**
```
email=tenant.user@example.com
password=securepassword123
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `400 Bad Request`: Missing X-TENANT header

---

### 👤 User Profile Management

#### Get Current User Profile
```http
GET /api/users/me
```

Get the current authenticated tenant user's profile.

**Headers:**
```
Authorization: Bearer <tenant_jwt_token>
X-TENANT: 1
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "tenant.user@example.com",
  "created_at": "2025-06-05T21:30:00Z",
  "is_active": true
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token
- `400 Bad Request`: Missing X-TENANT header

---

#### Update Current User Profile
```http
PUT /api/users/me
```

Update the current authenticated tenant user's profile.

**Headers:**
```
Authorization: Bearer <tenant_jwt_token>
X-TENANT: 1
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "updated.email@example.com"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "updated.email@example.com",
  "created_at": "2025-06-05T21:30:00Z",
  "is_active": true
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token
- `400 Bad Request`: Missing X-TENANT header or invalid data
- `422 Unprocessable Entity`: Invalid email format

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or invalid
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Invalid input validation
- `500 Internal Server Error`: Server error

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- Authentication endpoints: 5 requests per minute
- General endpoints: 100 requests per minute

Exceeded rate limits return `429 Too Many Requests`.

---

## Examples

### Complete User Registration and Organization Creation Flow

1. **Register as owner:**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@company.com",
    "password": "securepass123",
    "is_owner": true
  }'
```

2. **Verify email:**
```bash
curl "http://localhost:8000/api/auth/verify?token=<verification_token>"
```

3. **Login to get access token:**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@company.com",
    "password": "securepass123"
  }'
```

4. **Create organization:**
```bash
curl -X POST "http://localhost:8000/api/organizations" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company"}'
```

### Tenant User Registration and Login Flow

1. **Register tenant user:**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "X-TENANT: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "employee@company.com",
    "password": "securepass123"
  }'
```

2. **Login as tenant user:**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "X-TENANT: 1" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=employee@company.com&password=securepass123"
```

3. **Get user profile:**
```bash
curl "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer <tenant_access_token>" \
  -H "X-TENANT: 1"
```