# ODI · Inventario completo de órdenes generadas en este chat

**Fecha de consolidación:** 2026-06-22  
**Alcance:** órdenes explícitas, órdenes operativas y directivas de coordinación emitidas o formalizadas durante este hilo.  
**Regla:** la documentación orienta; el terreno manda. Primero leer, luego verificar runtime y después actuar.

---

## A. Órdenes formalizadas como tableros principales

### 1. MULTI_STORE_INVENTORY_CERTIFICATION
- **Registro:** `juandavidjd/odi-vende` · Issue #28.
- **Objetivo:** inventario real, billing, actividad, imágenes, copy, publicación y certificación de DFG, YOKOMAR, VAISAND y KAIQI.
- **Estado:** ACTIVA como tablero multi-store.

### 2. SKU_ODI_AUDIT_CLOSE_GAPS_TESTS_PR
- **Registro:** `juandavidjd/odi-vende` · Issue #35.
- **Objetivo real corregido:** auditar lo existente; completar taxonomía; poblar dedup; crear tests; formalizar PR.
- **Prohibición:** no reconstruir `producto_alias`, `sku_odi` o `sku_hash` desde cero.
- **Estado:** PENDIENTE REAL PC II.

### 3. PIPELINE_ODI_V25_22_RUNTIME_MAP_AND_MANAGEMENT
- **Registro:** `juandavidjd/odi-vende` · Issue #43.
- **Objetivo:** convertir el mapa de 26 pasos del Core Pipeline y sus carriles pendientes en tablero de gestión.
- **Estado:** CORE VERDE OPERATIVO; backlog re-escopado por terreno.

### 4. SRM_SOCIAL_LANDING_STANDARD_V1
- **Registro:** `juandavidjd/odi-vende` · Issue #47.
- **Objetivo:** evolucionar SRM existente hacia hábitat social industrial ODI usando P10, T10 y PAEM como moldes de interacción.
- **Prohibición:** no rebuild, no copiar P10/T10 literalmente, no rediseño visual aislado.
- **Estado:** LISTO PARA ORDEN QUIRÚRGICA.

### 5. ORDEN_CLAUDE_CODE_SRM_SOCIAL_LANDING_STANDARD_V1
- **Destino:** Issue #47.
- **Objetivo:** implementación quirúrgica sobre Home, Catálogo, Clientes, SRM Intelligent, Academia, Auth y estándar IMBRA.
- **Estado:** NOMBRADA Y DEFINIDA; documento quirúrgico final aún pendiente de redacción/ejecución.

---

## B. Órdenes KAIQI, YOKOMAR, DARROW e imágenes

### 6. YOKOMAR_QC_ADVISORY_NO_DELETE
- **Origen:** `task_yok_img_del`.
- **Orden:** no aprobar borrado de 269 imágenes.
- **Motivo:** watermark YOKOMAR es marca propia; QC con alto falso positivo.
- **Estado:** SELLADA; 0 borrado.

### 7. KAIQI_IMAGE_LAYER_UNDER_ORIGENES_CORRECTION
- **Orden:** revertir las 6 imágenes incorrectas y re-verificar una por una con consulta directa.
- **Resultado:** 6/6 revertidas; banco real 127 intacto; 0 marca ajena.
- **Estado:** CERRADA.

### 8. KAIQI_QC_VISUAL_HUMAN_REVIEW
- **Origen:** `task_kaiqi_dominant`.
- **Orden:** revisión visual humana; no auto-borrado ni auto-apply.
- **Artefacto:** `/tmp/kaiqi_qc_81_top_dominant.html`.
- **Estado:** FRONTERA HUMANA / QC VISUAL.

### 9. KAIQI_QC_CONSISTENCY_SWEEP
- **Orden:** repasar las aceptadas y marcar archivo que nombre pieza distinta al título.
- **Regla:** coincidencia de palabras no equivale a correspondencia de pieza.
- **Resultado:** 85 ACCEPT, 5 REJECT, 10 REVIEW/PENDING.
- **Estado:** CERRADA READ-ONLY.

### 10. KAIQI_QC_CLEAN_MANIFEST_85
- **Orden:** generar JSON limpio, deduplicado a una imagen por producto.
- **Artefacto:** `kaiqi_qc_clean_apply_manifest_85.json`.
- **Resultado:** 85 listas, 5 gap honesto, 10 revisión.
- **Estado:** GENERADO READ-ONLY.

### 11. KAIQI_OWN_BANK_VERIFICATION
- **Orden:** confirmar que cada imagen aceptada proviene del banco propio/proveedor KAIQI.
- **Checks:** 0 source-store ajeno; 0 watermark ajena; provenance/evidence.
- **Estado:** PENDIENTE READ-ONLY EN SERVIDOR.

