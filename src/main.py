"""Development entry point. Run from the project root:  python -m src.main"""

import uvicorn

from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
