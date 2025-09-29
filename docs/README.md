# Momentum Backend Documentation

This directory contains comprehensive documentation for the Momentum MVP backend system.

## Documentation Structure

### API Documentation
- [**API Overview**](./api/overview.md) - High-level API architecture and design principles
- [**Authentication**](./api/authentication.md) - User authentication and authorization
- [**Deliverables**](./api/deliverables.md) - Core deliverable generation and management
- [**Zoom Integration**](./api/zoom-integration.md) - Zoom meeting recording integration
- [**Organizations**](./api/organizations.md) - Multi-tenant organization management
- [**File Upload**](./api/file-upload.md) - Audio/video file processing

### Database Documentation
- [**Schema Overview**](./database/schema-overview.md) - Complete database schema
- [**Migrations**](./database/migrations.md) - Database migration requirements
- [**Relationships**](./database/relationships.md) - Table relationships and constraints

### Deployment Documentation
- [**Environment Setup**](./deployment/environment.md) - Environment variables and configuration
- [**Dependencies**](./deployment/dependencies.md) - Required dependencies and services
- [**Docker Setup**](./deployment/docker.md) - Docker containerization (if applicable)

### Development Documentation
- [**Getting Started**](./development/getting-started.md) - Local development setup
- [**Code Architecture**](./development/architecture.md) - Code organization and patterns
- [**Testing**](./development/testing.md) - Testing strategy and guidelines
- [**Contributing**](./development/contributing.md) - Development guidelines and standards

### Integration Documentation
- [**Zoom Setup**](./integrations/zoom-setup.md) - Setting up Zoom app and OAuth
- [**Supabase Setup**](./integrations/supabase-setup.md) - Supabase configuration
- [**OpenAI Setup**](./integrations/openai-setup.md) - OpenAI API configuration

## Quick Links

- **Core Features**: [Deliverables API](./api/deliverables.md), [Authentication](./api/authentication.md)
- **Integrations**: [Zoom Integration](./api/zoom-integration.md), [File Upload](./api/file-upload.md)
- **Setup**: [Getting Started](./development/getting-started.md), [Environment Setup](./deployment/environment.md)
- **Database**: [Schema Overview](./database/schema-overview.md), [Migrations](./database/migrations.md)

## System Overview

The Momentum backend is a FastAPI-based system that provides:

1. **Session Processing**: Upload and transcribe audio/video files to generate structured deliverables
2. **User Management**: Multi-tenant user authentication and organization management
3. **Zoom Integration**: Connect with Zoom to automatically process meeting recordings
4. **Deliverable Management**: Store, retrieve, and export session deliverables

### Key Technologies

- **Framework**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth with JWT
- **AI/ML**: OpenAI GPT-4 for transcription and summarization
- **File Storage**: Supabase Storage
- **Integrations**: Zoom API for meeting recordings

### Architecture Principles

- **API-First**: RESTful API design with OpenAPI documentation
- **Security**: JWT-based authentication with user data isolation
- **Scalability**: Async/await pattern with efficient database queries
- **Error Handling**: Comprehensive error handling with proper HTTP status codes
- **Rate Limiting**: Built-in rate limiting for external API calls
- **Documentation**: Self-documenting code with comprehensive API docs
