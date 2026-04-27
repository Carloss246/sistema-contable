# Desplegar en Render (Gratis)

## Paso 1: Preparar tu código en GitHub

1. Sube tu proyecto a GitHub:
   ```bash
   git init
   git add .
   git commit -m "Sistema contable listo para desplegar"
   git branch -M main
   git remote add origin https://github.com/tu-usuario/sistema-contable.git
   git push -u origin main
   ```

## Paso 2: Crear cuenta en Render

1. Ve a `https://render.com`
2. Haz clic en `Sign up`
3. Regístrate con GitHub (es lo más fácil)
4. Autoriza la conexión

## Paso 3: Crear nuevo servicio en Render

1. En el dashboard, haz clic en `+ New`
2. Selecciona `Web Service`
3. Elige `Deploy an existing repository from GitHub`
4. Busca y selecciona tu repositorio `sistema-contable`
5. Configura así:
   - **Name**: `sistema-contable`
   - **Runtime**: `Docker`
   - **Plan**: Free
   - **Region**: `Ohio` (más rápido para Latinoamérica)

## Paso 4: Agregar variables de entorno

En la sección `Environment`:
- Haz clic en `Add from file` (opcional) o agrega manual:

```
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-key-real
APP_SESSION_SECRET=pon-una-clave-larga-y-segura-minimo-32-caracteres
```

**Nota**: `OLLAMA_BASE_URL` y `OLLAMA_MODEL` ya están en `render.yaml`, pero no se usarán (Ollama no funciona en Render). La app usará `local-reglas` automáticamente.

## Paso 5: Desplegar

1. Haz clic en `Create Web Service`
2. Espera ~3-5 minutos a que Render:
   - Clone tu repo
   - Construya la imagen Docker
   - Inicie el contenedor
3. Cuando veas `Your service is live` con una URL, ¡listo!

## Paso 6: Acceder a tu app

Tu app estará en: `https://sistema-contable.onrender.com` (o similar)

## Paso 7: Configurar dominio (opcional)

1. En Render, ve a `Settings` del servicio.
2. En `Custom Domain`, agrega tu dominio.
3. En tu registrador de dominio (Namecheap, etc.), apunta el DNS a la URL de Render.
4. Espera propagación (~1 hora).

## Notas importantes

- **Plan Free**: Se "duerme" después de 15 minutos sin tráfico. Al acceder, se despiertan en ~20 segundos. Hay versión Pro ($7 USD/mes) para evitar esto.
- **IA**: En Render usará `local-reglas` (gratis, offline). Ollama no funciona porque no mantiene estado persistente.
- **BD**: Supabase funciona perfectamente desde Render.
- **Redeploys**: Cada `git push` a `main` redeploya automáticamente.

## Alternativas: Railway y Koyeb

- **Railway.app**: Similar a Render, plan free con $5 USD crédito gratuito.
- **Koyeb.com**: Similar, plan free con límites.

Todos son prácticamente iguales en facilidad. Render es quizás el más amigable.
