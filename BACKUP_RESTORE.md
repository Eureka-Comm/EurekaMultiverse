# Backup / Restore — Frontend EUREKA (versión estable)

> **Backup ESTABLE (más reciente, recomendar):** `D:\DS_ARNES\IA Agentes\_backup_frontend_stable_2026-08-31_130804`
> **Fecha:** 2026-08-31 13:08:04 — frontend estilo **DeepSeek Harness** completo (tema claro, sidebar colapsable con iconos SVG, rail neuronal, chat markdown + copiar + stats, tabs, intake con fondo blanco + botón "Ask").
> **Qué incluye:** snapshot completo de la fuente (`src/` 103 archivos, `public/`, `package.json` con `react-markdown`/`remark-gfm`, `package-lock.json`, configs Vite/tsconfig, `index.html`). Excluye `node_modules`/`dist`/`.vite` (regenerables). Verificado 121/121.
>
> **Backups anteriores:** `_backup_frontend_stable_2026-08-31_125840` · `_backup_frontend_2026-08-31_102110`.

---

## Cómo hacer ROLLBACK (si el nuevo frontend se rompe)

1. **Detener** el servidor de Vite si está corriendo.
2. **Reemplazar** la carpeta actual del frontend por el backup **estable**:

   ```powershell
   # Desde D:\DS_ARNES\IA Agentes
   Remove-Item -Recurse -Force eureka-frontend\src, eureka-frontend\public
   Copy-Item -Recurse -Force _backup_frontend_stable_2026-08-31_130804\src eureka-frontend\src
   Copy-Item -Recurse -Force _backup_frontend_stable_2026-08-31_130804\public eureka-frontend\public
   Copy-Item -Force _backup_frontend_stable_2026-08-31_130804\package.json eureka-frontend\package.json
   Copy-Item -Force _backup_frontend_stable_2026-08-31_130804\package-lock.json eureka-frontend\package-lock.json
   Copy-Item -Force _backup_frontend_stable_2026-08-31_130804\vite.config.ts eureka-frontend\vite.config.ts
   Copy-Item -Force _backup_frontend_stable_2026-08-31_130804\tsconfig.json eureka-frontend\tsconfig.json
   Copy-Item -Force _backup_frontend_stable_2026-08-31_130804\tsconfig.app.json eureka-frontend\tsconfig.app.json
   Copy-Item -Force _backup_frontend_stable_2026-08-31_130804\tsconfig.node.json eureka-frontend\tsconfig.node.json
   Copy-Item -Force _backup_frontend_stable_2026-08-31_130804\index.html eureka-frontend\index.html
   ```
   > `node_modules` se regenera con `npm install` (el `package.json` incluye `react-markdown` + `remark-gfm`).

3. **Reinstalar** dependencias:
   ```powershell
   cd eureka-frontend
   npm install
   ```
4. **Re-arrancar** el frontend:
   ```powershell
   cd eureka-frontend; npm run dev -- --host 127.0.0.1 --port 5173
   ```

---

## Alternativa: backup completo (si prefieres incluir node_modules)

El snapshot excluye `node_modules`/`dist` (rápido). Si prefieres un clon idéntico:

```powershell
Copy-Item -Recurse -Force eureka-frontend <destino>\eureka-frontend
```

*Fin de la guía de backup/restauración.*

