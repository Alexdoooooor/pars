================================================================================
Почему 404 на https://ваш-домен/pars/api/public/status
================================================================================

Этот URL должен обрабатывать процесс uvicorn (FastAPI), а не искаться как файл
на диске. Если в конфиге веб-сервера для /pars/ указан только Alias/DocumentRoot
к папке с HTML — запросы к /pars/api/... получат 404.

Нужно ОДНО из:
  A) Проксировать ВЕСЬ префикс /pars/ на uvicorn (рекомендуется), ИЛИ
  B) Отдельно проксировать хотя бы /pars/api/ на uvicorn.

На сервере должны быть выполнены:
  1) Установлены зависимости: pip install -r requirements.txt
  2) Запущен uvicorn, например:
       cd /path/to/pars
       python3 -m uvicorn server.main:app --host 127.0.0.1 --port 8765
  3) Запущен parser_service (отдельный процесс):
       cd /path/to/pars
       python3 -m uvicorn parser_service.main:app --host 127.0.0.1 --port 8810
  4) В .env:
       APP_BASE_URL=/pars
       PARSER_SERVICE_URL=http://127.0.0.1:8810
       PARSER_SERVICE_API_KEY=<тот же ключ, что и в parser_service>

Проверка с самого сервера (SSH):
  curl -sS http://127.0.0.1:8765/pars/api/public/status
  curl -sS http://127.0.0.1:8810/health

Если здесь JSON от обоих URL — сервисы живы; тогда чинить только nginx/Apache.

Файлы-примеры в этой папке:
  - nginx-aisidora-pars.example.conf
  - apache-pars.example.conf
  - PARSER-API.txt  (отдельный HTTP-сервис парсера, порт 8810)