### 12. KAIQI_APPLY_85_VIA_IMAGE_WRITE_GATEWAY
- **Orden:** aplicar únicamente las 85 aceptadas después de own-bank PASS.
- **Condiciones:** firma del Arquitecto, gateway, evidencia pre/post y rollback.
- **Estado:** BLOQUEADA HASTA VERIFICACIÓN + FIRMA.

### 13. WATERMARK_FOREIGN_DETECTOR
- **Orden:** construir/activar detector específico de marca ajena antes de cross-store o borrados visuales.
- **Dueño:** PC I.
- **Estado:** EN COLA, ESPERANDO FIRMA ESPECÍFICA.

### 14. DRW_WBI_RELINK_READY
- **Orden inicial:** rescatar 65 imágenes reales desde CDN propio DARROW por SKU exacto.
- **Reglas:** no IA, no fuente ajena, Orígenes + gateway + evidence.
- **Estado posterior:** POSPUESTO.

### 15. DARROW_POSTPONED_PERPLEXITY_FRONTIER
- **Orden:** posponer DARROW; mantenerlo retomable.
- **Motivo:** prioridad baja y frontera humana de token/saldo Perplexity.
- **Estado:** `monitoring`, no killed.

---

## C. Órdenes Dispatch / Orchestrator

### 16. CANCEL_SIGNAL_REMINDERS_10043
- **Orden inicial:** cancelar `task_248ab65b` y `task_4561f81d`.
- **Resultado:** cancelados.
- **Estado:** EJECUTADA.

### 17. FIX_ORCHESTRATOR_REMINDER_LOOP_FIRST
- **Orden corregida:** arreglar causa raíz antes de cancelar nuevos signals.
- **Guard:** no regenerar si parent está diferido, ya decidido, HTML listo o nota futura.
- **Idempotencia:** `parent + tipo_signal + decision_version`.
- **Estado:** EJECUTADA.

### 18. CANCEL_SIGNAL_REMINDERS_10063_AND_10070
- **Orden:** cancelar signals nuevos sólo después del fix.
- **Resultado:** signals ciclo 10063 y residual 10070 cancelados.
- **Estado:** EJECUTADA.

### 19. PARK_DARROW_AS_MONITORING
- **Orden:** sacar DARROW de `awaiting_human` sin matarlo.
- **Estado:** EJECUTADA; retomable.

### 20. VERIFY_ORCHESTRATOR_NEXT_LIVE_CYCLE
- **Orden:** verificar un ciclo posterior al restart.
- **Criterio PASS:** 0 nuevos signals, 0 regeneración.
- **Resultado:** ciclo 10072, `tasks=0`, 32/32 tests.
- **Estado:** SELLADA; loop cerrado permanentemente.

---

## D. Órdenes Core Pipeline / Wave 1

### 21. PIPELINE_ACTIVATION_WAVE_1
- **Orden inicial:** ADN gate, Source Engine, Product Provenance y StorefrontAuditor.
- **Corrección posterior:** no construir desde cero; verificar, conectar y completar.
- **Estado:** RE-ESCOPADA.

### 22. PIPELINE_ACTIVATION_WAVE_1_AUDIT_CONNECT_COMPLETE
- **Orden definitiva:** leer Orígenes/terreno antes de escribir; cerrar sólo gaps reales.
- **Estado:** ACTIVA COMO DOCTRINA DE EJECUCIÓN.

### 23. ADN_REJECT_ROUTE_ENFORCEMENT
- **Orden:** demostrar que ADN C.4 rechaza contenido, no sólo que carga `adn.yaml`.
- **Resultado:** `violations ADN:prohibida:*`, `pass=False`, penalty.
- **Estado:** DONE / FUNCIONAL.

### 24. SOURCE_ENGINE_REPORT_TO_DISPATCH
- **Orden:** conectar los reports producidos por Source Engine al ciclo de dispatch/tasks.
- **No hacer:** no reactivar timer; ya corre cada ~6h.
- **Estado:** PENDIENTE REAL PC II.

### 25. PRODUCT_PROVENANCE_CURRENT_RUN_PERSISTENCE
- **Orden:** verificar tabla, cobertura y persistencia en runs actuales.
- **Resultado:** 21,390+ filas, esquema completo y persistiendo.
- **Estado:** DONE; sólo monitoreo.

### 26. STOREFRONT_AUDITOR_V2_BUILD
- **Orden:** construir auditor real sobre `audit_quality_v253.py`, no sobre referencia stale.
- **Resultado:** `odi_storefront_auditor_v2.py` + runner diario.
- **Estado:** BUILT.

### 27. STOREFRONT_AUDITOR_V2_SCHEDULE
- **Orden:** crear/agendar timer o scheduler para auditor v2.
- **Estado:** PENDIENTE REAL PC II.

### 28. FITMENT_ENGINE_CORE_REINTEGRATION
- **Orden:** reimplementar FITMENT como módulo Core/Pipeline, no container `:8802`.
- **Base:** `fitment_master_v1.json` y taxonomía existente.
- **Estado:** SIGUIENTE OLA / PENDIENTE.

