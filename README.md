# SETU — Emergency Ambulance & Hospital Coordination System

A real-time coordination system between first responders, hospitals, patients, and admins.

## Setup & Run

**1. Clone the repo**
```bash
git clone https://github.com/Kkj1203/SETU-final.git
cd SETU-final
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Run the server**
```bash
python app.py
```

**4. Open in browser**
```
http://127.0.0.1:5000
```

## First Time Setup

1. Go to `http://127.0.0.1:5000`
2. Click **Admin → Sign Up**
3. Enter bootstrap key: `SETU2026`
4. Create your admin account
5. Log in as Admin and create Hospital Staff and First Responder accounts

## Demo (Two Browsers Simultaneously)

- Open First Responder dashboard in **Normal browser window/tab**
- Open Hospital Staff dashboard in **Incognito**
- Both sessions run independently — demo the full ping/accept flow side by side

## Roles

| Role | Access |
|---|---|
| Patient | Self-signup, view and edit personal + medical profile |
| First Responder | Search patients, report site situation, ping hospitals |
| Hospital Staff | Receive pings, view patient details, accept or decline |
| Admin | Create staff accounts, view all users |

## Tech Stack

- Python + Flask
- SQLite (auto-generated on first run)
- Vanilla HTML + JavaScript + Bootstrap 5
