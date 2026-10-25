# Integración con el SGU (auth.uho.edu.cu)

RE-002 y RF-012 piden que los usuarios internos se autentiquen contra el
Sistema de Gestión de Usuarios de la UHO. Todavía no se conoce el protocolo
que ofrece el SGU (OAuth 2.0 o LDAP), así que el sistema trae un **adaptador**
desactivado y, mientras tanto, los usuarios internos usan una contraseña local.

## Cómo funciona hoy

- Cada usuario tiene un campo `origen`: `local` o `sgu`.
- `local`: la contraseña se valida contra el hash Argon2 guardado en SIGECUE.
- `sgu`: la contraseña **no** se guarda en SIGECUE. En el login,
  `apps/users/services/autenticacion.py` llama al proveedor configurado en
  `SGU_PROVEEDOR`. Si no hay proveedor configurado, esos usuarios no pueden
  entrar.
- El rol y la entidad del usuario se gestionan siempre en SIGECUE, aunque la
  identidad venga del SGU.
- Los aspirantes no pasan por el SGU: siempre son `local`.

El contrato está en `apps/users/sgu.py`:

```python
class ProveedorSGU:
    def autenticar(self, username: str, password: str) -> IdentidadSGU | None: ...
```

## Pasos para conectarlo

### 1. Averiguar con la Dirección de Informatización

- Protocolo: LDAP (usuario y contraseña validados en el servidor) u OAuth 2.0 /
  OpenID Connect (redirección a la página de login del SGU).
- Para LDAP: host, puerto, si usa LDAPS/StartTLS, base DN de usuarios,
  atributo de usuario (`uid`, `sAMAccountName`...), y si hace falta una cuenta
  de servicio para buscar.
- Para OAuth 2.0: URL de autorización, de token y de userinfo, `client_id` y
  `client_secret` registrados para SIGECUE, URL de retorno permitida y claims
  disponibles (usuario, nombre, email).

### 2a. Si es LDAP

Encaja directamente con el contrato actual (usuario + contraseña).

1. Pedir aprobación para agregar la librería `ldap3` a `requirements/base.txt`.
2. Crear `apps/users/sgu_ldap.py`:
   ```python
   from django.conf import settings
   from ldap3 import Connection, Server

   from .sgu import IdentidadSGU, ProveedorSGU


   class ProveedorLDAP(ProveedorSGU):
       def autenticar(self, username, password):
           if not password:
               return None
           servidor = Server(settings.SGU_LDAP_HOST, use_ssl=True)
           dn = settings.SGU_LDAP_USER_DN.format(username=username)
           conexion = Connection(servidor, user=dn, password=password)
           if not conexion.bind():
               return None
           conexion.search(dn, "(objectClass=person)", attributes=["givenName", "sn", "mail"])
           entrada = conexion.entries[0] if conexion.entries else None
           conexion.unbind()
           return IdentidadSGU(
               username=username,
               nombre=str(entrada.givenName) if entrada else "",
               apellidos=str(entrada.sn) if entrada else "",
               email=str(entrada.mail) if entrada else "",
           )
   ```
3. Agregar a `config/settings/base.py` las variables `SGU_LDAP_HOST` y
   `SGU_LDAP_USER_DN` (p. ej. `uid={username},ou=people,dc=uho,dc=edu,dc=cu`)
   leídas del `.env`.
4. En `.env`: `SGU_PROVEEDOR=apps.users.sgu_ldap.ProveedorLDAP`.
5. Dar de alta a los usuarios internos con `origen=sgu` y sin contraseña
   (`POST /api/v1/admin/usuarios/` con `"origen": "sgu"`).

### 2b. Si es OAuth 2.0 / OpenID Connect

Aquí el usuario no escribe la contraseña en SIGECUE: se le redirige al SGU.
El contrato `autenticar(username, password)` no aplica y hay que agregar un
flujo nuevo:

1. Pedir aprobación para una librería cliente (p. ej. `authlib`).
2. Backend: dos endpoints nuevos.
   - `GET /api/v1/auth/sgu/iniciar/`: genera `state` y redirige a la URL de
     autorización del SGU.
   - `GET /api/v1/auth/sgu/retorno/`: valida `state`, canjea el `code` por un
     token, consulta userinfo, busca al usuario por `username` con
     `origen=sgu`, emite los tokens de SIGECUE con
     `autenticacion.emitir_tokens(usuario)`, deja la cookie de refresh y
     redirige al frontend.
3. Frontend: botón "Entrar con cuenta UHO" en el login que navega a
   `/api/v1/auth/sgu/iniciar/`.
4. El login con usuario y contraseña sigue igual para los aspirantes.

### 3. Probar

- `tests/test_autenticacion.py::TestSGU` muestra cómo sustituir el proveedor
  por uno de prueba con `settings.SGU_PROVEEDOR`.
- Comprobar con un usuario real que: entra con su clave del SGU, una clave
  incorrecta cuenta para el bloqueo temporal, y un usuario bloqueado en
  SIGECUE no entra aunque el SGU lo acepte.
