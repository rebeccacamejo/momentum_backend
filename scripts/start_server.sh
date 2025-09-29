#!/bin/bash

# Start the Momentum Backend API server with uvicorn
# This script starts the FastAPI application with hot reload enabled for development

echo "Starting Momentum Backend API server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload