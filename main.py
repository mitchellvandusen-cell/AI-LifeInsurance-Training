"""
InsuranceGrokBot — AI Sales Training for Life Insurance Agents
Entry point for the FastAPI server.
"""

import uvicorn

from src.api.routes import app
from src.config import config


def main():
    warnings = config.validate()
    for w in warnings:
        print(f"[WARNING] {w}")

    print("=" * 60)
    print("  InsuranceGrokBot — AI Sales Training")
    print("=" * 60)
    print(f"  Server: http://{config.host}:{config.port}")
    print(f"  Docs:   http://{config.host}:{config.port}/docs")
    print(f"  Model:  {config.llm_model}")
    print("=" * 60)

    uvicorn.run(
        "src.api.routes:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )


if __name__ == "__main__":
    main()
