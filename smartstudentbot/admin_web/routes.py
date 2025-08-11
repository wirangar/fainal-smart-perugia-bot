from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from starlette.requests import Request
from itsdangerous import URLSafeSerializer, BadSignature

from config import ADMIN_USERNAME, ADMIN_PASSWORD, SESSION_SECRET_KEY
from utils.db_utils import get_db_session
from models_db import User, News, SuccessStory, StoryStatus

router = APIRouter()
templates = Jinja2Templates(directory="smartstudentbot/admin_web/templates")
serializer = URLSafeSerializer(SESSION_SECRET_KEY)

# --- Authentication ---
def get_current_user(request: Request):
    session_cookie = request.cookies.get("admin_session")
    if not session_cookie:
        return None
    try:
        data = serializer.loads(session_cookie)
        return data.get("username")
    except BadSignature:
        return None

# --- Routes ---
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
        session_data = serializer.dumps({"username": username})
        response.set_cookie(key="admin_session", value=session_data, httponly=True)
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="admin_session")
    return response

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    # Fetch stats
    total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
    total_news = (await session.execute(select(func.count(News.id)))).scalar_one()
    pending_stories = (await session.execute(select(func.count(SuccessStory.id)).where(SuccessStory.status == StoryStatus.PENDING))).scalar_one()

    stats = {
        "total_users": total_users,
        "total_news": total_news,
        "pending_stories": pending_stories,
    }

    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})

# A simple root to redirect to the dashboard
@router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/admin/dashboard")

# --- News Management ---
@router.get("/news", response_class=HTMLResponse)
async def news_management_page(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    news_list = (await session.execute(select(News).order_by(News.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("news.html", {"request": request, "news_list": news_list, "article": None})

@router.get("/news/edit/{article_id}", response_class=HTMLResponse)
async def edit_news_page(request: Request, article_id: int, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    article = (await session.execute(select(News).where(News.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    news_list = (await session.execute(select(News).order_by(News.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("news.html", {"request": request, "news_list": news_list, "article": article})

@router.post("/news/add")
async def handle_add_edit_news(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user),
    article_id: str = Form(None),
    title: str = Form(...),
    content: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    if article_id: # Editing existing
        article = (await session.execute(select(News).where(News.id == int(article_id)))).scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        article.title = title
        article.content = content
    else: # Adding new
        article = News(title=title, content=content, posted_by=0) # posted_by 0 for admin
        session.add(article)

    await session.commit()
    return RedirectResponse(url="/admin/news", status_code=status.HTTP_302_FOUND)

@router.get("/news/delete/{article_id}")
async def delete_news_article(
    request: Request,
    article_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    article = (await session.execute(select(News).where(News.id == article_id))).scalar_one_or_none()
    if article:
        await session.delete(article)
        await session.commit()

    return RedirectResponse(url="/admin/news", status_code=status.HTTP_302_FOUND)
