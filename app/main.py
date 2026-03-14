import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

from .encryption import save_admin_credentials, get_admin_credentials
from .bot_manager import trigger_admin_bot, trigger_activator_bot

load_dotenv()

app = FastAPI(title="Google Workspace AutoBot")

# Session & OAuth setup
SECRET_KEY = os.getenv("SESSION_SECRET", "super-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')
    
    domain = request.session.get('domain')
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": user, 
        "domain": domain
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get('userinfo')
    if user:
        request.session['user'] = user
        # Ekstrak domain dari email
        email = user.get('email', '')
        if '@' in email:
            domain = email.split('@')[1]
            request.session['domain'] = domain
            
    return RedirectResponse(url='/')

@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    request.session.pop('domain', None)
    return RedirectResponse(url='/login')

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    domain = request.session.get('domain')
    if not domain:
        return RedirectResponse(url='/login')
    
    creds = get_admin_credentials(domain)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "domain": domain,
        "creds": creds
    })

@app.post("/settings")
async def save_settings(request: Request, email: str = Form(...), password: str = Form(...)):
    domain = request.session.get('domain')
    if not domain:
        raise HTTPException(status_code=403, detail="Not logged in")
    
    save_admin_credentials(domain, email, password)
    
    creds = get_admin_credentials(domain)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "domain": domain,
        "creds": creds,
        "message": "Credentials saved successfully!"
    })

@app.post("/run/admin")
async def run_admin(request: Request, background_tasks: BackgroundTasks):
    domain = request.session.get('domain')
    if not domain:
        return RedirectResponse(url='/login')
    
    success, msg = trigger_admin_bot(domain, background_tasks)
    return RedirectResponse(url='/?msg=' + msg)

@app.post("/run/activator")
async def run_activator(request: Request, background_tasks: BackgroundTasks):
    domain = request.session.get('domain')
    if not domain:
        return RedirectResponse(url='/login')
    
    success, msg = trigger_activator_bot(domain, background_tasks)
    return RedirectResponse(url='/?msg=' + msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
