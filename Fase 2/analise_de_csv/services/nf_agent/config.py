# config.py
import os

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "192.168.0.120:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-small3.1:24b-instruct-2503-q8_0")
OLLAMA_FUNCTION_CALLING = os.getenv("OLLAMA_FUNCTION_CALLING", "true").lower() == "true"
OLLAMA_JSON_OUTPUT = os.getenv("OLLAMA_JSON_OUTPUT", "true").lower() == "true"
OLLAMA_VISION = os.getenv("OLLAMA_VISION", "false").lower() == "true"

# Ollama2 configuration
OLLAMA2_HOST = os.getenv("OLLAMA2_HOST", "ollama2:11434")
OLLAMA2_MODEL = os.getenv("OLLAMA2_MODEL", "phi3")
OLLAMA2_FUNCTION_CALLING = os.getenv("OLLAMA2_FUNCTION_CALLING", "false").lower() == "true"
OLLAMA2_JSON_OUTPUT = os.getenv("OLLAMA2_JSON_OUTPUT", "false").lower() == "true"
OLLAMA2_VISION = os.getenv("OLLAMA2_VISION", "false").lower() == "true"

# MCP Tools configuration
FILESYSTEM_MOUNT_PATH = os.getenv("FILESYSTEM_MOUNT_PATH", "/home/enzo/dev/autogen/fs")
FILESYSTEM_CONTAINER_PATH = os.getenv("FILESYSTEM_CONTAINER_PATH", "/data")
MCP_FILESYSTEM_IMAGE = os.getenv("MCP_FILESYSTEM_IMAGE", "mcp/filesystem")
MCP_POSTGRES_IMAGE = os.getenv("MCP_POSTGRES_IMAGE", "mcp/postgres")

# PostgreSQL configuration
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@host.docker.internal:5432/notasfiscais")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "notasfiscais")
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "public")

# Service configuration
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "50"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO") 