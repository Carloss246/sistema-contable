# Sistema contable con Python + Supabase

Este proyecto implementa un sistema contable base alineado con los principios de los capitulos compartidos de Horngren:

- Contabilidad como sistema de informacion financiera.
- Ecuacion contable: `Activos = Pasivos + Capital`.
- Registro cronologico en diario.
- Traspaso al mayor por cuenta.
- Balanza de comprobacion.
- Estados financieros: Estado de resultados y Balance general.
- Partida doble obligatoria (debe = haber en cada asiento).

## 1) Estructura

- `SQL/001_schema_contable.sql`: tablas, restricciones, funcion de registro y vistas.
- `SQL/002_seed_catalogo_cuentas.sql`: catalogo base de cuentas.
- `app/`: codigo Python.
- `examples/`: ejemplos de asientos en JSON.

## 2) Configuracion de Supabase

1. Crea un proyecto en Supabase.
2. Abre el SQL Editor y ejecuta en orden:
   - `SQL/001_schema_contable.sql`
   - `SQL/002_seed_catalogo_cuentas.sql`
3. Copia `URL` y `API Key` del proyecto.

## 3) Configuracion Python

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Crea archivo `.env` basado en `.env.example`:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-o-service-role-key
APP_SESSION_SECRET=una-clave-larga-y-segura-para-firmar-la-cookie
```

3. Usuarios (Supabase Auth):
- Opcion A: crea usuarios desde `Authentication > Users` en Supabase.
- Opcion B: usa el formulario web `/signup` para registrar usuarios.

4. Login web:
- Abre `http://127.0.0.1:8000/login`
- Inicia sesion con el correo y contraseña del usuario de Supabase Auth.

## 4) Uso web

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Ejecuta la aplicacion web:

```bash
python -m app
```

3. Abre en el navegador:

```text
http://127.0.0.1:8000
```

Pantallas disponibles:
- Inicio
- Login y logout
- Registro de usuarios
- Nuevo asiento
- Catálogo de cuentas
- Libro diario
- Libro mayor
- Balanza de comprobación
- Estado de resultados
- Balance general

## 5) Uso por linea de comandos

### Mostrar catalogo de cuentas

```bash
python -m app.cli catalogo
```

### Registrar asiento (desde JSON)

```bash
python -m app.cli registrar-asiento --fecha 2026-04-27 --descripcion "Aporte inicial" --archivo examples/asiento_aporte_inicial.json
```

### Libro diario

```bash
python -m app.cli diario --desde 2026-01-01 --hasta 2026-12-31
```

### Libro mayor

```bash
python -m app.cli mayor --cuenta 101
```

### Balanza de comprobacion

```bash
python -m app.cli balanza
```

### Estado de resultados

```bash
python -m app.cli estado-resultados
```

### Balance general

```bash
python -m app.cli balance-general
```

## 6) Notas importantes

- No pude crear tu base directamente en la nube porque se requiere acceso a tu cuenta de Supabase; por eso te dejo scripts listos para ejecutar.
- El sistema valida partida doble en Python y en PostgreSQL para evitar asientos descuadrados.
- El balance general incorpora la utilidad del ejercicio al capital para mantener la ecuacion contable.
