# Transcripciones de las conversaciones con la IA

Cada archivo es una conversación con la IA copiada **íntegra, sin editar**: el prompt tal como se
escribió y la respuesta completa. Son la fuente que citan el análisis del uso de la IA y la auditoría
de seguridad. La decisión sobre cada propuesta (adoptada, modificada o descartada, con su motivo) no
está aquí, sino en el documento que la analiza.

| Archivo | Qué se le pidió a la IA | Para qué | Dónde se analiza |
|---|---|---|---|
| [`modelo_iteracion_1_prompt_pobre_respuesta.md`](modelo_iteracion_1_prompt_pobre_respuesta.md) | El diagrama de clases y su código, con un prompt pobre, sin el caso adjunto | Ver qué propone la IA sin contexto: clases que el caso no pide, cupo como contador, precio en `float` | [`ANALISIS_IA.md`](../ANALISIS_IA.md) |
| [`modelo_iteracion_2_prompt_claro_respuesta.md`](modelo_iteracion_2_prompt_claro_respuesta.md) | El mismo diseño, con un prompt según el esquema CLARO (Contexto, Labor, Alcance, Rol y Orden) y el caso adjunto | Comparar: cuánto cambia la respuesta con un buen prompt, y qué sigue fallando | [`ANALISIS_IA.md`](../ANALISIS_IA.md) |
| [`auditoria_seguridad_ia.md`](auditoria_seguridad_ia.md) | Una auditoría de seguridad del código (commit `525ab10`), en un agente nuevo sin el contexto del proyecto | Obtener hallazgos con ubicación, impacto y categoría OWASP, para verificarlos uno por uno | [`AUDITORIA.md`](../AUDITORIA.md) |

Los prompts y las respuestas completos de todo el desarrollo, y no solo de estas tres conversaciones,
están en el registro de trabajo, que no viaja al repositorio.
