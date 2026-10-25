# Flujo de Git

## Ramas

- `develop` es la rama por defecto y la base de todo el desarrollo.
- No se trabaja directo sobre `main` ni `master`.
- Cada funcionalidad se desarrolla en su propia rama, una a la vez:

```bash
git checkout develop
git checkout -b feature/nombre-en-kebab-case
# ... commits pequeños y atómicos ...
git push -u origin feature/nombre-en-kebab-case

# Cuando la feature está estable:
git checkout develop
git merge feature/nombre-en-kebab-case
git push origin develop
git branch -d feature/nombre-en-kebab-case
git push origin --delete feature/nombre-en-kebab-case
```

## Formato de commits

```
tipo(alcance): descripcion breve
```

- Tipos permitidos: `feat`, `fix`, `style`, `docs`.
- El alcance es obligatorio.

Ejemplos:

```
feat(auth): agregar login con jwt
fix(users): corregir validacion de email
style(button): ajustar padding y colores
docs(readme): actualizar instrucciones de instalacion
```
