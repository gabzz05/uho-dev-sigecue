# Despliegue con Docker Compose

Forma recomendada de desplegar SIGECUE (RG-021, RE-007, RNF-010, criterio de
aceptación 15). Solo hace falta **Docker con Compose** en el host. Las
dependencias del sistema (Python, Node, PostgreSQL, Redis, nginx y las
librerías de WeasyPrint para los PDF) van dentro de las imágenes.

Para instalar sin Docker, ver [DESPLIEGUE.md](DESPLIEGUE.md).

## Servicios

| Servicio | Imagen | Función |
|---|---|---|
| `db` | `postgres:16-alpine` | Base de datos (volumen `pgdata`) |
| `redis` | `redis:7-alpine` | Broker de Celery |
| `backend` | `sigecue-backend` (`backend/Dockerfile`) | Django + gunicorn. Al arrancar espera a la base, migra, recoge los estáticos y crea el Superadmin si se pidió |
| `worker` | `sigecue-backend` | `celery worker`: correos y tareas en segundo plano |
| `beat` | `sigecue-backend` | `celery beat`: cierres, avisos de prematrícula y retención mensual |
| `web` | `sigecue-web` (`frontend/Dockerfile`) | Compila el frontend y lo sirve con nginx, que hace de proxy de `/api/` y termina el TLS |

**Volúmenes:**

| Volumen | Contenido | Quién lo usa |
|---|---|---|
| `pgdata` | Base de datos | `db` |
| `media` | Archivos privados de los aspirantes | Solo el backend |
| `media_publica` | Imágenes públicas | nginx lo sirve en `/media/` |
| `static` | Estáticos de Django | nginx lo sirve en `/static/` |
| `logs` | Logs de la aplicación | backend, worker y beat |

## Primer arranque (entorno limpio)

```bash
git clone <repositorio> sigecue && cd sigecue
cp .env.example .env

# Generar las claves y pegar las tres líneas en .env
docker compose run --rm --no-deps backend claves

# Editar en .env: POSTGRES_PASSWORD, DJANGO_SUPERUSER_PASSWORD, dominio y SMTP
docker compose up -d --build
```

Después, abrir `https://localhost` (o el dominio configurado) y entrar con el
Superadmin de `.env` en `/login`.

- **Claves:** `FIELD_ENCRYPTION_KEY` y `SEARCH_HASH_KEY` se guardan **fuera del
  servidor**. Si se pierden, CI, correo y celular no se pueden recuperar.
- **Arranque sin claves:** si `.env` no tiene las claves, el backend no
  arranca e indica el comando para generarlas.
- **Puertos:** si 80 o 443 están ocupados, se cambian `WEB_HTTP_PORT` y
  `WEB_HTTPS_PORT`. Con puertos no estándar, la redirección de HTTP a HTTPS
  apunta al 443; hay que entrar directamente por `https://host:PUERTO`.

## Certificado TLS (RG-006)

nginx sirve solo HTTPS (TLS 1.2 y 1.3) y redirige el HTTP.

- **Producción:** copiar el certificado de la UHO en `./certs/sigecue.crt` y
  `./certs/sigecue.key` y reiniciar `web` (`docker compose restart web`).
- **Sin certificado:** se genera uno autofirmado para poder probar. El
  navegador avisa de que no es de confianza.

## Operación

| Tarea | Comando |
|---|---|
| Ver el estado | `docker compose ps` |
| Ver logs | `docker compose logs -f backend` (o `worker`, `beat`, `web`) |
| Comando de Django | `docker compose exec backend python manage.py <comando>` |
| Actualizar a una versión nueva | `git pull && docker compose up -d --build` (las migraciones se aplican solas) |
| Parar | `docker compose down` (los datos quedan en los volúmenes) |

## Copias de seguridad (RG-013, RNF-004)

```bash
# Copia de la base de datos (programarla a diario, con 30 días de retención)
docker compose exec -T db pg_dump -U sigecue -Fc sigecue > sigecue-$(date +%F).dump

# Copia de los archivos privados y públicos
docker run --rm -v sigecue_media:/m -v sigecue_media_publica:/p -v "$PWD":/copia alpine \
    tar czf /copia/archivos-$(date +%F).tgz -C / m p

# Restaurar la base en una instalación nueva (con los servicios parados salvo db)
docker compose up -d db
docker compose exec -T db pg_restore -U sigecue -d sigecue --clean --if-exists < sigecue-AAAA-MM-DD.dump
```

El nombre de los volúmenes lleva delante el de la carpeta del proyecto
(`sigecue_` si se clonó en `sigecue/`): se comprueba con `docker volume ls`.

Si se restaura una copia antigua, hay que volver a ejecutar la retención de
datos (Configuración → Retención de datos) antes de reabrir el sistema. Ver
DESPLIEGUE §5.

## Problemas conocidos

**Error al subir el escudo o la imagen de una carrera** en instalaciones
creadas antes de la versión 1.0.2: el volumen `media_publica` quedó con dueño
`root` y el backend no puede escribir en él. Se corrige una sola vez con:

```bash
docker compose run --rm --no-deps -u root backend chown -R sigecue:sigecue /data/media_publica
```

**502 Bad Gateway después de actualizar** en versiones anteriores a la 1.0.2:
nginx guardaba la IP del contenedor `backend` del arranque y, si se recreaba,
seguía enviando a la antigua. Desde la 1.0.2 la resuelve en cada petición. En
una instalación anterior se arregla con `docker compose restart web`.

## Verificado

Probado en un clon limpio del repositorio:

- **Arranque:** construcción de las imágenes, generación de claves y
  `docker compose up` sin instalar nada en el host.
- **Punto a punto a través de nginx:**
  - landing y rutas del panel;
  - salud de la API, Swagger y estáticos;
  - redirección de HTTP a HTTPS;
  - login del Superadmin;
  - worker y beat de Celery funcionando.
- **Suite de pruebas dentro de la imagen del backend:** 529 pasan, incluidas
  las de PDF (plan de plazas, otorgamiento, prematrícula y solicitudes), que en
  Windows se omiten por falta de GTK.
- **Copia y restauración:** `pg_dump` y `pg_restore` de la base de datos.
