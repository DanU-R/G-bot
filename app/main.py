import os
from typing import Optional
from fastapi import FastAPI, Request, Form, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

from .encryption import save_admin_credentials, get_admin_credentials
from .bot_manager import trigger_admin_bot, trigger_activator_bot, trigger_mass_delete, trigger_reset_data, active_connections

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
async def dashboard(request: Request, msg: str = None):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')
    
    domain = request.session.get('domain')
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": user, 
        "domain": domain,
        "msg": msg
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
async def run_admin(
    request: Request, 
    background_tasks: BackgroundTasks,
    user_count: int = Form(4),
    name_prefix: str = Form("User"),
    random_names: bool = Form(False)
):
    domain = request.session.get('domain')
    user = request.session.get('user')
    if not domain or not user:
        return RedirectResponse(url='/login')
    
    success, msg = trigger_admin_bot(
        domain, 
        user.get('email'),
        background_tasks,
        user_count=user_count,
        name_prefix=name_prefix,
        random_names=random_names
    )
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.post("/run/activator")
async def run_activator(request: Request, background_tasks: BackgroundTasks):
    domain = request.session.get('domain')
    user = request.session.get('user')
    if not domain or not user:
        return RedirectResponse(url='/login')
    
    success, msg = trigger_activator_bot(domain, user.get('email'), background_tasks)
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.post("/run/mass-delete")
async def run_mass_delete(
    request: Request, 
    background_tasks: BackgroundTasks
):
    domain = request.session.get('domain')
    user = request.session.get('user')
    if not domain or not user:
        return RedirectResponse(url='/login')
    
    success, msg = trigger_mass_delete(domain, user.get('email'), background_tasks)
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.post("/run/reset")
async def run_reset(request: Request, background_tasks: BackgroundTasks):
    domain = request.session.get('domain')
    if not domain:
        return RedirectResponse(url='/login')
    
    success, msg = trigger_reset_data(background_tasks)
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection open and wait for messages (e.g. ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
