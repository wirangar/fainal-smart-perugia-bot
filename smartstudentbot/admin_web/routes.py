from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from starlette.requests import Request
from itsdangerous import URLSafeSerializer, BadSignature

from config import ADMIN_USERNAME, ADMIN_PASSWORD, SESSION_SECRET_KEY
from utils.db_utils import get_db_session
from models_db import User, News, SuccessStory, StoryStatus, Discount, Event, EventStatus, Podcast, Feedback

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

# --- Discount Management ---
@router.get("/discounts", response_class=HTMLResponse)
async def discount_management_page(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    discount_list = (await session.execute(select(Discount).order_by(Discount.category, Discount.name))).scalars().all()
    return templates.TemplateResponse("discounts.html", {"request": request, "discount_list": discount_list, "discount": None})

@router.get("/discounts/edit/{discount_id}", response_class=HTMLResponse)
async def edit_discount_page(request: Request, discount_id: int, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    discount = (await session.execute(select(Discount).where(Discount.id == discount_id))).scalar_one_or_none()
    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")

    discount_list = (await session.execute(select(Discount).order_by(Discount.category, Discount.name))).scalars().all()
    return templates.TemplateResponse("discounts.html", {"request": request, "discount_list": discount_list, "discount": discount})

@router.post("/discounts/add")
async def handle_add_edit_discount(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user),
    discount_id: str = Form(None),
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    validity: str = Form(...)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    if discount_id: # Editing
        discount = (await session.execute(select(Discount).where(Discount.id == int(discount_id)))).scalar_one_or_none()
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        discount.name, discount.category, discount.description, discount.location, discount.validity = name, category, description, location, validity
    else: # Adding new
        discount = Discount(name=name, category=category, description=description, location=location, validity=validity)
        session.add(discount)

    await session.commit()
    return RedirectResponse(url="/admin/discounts", status_code=status.HTTP_302_FOUND)

@router.get("/discounts/delete/{discount_id}")
async def delete_discount(
    request: Request,
    discount_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    discount = (await session.execute(select(Discount).where(Discount.id == discount_id))).scalar_one_or_none()
    if discount:
        await session.delete(discount)
        await session.commit()

    return RedirectResponse(url="/admin/discounts", status_code=status.HTTP_302_FOUND)

# --- Event Management ---
@router.get("/events", response_class=HTMLResponse)
async def event_management_page(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    event_list = (await session.execute(select(Event).order_by(Event.event_datetime.desc()))).scalars().all()
    return templates.TemplateResponse("events.html", {"request": request, "event_list": event_list})

@router.get("/events/{action}/{event_id}")
async def handle_event_action(
    request: Request,
    action: str,
    event_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    event = (await session.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if action == "confirm":
        event.status = EventStatus.CONFIRMED
    elif action == "cancel":
        event.status = EventStatus.CANCELLED
    elif action == "delete":
        await session.delete(event)

    await session.commit()
    # In a real app, you'd also notify the user who created the event.
    return RedirectResponse(url="/admin/events", status_code=status.HTTP_302_FOUND)

# --- Podcast Management ---
@router.get("/podcasts", response_class=HTMLResponse)
async def podcast_management_page(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    podcast_list = (await session.execute(select(Podcast).order_by(Podcast.id.desc()))).scalars().all()
    return templates.TemplateResponse("podcasts.html", {"request": request, "podcast_list": podcast_list})

@router.post("/podcasts/add")
async def handle_add_podcast(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user),
    title: str = Form(...),
    description: str = Form(...),
    audio_file_id: str = Form(...),
    duration_seconds: int = Form(...)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    podcast = Podcast(title=title, description=description, audio_file_id=audio_file_id, duration_seconds=duration_seconds)
    session.add(podcast)
    await session.commit()

    return RedirectResponse(url="/admin/podcasts", status_code=status.HTTP_302_FOUND)

@router.get("/podcasts/delete/{podcast_id}")
async def delete_podcast(
    request: Request,
    podcast_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    podcast = (await session.execute(select(Podcast).where(Podcast.id == podcast_id))).scalar_one_or_none()
    if podcast:
        await session.delete(podcast)
        await session.commit()

    return RedirectResponse(url="/admin/podcasts", status_code=status.HTTP_302_FOUND)

# --- Feedback Management ---
@router.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    feedback_list = (await session.execute(select(Feedback).order_by(Feedback.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("feedback.html", {"request": request, "feedback_list": feedback_list})

# --- User Management ---
@router.get("/users", response_class=HTMLResponse)
async def user_management_page(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    user_list = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("users.html", {"request": request, "user_list": user_list})

# --- Success Story Management ---
@router.get("/stories", response_class=HTMLResponse)
async def story_management_page(request: Request, session: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/admin/login")

    story_list = (await session.execute(select(SuccessStory).order_by(SuccessStory.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("stories.html", {"request": request, "story_list": story_list})

@router.get("/stories/{action}/{story_id}")
async def handle_story_action(
    request: Request,
    action: str,
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: str = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/admin/login")

    story = (await session.execute(select(SuccessStory).where(SuccessStory.id == story_id))).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if action == "approve":
        story.status = StoryStatus.APPROVED
    elif action == "reject":
        story.status = StoryStatus.REJECTED
    elif action == "delete":
        await session.delete(story)

    await session.commit()
    return RedirectResponse(url="/admin/stories", status_code=status.HTTP_302_FOUND)
