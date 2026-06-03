
# Notes API
Secure Notes API

## Overview
Use asdf-vm to select python versions
Use direnv for virtual python environments
Design and implement a simple small backend service in python that demonstrates API design, data persistence, testing, and documentation. This will be the base of learning so just the simple basics to build on later.

You will build a service that allows users to create, view, manage, and share notes - with authentication, access control, and considerations for how the system would operate in production.

Focus on a well-structured, production-minded solution and documenting your decisions. It is acceptable to stub or describe components you didn't have time to fully implement - we value your reasoning as much as your code.

# Problem Statement
Implement a Secure Notes API that: 
  - Exposes a REST API
  - Authenticates users
  - Enforces access control
  - Persists data
  - Includes automated tests
  - Considers operational concerns

# Functional Requirements
## API Endpoints
 - POST /auth/register # Register a new user
 - POST /auth/login    # Authenticate and receive a token
 - POST /notes         # Create a new note
 - GET  /notes         # List the authenticated user’s notes
 - GET  /notes/{id}    # Get a note by ID (if authorized)
 - PUT  /notes/{id}    # Update a note (if authorized)
 - DELETE /notes/{id}  # Delete a note (if authorized)
 - POST /notes/{id}/share # Share a note with another user (read only)

## API Behavior
 - Use appropriate HTTP status codes
 - Return clear error responses for invalid requests
 - API behavior should be predictable and documented

## Authentication & Authorization
 - Implement token-based authentication (e.g., JWT)
 - Users can only access their own notes unless a note has been explicitly shared with them
 - Shared notes are read-only to the recipient

# Data Model
## At minimum: 
 - User: id, username, password_hash, created_at
 - Note: id, owner_id, content, created_at, updated_at
 - Share: id, note_id, shared_with_user_id, created_at

# Data Storage
Use a Postgres database
 
# Testing
## Include automated tests:
 - API-level tests (at least authentication and access control scenarios)
 - Business logic or data-layer tests
 - At least one test that verifies a user cannot access another user's note

# Documentation
Include a README.md covering:
 - System overview and architecture
 - Tech choices
 - How to run the project and tests
 - API usage examples
 - Security considerations
 - Assumptions, tradeoffs, and future improvements

In DESIGN.md, briefly address: 
 - How would you deploy this service to production?
 - What would you monitor or alert on?
 - How would you handle database migrations over time?
 - What would change if this needed to support 10,000 concurrent users?

# Build & Submission
Use Docker Compose with postgres and the notes app
