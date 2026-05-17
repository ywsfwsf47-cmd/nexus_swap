from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 1. إعداد قاعدة البيانات (SQLite)
DATABASE_URL = "sqlite:///./nexus_swap.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. تصميم جدول المستخدمين
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)  
    skills = Column(String, default="")  
    interests = Column(String, default="")  
    points = Column(Integer, default=100)  

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- المسارات والـ Routes ---

# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# صفحة التسجيل (GET)
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

# استقبال بيانات التسجيل والتحويل التلقائي للوحة التحكم (POST)
@app.post("/register")
async def register_user(
    username: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...),
    skills: str = Form(...),
    interests: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user_email = db.query(User).filter(User.email == email).first()
    if db_user_email:
        return "البريد الإلكتروني مسجل بالفعل!"
        
    db_user_name = db.query(User).filter(User.username == username).first()
    if db_user_name:
        return "اسم المستخدم هذا مأخوذ بالفعل! اختر اسماً آخر."
    
    new_user = User(
        username=username, 
        email=email, 
        password=password, 
        skills=skills,
        interests=interests
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url=f"/dashboard?username={username}", status_code=status.HTTP_303_SEE_OTHER)

# مسار لوحة التحكم (Dashboard) + ميزة البحث وعرض المستخدمين
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    username: str, 
    search: str = None, 
    db: Session = Depends(get_db)
):
    # جلب بيانات المستخدم الحالي
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return RedirectResponse(url="/register")
    
    # ميزة البحث: إذا كان هناك كلمة بحث، نبحث عنها في المهارات أو الاهتمامات
    if search:
        all_users = db.query(User).filter(
            User.username != username, # عدم إظهار الحساب الحالي في البحث
            or_(
                User.skills.like(f"%{search}%"),
                User.interests.like(f"%{search}%")
            )
        ).all()
    else:
        # إذا لم يكن هناك بحث، نعرض آخر 5 مستخدمين مسجلين في الشبكة لتبادل المهارات معهم
        all_users = db.query(User).filter(User.username != username).order_by(User.id.desc()).limit(5).all()
    
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={"user": user, "all_users": all_users, "search_query": search}
    )
