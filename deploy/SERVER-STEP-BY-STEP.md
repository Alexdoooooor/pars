# Price Intelligence: пошаговый деплой на сервер (Linux + Nginx)

Ниже команды для запуска на сервере по SSH.  
Предполагается, что проект уже загружен в каталог `/var/www/pars` (или другой путь).

## 0) Что должно быть в проекте

- `requirements.txt`
- `server/main.py`
- `parser_service/main.py`
- `sql/schema.sql`
- `.env` (боевой)

## 1) Базовая проверка окружения

```bash
whoami
pwd
python3 --version
pip3 --version
nginx -v
mysql --version
```

## 2) Установка зависимостей Python

```bash
cd /var/www/pars
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## 3) Подготовка `.env` (пример для прода)

Создайте/обновите файл `.env` в корне проекта:

```dotenv
APP_ENV=production
APP_DEBUG=false
APP_BASE_URL=/pars

DB_HOST=127.0.0.1
DB_PORT=3306
PI_DB_NAME=vtb_price_intel
DB_USER=YOUR_DB_USER
DB_PASSWORD=YOUR_DB_PASSWORD
# DB_SOCKET=...

ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_THIS_STRONG_PASSWORD

PARSER_MODE=live
PARSER_SERVICE_URL=http://127.0.0.1:8810
PARSER_SERVICE_API_KEY=CHANGE_THIS_LONG_SECRET
PARSER_SERVICE_TIMEOUT=120
```

Важно:
- `PARSER_SERVICE_API_KEY` должен совпадать в main API и parser_service.
- Если используете TCP к MySQL, не включайте `DB_SOCKET`.

## 4) Создание базы и таблиц

```bash
mysql -u YOUR_DB_USER -p -e "CREATE DATABASE IF NOT EXISTS vtb_price_intel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u YOUR_DB_USER -p vtb_price_intel < sql/schema.sql
```

## 5) Быстрый запуск без systemd (проверочный)

В двух SSH-сессиях:

Сессия 1:
```bash
cd /var/www/pars
python3 -m uvicorn parser_service.main:app --host 127.0.0.1 --port 8810
```

Сессия 2:
```bash
cd /var/www/pars
python3 -m uvicorn server.main:app --host 127.0.0.1 --port 8765
```

Проверка:

```bash
curl -sS http://127.0.0.1:8810/health
curl -sS http://127.0.0.1:8765/pars/api/public/status
```

## 6) Nginx: проксирование `/pars/`

Скопируйте `deploy/nginx-aisidora-pars.example.conf` в ваш `server { ... }`.

Ключевой блок:

```nginx
location /pars/ {
    proxy_pass http://127.0.0.1:8765/pars/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
}
```

Применение:

```bash
nginx -t
sudo systemctl reload nginx
```

## 7) Перевод в фон (systemd)

Создайте сервисы (пример ниже), затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pi-parser pi-main
sudo systemctl restart pi-parser pi-main
sudo systemctl status pi-parser --no-pager -l
sudo systemctl status pi-main --no-pager -l
```

## 8) Проверка снаружи

```bash
curl -I https://YOUR_DOMAIN/pars/
curl -sS https://YOUR_DOMAIN/pars/api/public/status
```

## 9) Типовые ошибки

- `404 /pars/api/...`: Nginx отдает статику вместо proxy.
- `401` в parser API: не совпадает `PARSER_SERVICE_API_KEY`.
- `Can't connect to MySQL`: не запущен MySQL или неверные `DB_HOST/PORT/USER/PASSWORD`.
- `DB_SOCKET` на Linux-сервере задан неверно: переключитесь на TCP `127.0.0.1:3306`.
