# Multi-Tenant FastAPI Application

A FastAPI-based multi-tenant application with dynamic database routing, JWT authentication, and organization management.

## 🏗️ Architecture Overview

This application implements a multi-tenant architecture with:
- **Core Database**: Manages organizations, tenant owners, and system-wide data
- **Tenant Databases**: Separate databases for each tenant/organization
- **Dynamic Routing**: Automatic connection switching based on `X-TENANT` header
- **JWT Authentication**: Separate authentication contexts for core and tenant operations

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- uv package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nickmwangemi/multi-tenant-app.git
   cd multi-tenant-app
   ```

2. **Create and activate virtual environment**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   uv pip install -e .
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/multi_tenant_core
   SECRET_KEY=your-super-secret-key-here-change-this-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   VERIFICATION_TOKEN_EXPIRE_HOURS=24
   ```

5. **Set up PostgreSQL**
   ```bash
   # Create the core database
   createdb multi_tenant_core
   ```

6. **Run database migrations**
   ```bash
   aerich init -t app.config.TORTOISE_ORM
   aerich init-db
   aerich migrate
   aerich upgrade
   ```

### Running the Application

1. **Start the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the application**
   - API: http://localhost:8000
   - Interactive API docs: http://localhost:8000/docs
   - ReDoc documentation: http://localhost:8000/redoc

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_core.py -v
```

### Test Structure

- `tests/test_core.py` - Core database operations and authentication
- `tests/test_tenant.py` - Tenant-specific operations
- `tests/test_integration.py` - End-to-end integration tests

## 📊 Database Schema

### Core Database Tables

- **coreuser**: System users and organization owners
- **organization**: Tenant organizations
- **aerich**: Migration history

### Tenant Database Tables

- **tenantuser**: Tenant-specific users
- **aerich**: Migration history per tenant

## 🔧 Development

### Code Quality Tools

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type checking (if mypy is added)
mypy app/

# Linting (if ruff is added)
ruff check app/
```

### Database Operations

```bash
# Create new migration
aerich migrate --name "description_of_changes"

# Apply migrations
aerich upgrade

# Rollback migration
aerich downgrade
```

## 🚀 Deployment

### Using Docker (Recommended)

```bash
# Build and run with docker-compose
docker-compose up --build

# Or run individual services
docker build -t multi-tenant-app .
docker run -p 8000:8000 multi-tenant-app
```

### Manual Deployment

1. Set up production database
2. Configure environment variables
3. Run migrations
4. Use a production WSGI server:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

## 🔐 Security Considerations

- Change the `SECRET_KEY` in production
- Use environment variables for sensitive data
- Implement rate limiting for authentication endpoints
- Set up proper CORS policies
- Use HTTPS in production
- Implement proper logging and monitoring

## 📈 Performance Optimization

- Use connection pooling for database connections
- Implement caching for frequently accessed data
- Add database indexes for commonly queried fields
- Use async operations throughout the application

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure database exists

2. **Migration Errors**
   - Check if aerich is properly initialized
   - Verify database permissions
   - Run migrations in correct order

3. **Authentication Issues**
   - Verify JWT secret key is set
   - Check token expiration times
   - Ensure proper headers are sent

### Documentation

- [API Documentation](DOCUMENTATION.md)
- [Technical Documentation](TECHNICAL_DOCUMENTATION.md)


### Technical Documentation

Documentation for the API endpoint is available [here](DOCUMENTATION.md)

### Getting Help

- Check the [Issues](https://github.com/nickmwangemi/multi-tenant-app/issues) page
- Review the API documentation at `/docs`
- Check application logs for detailed error messages