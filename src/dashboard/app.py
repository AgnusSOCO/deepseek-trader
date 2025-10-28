"""
FastAPI Dashboard Application

Main FastAPI application for the trading bot dashboard.
Provides REST API endpoints for monitoring and control.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os

from .routes import router


def create_app(title: str = "AI Crypto Trading Bot Dashboard",
               version: str = "2.0.0",
               description: str = "Dashboard for monitoring and controlling the AI cryptocurrency trading bot") -> FastAPI:
    """
    Create FastAPI application
    
    Args:
        title: Application title
        version: Application version
        description: Application description
        
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title=title,
        version=version,
        description=description,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router, prefix="/api")
    
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    if os.path.exists(templates_dir):
        @app.get("/", response_class=HTMLResponse)
        async def read_root():
            """Serve main dashboard page"""
            index_path = os.path.join(templates_dir, "index.html")
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    return f.read()
            return "<h1>AI Crypto Trading Bot Dashboard</h1><p>API documentation available at <a href='/docs'>/docs</a></p>"
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "ok", "version": version}
    
    return app
