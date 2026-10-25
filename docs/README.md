# Documentación de SIGECUE

Sistema de Gestión de Carreras por Encuentro de la Universidad de Holguín (UHO).
Cubre el ciclo de ingreso a las carreras por encuentro: oferta académica,
expresión de interés, plan de plazas, convocatoria de solicitud, otorgamiento
de plazas y prematrícula.

## Índice

| Documento | Contenido |
|---|---|
| [DESARROLLO.md](DESARROLLO.md) | Cómo levantar el proyecto en una máquina local |
| [DESPLIEGUE.md](DESPLIEGUE.md) | Cómo instalar y poner en producción en un servidor Linux |
| [DOCKER.md](DOCKER.md) | Cómo contenerizar el sistema más adelante (pendiente de implementar) |
| [GIT.md](GIT.md) | Flujo de ramas y formato de commits |
| [DECISIONES.md](DECISIONES.md) | Decisiones del cliente que se apartan o precisan la ERS |
| [ANOTACIONES.md](ANOTACIONES.md) | Elementos provisionales y pendientes de material externo |

## Arquitectura

```
navegador ──► nginx ──┬──► frontend/dist (React compilado, archivos estáticos)
                      └──► /api, /admin ──► gunicorn ──► Django + DRF ──► PostgreSQL
                                                              │
                                                              └──► Redis ◄── Celery (worker + beat)
```

- **backend/** — API REST con Django + Django REST Framework.
  - `config/`: configuración del proyecto. `settings/base.py` es común;
    `dev.py` (SQLite, depuración) y `prod.py` (PostgreSQL, HTTPS) la extienden.
  - `apps/`: una app de Django por dominio (`core`, y las que se agreguen
    por feature). Cada app separa modelos, serializers, vistas y, si la lógica
    es compleja, `services.py`.
  - Todas las rutas de la API cuelgan de `/api/v1/`.
- **frontend/** — SPA con React + Vite.
  - `src/components/`: componentes reutilizables.
  - `src/pages/`: pantallas.
  - `src/hooks/`: hooks propios.
  - `src/services/`: acceso a la API.
  - `src/styles/tokens.css`: único CSS global (variables de diseño y reset).
    El resto de los estilos usa CSS Modules (`Componente.module.css`).
- **Celery + Redis** — tareas programadas (cierre automático de convocatorias,
  limpieza de cuentas no activadas, recordatorios, etc.).
