# 🔌 Sync CrearPSL — Instrucciones de deploy

## 📦 Archivos
- `sync_crearpsl.py` — el scraper

## 🔧 Variables de entorno a agregar en Render (bot-cpsl)

```
CREARPSL_USER         = jsanchez
CREARPSL_PASS         = crearpsl25
CREARPSL_FIELD_USER   = usuario       ← AJUSTAR según el form real
CREARPSL_FIELD_PASS   = clave         ← AJUSTAR según el form real
SYNC_INTERVAL_SEG     = 1800          ← 30 min
SHEET_CRM_ID          = 1IoCYs1qfOTdn3XWyeK64jsUfAXOFgv3Wa6uJBM-lR2Y
```

> `GOOGLE_CREDENTIALS` ya está configurado en el bot, se reutiliza.

## 🔧 Requirements (agregar al requirements.txt si no están)

```
beautifulsoup4>=4.12.0
requests>=2.31.0
```

Las demás (google-api-python-client, google-auth) ya están.

## 🚀 Cómo activarlo en bot_whatsapp.py

Agregar al final del bloque de imports / startup, junto a los otros módulos:

```python
# ── Sincronizador CrearPSL Global ──
try:
    from sync_crearpsl import iniciar_thread as iniciar_sync_crearpsl
    iniciar_sync_crearpsl()
    log.info("✅ Sync CrearPSL iniciado — cada 30 min")
except Exception as e:
    log.warning(f"⚠ Sync CrearPSL no inició: {e}")
```

## 🧪 Test standalone (antes de deploy)

Para probar localmente que el login y scraping funcionan:

```bash
export CREARPSL_USER=jsanchez
export CREARPSL_PASS=crearpsl25
export CREARPSL_FIELD_USER=usuario
export CREARPSL_FIELD_PASS=clave
export GOOGLE_CREDENTIALS='{... json ...}'

python3 sync_crearpsl.py
```

Debe imprimir:
```
✅ Login OK en crearpslglobal.com
  · datosparticipante.php → N filas
  · reporte_detallegestion.php → N filas
  ...
✅ Ciclo completo: TOTAL filas en X.Xs
```

## ⚠️ Si el login falla

Lo más probable: los nombres de los campos del form son distintos a `usuario`/`clave`.

**Cómo averiguar los nombres correctos:**
1. Abrir https://crearpslglobal.com/admin/login.php en Chrome
2. F12 → Network → marcar "Preserve log"
3. Loguearse normalmente
4. Buscar el POST a login.php → pestaña "Payload"
5. Ver los nombres exactos. Ejemplos comunes en sistemas PHP:
   - `usuario` / `clave`
   - `usuario` / `password`
   - `user` / `pass`
   - `txtusuario` / `txtclave`
   - `email` / `pwd`

Una vez identificados, actualizar las variables de entorno `CREARPSL_FIELD_USER` y `CREARPSL_FIELD_PASS` en Render. NO hace falta tocar el código.

## 📊 Lo que llegará al Sheet del CRM

8 hojas nuevas (se crean automáticamente):

| Hoja | Origen | Refresco |
|------|--------|----------|
| `CREARPSL_PARTICIPANTES` | datosparticipante.php?mostrar=todos | 30 min |
| `CREARPSL_GESTION` | reporte_detallegestion.php | 30 min |
| `CREARPSL_FACTURAS` | reporte_cierrefactura.php | 30 min |
| `CREARPSL_LLAMADAS_C1` | resultado_llamadas.php | 30 min |
| `CREARPSL_LLAMADAS_C2` | resultado_llamadasc2.php | 30 min |
| `CREARPSL_ASIGNACIONES_C1` | listar_asignaciones.php | 30 min |
| `CREARPSL_ASIGNACIONES_C2` | listar_asignacionesc2.php | 30 min |
| `CREARPSL_AUDITORIA` | log de cada corrida | append |

## 🔄 Próximo paso (después del primer deploy exitoso)

Actualizar el CRM (`app_buscador.py`) y el bot para que:
- La **Sala de Guerra** lea `CREARPSL_PARTICIPANTES` en lugar de los XLSX cacheados
- Las métricas de avance por CC vengan de `CREARPSL_LLAMADAS_C1` (datos reales en lugar de hardcoded)
- El **Cerebro Cuántico** tenga acceso al contexto fresco de las 7 hojas

Eso lo hacemos en el siguiente paso, una vez confirmes que el sync trae datos.
