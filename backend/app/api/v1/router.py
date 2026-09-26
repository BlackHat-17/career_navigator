"""
Central v1 router — mounts all sub-routers.
Imported by app/main.py.
"""
from fastapi import APIRouter

from app.api.v1 import analysis, github, jobs, projects, resume, roadmap, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users.router)
api_router.include_router(github.router)
api_router.include_router(resume.router)
api_router.include_router(jobs.router)
api_router.include_router(analysis.router)
api_router.include_router(projects.router)
api_router.include_router(roadmap.router)
