# Instalación desde cero

Probada el 11/10/2026 sobre una base PostgreSQL 15 vacía, a partir de un clon
limpio del repositorio: análisis de un ejemplo, comprobante
en PDF e inicio de una revisión B-1 v1.2 con sus 11 controles.

## Requisitos

- Python 3.11 o posterior (en producción, Python 3.12 desde la versión 0.10.64).
- PostgreSQL 15 (no requiere extensiones).
- Opcional: `tesseract` con los idiomas `spa` y `eng`, para leer PDF escaneados
  e imágenes en el propio servidor. Sin él, esas lecturas se declaran como no
  realizadas; Excel y CSV no lo necesitan.
- HTTPS delante de la aplicación (por ejemplo, nginx). La cookie de sesión es
  `Secure`: por HTTP solo funciona entrando por `localhost`.

## Pasos

1. Crear la base y su usuario:

   ```sql
   CREATE USER gobernanza WITH PASSWORD '...';
   CREATE DATABASE gobernanza OWNER gobernanza;
   ```

2. Instalar dependencias:

   ```bash
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   ```

3. Configurar: copiar `.env.example` a `.env` y completar como mínimo
   `DATABASE_URL`, `SECRET_KEY`, `GOBERNANZA_PASSWORD`, `ADMIN_EMAIL` y
   `PUBLIC_BASE_URL`. Las claves de modelos de lenguaje son opcionales: sin
   ellas, los controles automáticos y el comprobante funcionan igual.

4. Preparar la base:

   ```bash
   venv/bin/python scripts/inicializar_base.py
   ```

   En una base vacía crea las tablas, carga las definiciones de los
   protocolos B-1 y R-1 (`sql/datos_referencia_protocolos.json`) y marca la
   última migración. En una base existente aplica las migraciones pendientes.
   No usar `alembic upgrade head` en una base vacía: la primera migración se
   generó sobre una base que ya existía y falla.

5. Iniciar:

   ```bash
   venv/bin/uvicorn main:app --host 127.0.0.1 --port 6163
   ```

   Al primer arranque se crea la cuenta de administración con `ADMIN_EMAIL` y
   `ADMIN_PASSWORD` (o `GOBERNANZA_PASSWORD` si falta). Para producción, ver la
   unidad de ejemplo en `systemd/gobernanza.service`.

## Claves propias

La aplicación no arranca con los valores de ejemplo ni con claves cortas:

| Variable | Requisito |
| --- | --- |
| `SECRET_KEY` | Al menos 32 caracteres. Generar con `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GOBERNANZA_PASSWORD` | Al menos 12 caracteres, distinta de `SECRET_KEY` |
| `ADMIN_PASSWORD` | Si se define, al menos 12 caracteres |

## Servidor web

La aplicación escucha solo en `127.0.0.1`; se publica con HTTPS detrás de un proxy. Ejemplo para nginx:

```nginx
server {
    listen 443 ssl;
    server_name gobernanza.su-institucion.edu;
    ssl_certificate     /etc/letsencrypt/live/gobernanza.su-institucion.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gobernanza.su-institucion.edu/privkey.pem;
    client_max_body_size 30m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "same-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; object-src 'none'; frame-src https://www.youtube-nocookie.com; base-uri 'self'; frame-ancestors 'none'; form-action 'self'" always;

    location / {
        proxy_pass http://127.0.0.1:6163;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

- Las cabeceras de seguridad las envía el proxy: no omitirlas. Si un bloque `location` agrega sus propias
  cabeceras con `add_header`, repetir ahí las de arriba, porque nginx deja de heredarlas.
- `X-Forwarded-For` es necesaria para que el límite de intentos de ingreso se aplique a cada visitante.
  Uvicorn la acepta de forma predeterminada solo desde `127.0.0.1`; si el proxy está en otra máquina,
  iniciar con `--proxy-headers --forwarded-allow-ips=IP_DEL_PROXY`.
- Comprobar: el registro de acceso de la aplicación debe mostrar direcciones de los visitantes, no
  `127.0.0.1`, y `curl -I https://gobernanza.su-institucion.edu/` debe mostrar las cabeceras.

## Pruebas

```bash
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest -q
```

## Opcional en producción

- Respaldo diario de la base: ver `RESTAURACION-BACKUP.md`.
- Alertas por correo y vigilancia de la cola de análisis:
  `scripts/alerta_errores.py` (cada 10 minutos) y `scripts/vigilar_cola.py`
  (cada 2 minutos), por cron.