### 29. SELF_HEALING_NOCTURNO_A6
- **Orden:** implementar/activar auditoría nocturna safe-only.
- **Base:** 13 criterios, 6 acciones.
- **Evolución reportada:** A6 sellado y actividad live.
- **Estado:** AVANZADO/SELLADO SEGÚN TERRENO; no reconstruir.

---

## E. Órdenes SRM / P10 / T10 / PAEM

### 30. SRM_DO_NOT_REBUILD_FROM_ZERO
- **Orden:** preservar SRM browser-real.
- **Rutas existentes:** Home, Catálogo, Clientes, Intelligent, Academia, Auth e IMBRA standard.
- **Estado:** REGLA SELLADA.

### 31. SRM_EVOLVE_TO_SOCIAL_INDUSTRIAL_HABITAT
- **Orden:** convertir SRM en hábitat social industrial sin perder identidad técnica.
- **Constante:** arquitectura ODI.
- **Variable:** habitante industrial.
- **Estado:** CONTENIDA EN #47.

### 32. MAP_P10_T10_TO_SRM
- **Orden:** heredar arquitectura de interacción, no textos ni estética literal.
- **P10:** confianza, gates, perfil, panel, convenio.
- **T10:** discovery, lugares, eventos, comunidades, multiactor.
- **Estado:** CONTENIDA EN #47.

### 33. REUSE_PAEM_BOOKING_CONVENIO_ANATOMY
- **Orden:** no crear booking SRM desde cero.
- **Reusar:** router gateway, tablas PG, adapters, crons, ledger y ciclo completo.
- **Adaptar:** habitante, vertical, lenguaje y caso comercial.
- **Estado:** CONTENIDA EN #47.

### 34. CONNECT_SRM_TO_CORE_PIPELINE_E2E
- **Orden:** conectar la piel SRM con Pipeline/Gateway/Orígenes y certificar punta a punta.
- **Estado:** PENDIENTE DENTRO DE LA ORDEN QUIRÚRGICA #47.

### 35. CERTIFY_SRM_IN_REAL_BROWSER
- **Orden:** evidencia browser de todas las rutas, sin claims falsos y sin romper Core.
- **Estado:** PENDIENTE DENTRO DE #47.

---

## F. Órdenes de coordinación y transferencia

### 36. PC_LANE_SEPARATION
- **PC I:** leer/verificar terreno.
- **PC II:** construir/conectar/escribir.
- **PC I V3:** FSM/orchestrator.
- **Estado:** REGLA ACTIVA.

### 37. NO_BUILD_WITHOUT_HEARTBEAT
- **Orden:** ningún build sin comprobar terreno.
- **Secuencia:** leer → verificar runtime → conectar/completar.
- **Estado:** SELLADA POR MÚLTIPLES HEARTBEATS.

### 38. ORIGENES_FIRST_BEFORE_WRITES
- **Orden:** consultar Orígenes antes de cualquier escritura.
- **Estado:** REGLA CONSTITUCIONAL ACTIVA.

### 39. NEW_CHAT_HANDOFF_READY
- **Orden:** independizar continuidad de este chat.
- **Artefacto:** `juandavidjd/extrac/ODI_HANDOFF_STATUS.md`.
- **Commit:** `7ffb5c77b1b0860491a0cbaa3edab3e7ca1fb260`.
- **Estado:** CREADO.

### 40. NEW_CHAT_READ_GITHUB_SOURCE_OF_TRUTH
- **Orden:** nuevo chat debe leer `extrac` y después `odi-vende` Issues #28, #35, #43, #45 y #47.
- **Estado:** ACTIVA PARA TRANSFERENCIA.

---

## G. Frentes registrados como backlog, no autorizados como ejecución inmediata

Estos se registraron en el mapa, pero no quedaron como orden inmediata durante el chat:

1. ImageMatcherV2 router de seis niveles.
2. CATRMU Taxonomía SQL.
3. Text-to-Image Step.
4. Imágenes 360°.
5. Video 360°.
6. Industry Bootstrapper V3.
7. Billing real adicional por vertical.
8. `POST /pipeline/ingest`.
9. Playwright 24/7 ampliado.
10. Guardian OS / CES C.4-C.5 universal.
11. POS endpoints / SAT-CP.
12. Expansión de Self-Service adapters PAEM/Matzu.

---

## Estado ejecutivo

```text
Formalizadas en issues principales: 5
Órdenes operativas y directivas explícitas: 35
Total consolidado: 40
Backlog registrado no activado: 12
```

## Fuente de continuidad

- `juandavidjd/extrac/ODI_HANDOFF_STATUS.md`
- `juandavidjd/odi-vende` Issues #28, #35, #43, #45, #47
- Este inventario debe mantenerse como índice de transferencia.

*Somos Industrias ODI.*
