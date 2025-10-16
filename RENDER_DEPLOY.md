# Deploy na Render.com - Inštrukcie

## Súbory potrebné pre deployment:
- flask_app.py
- database.py
- config.py
- requirements.txt
- Procfile (alebo render.yaml)

## Kroky:

1. **Vytvorte nový Web Service na Render.com**
   - Dashboard → New → Web Service
   
2. **Vyberte "Deploy from GitHub" alebo "Public Git repository"**
   - Ak nemáte GitHub: použite "Empty project" a nahrajte súbory

3. **Nastavenia:**
   - Name: `launchpad-api`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn flask_app:application`
   - Instance Type: `Free`

4. **Environment Variables** (nastavte v Render):
   Zatiaľ žiadne - databázové údaje sú v config.py

5. **Deploy!**
   - Kliknite "Create Web Service"
   - Počkajte 2-3 minúty na build

6. **Získajte URL:**
   - Bude niečo ako: `https://launchpad-api.onrender.com`

## Po deploye:
- Otestujte: `https://VAŠE-URL.onrender.com/api/health`
- Aktualizujte Android app s novým URL
