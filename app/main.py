import os
from typing import Optional
from fastapi import FastAPI, Request, Form, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from .encryption import save_admin_credentials, get_admin_credentials
from .bot_manager import trigger_admin_bot, trigger_activator_bot, trigger_mass_delete, trigger_reset_data, active_connections

load_dotenv()

app = FastAPI(title="Google Workspace AutoBot")

# Session setup
SECRET_KEY = os.getenv("SESSION_SECRET", "super-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, msg: str = None):
    # Authenticated if the bot successfully established a session
    if not request.session.get('logged_in'):
        return RedirectResponse(url='/login')
    
    email = request.session.get('email')
    domain = request.session.get('domain')
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "email": email, 
        "domain": domain,
        "msg": msg
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def process_login(request: Request, email: str = Form(...), password: str = Form(...)):
    if '@' not in email:
        return RedirectResponse(url='/login?error=Invalid email', status_code=303)
    
    domain = email.split('@')[1]
    request.session['temp_email'] = email
    request.session['temp_password'] = password
    request.session['domain'] = domain
    
    return RedirectResponse(url='/sync-session', status_code=303)

@app.get("/sync-session", response_class=HTMLResponse)
async def sync_page(request: Request):
    email = request.session.get('temp_email')
    if not email:
        return RedirectResponse(url='/login')
    
    domain = request.session.get('domain')
    return templates.TemplateResponse("sync.html", {
        "request": request,
        "email": email,
        "domain": domain
    })

@app.post("/sync-session")
async def start_sync_session(request: Request, background_tasks: BackgroundTasks):
    email = request.session.get('temp_email')
    password = request.session.get('temp_password')
    domain = request.session.get('domain')
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Missing credentials in session")
    
    # Trigger Selenium sync in background
    trigger_admin_bot(domain, email, background_tasks, password=password)
    return {"status": "sync_started"}

@app.get("/logout")
async def logout(request: Request):
    # Clear both permanent and temporary session data
    for key in ['email', 'temp_email', 'temp_password', 'domain', 'logged_in']:
        request.session.pop(key, None)
    return RedirectResponse(url='/login')

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    domain = request.session.get('domain')
    if not request.session.get('logged_in') or not domain:
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
    email = request.session.get('email')
    if not domain or not email:
        return RedirectResponse(url='/login')
    
    success, msg = trigger_admin_bot(
        domain, 
        email,
        background_tasks,
        user_count=user_count,
        name_prefix=name_prefix,
        random_names=random_names
    )
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.post("/run/activator")
async def run_activator(request: Request, background_tasks: BackgroundTasks):
    domain = request.session.get('domain')
    email = request.session.get('email')
    if not domain or not email:
        return RedirectResponse(url='/login', status_code=303)
    
    success, msg = trigger_activator_bot(domain, email, background_tasks)
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.post("/run/mass-delete")
async def run_mass_delete(
    request: Request, 
    background_tasks: BackgroundTasks
):
    domain = request.session.get('domain')
    email = request.session.get('email')
    if not domain or not email:
        return RedirectResponse(url='/login', status_code=303)
    
    success, msg = trigger_mass_delete(domain, email, background_tasks)
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.post("/run/reset")
async def run_reset(request: Request, background_tasks: BackgroundTasks):
    domain = request.session.get('domain')
    if not domain:
        return RedirectResponse(url='/login', status_code=303)
    
    success, msg = trigger_reset_data(background_tasks)
    return RedirectResponse(url='/?msg=' + msg, status_code=303)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Session promotion logic: When bot confirms dashboard entry
            if data == "promote_session":
                session = websocket.scope.get("session", {})
                temp_email = session.get("temp_email")
                if temp_email:
                    websocket.scope["session"]["logged_in"] = True
                    websocket.scope["session"]["email"] = temp_email
                    # Clear password from session for security
                    websocket.scope["session"].pop("temp_password", None)
                    print(f"[SYSTEM] Session promoted for {temp_email}")
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
