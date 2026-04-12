# Email para Director CISOL — Evaluación LCHAI v2.0

**Para:** Director del Centro de Investigación CISOL, SOLCA Ecuador
**De:** Servio Fernando Lima Reina
**Asunto:** Solicitud de evaluación experta del sistema LCHAI v2.0 — Análisis histológico de cáncer de pulmón con IA

---

Estimado/a Director/a del CISOL,

Le saludo cordialmente. Mi nombre es Servio Fernando Lima Reina, candidato doctoral en Ciencias de la Computación en la Universidad de Fribourg, Suiza, bajo la dirección del Prof. [nombre del director]. Me dirijo a usted para solicitar la colaboración de SOLCA en la evaluación experta de la herramienta **LCHAI v2.0** (*Lung Cancer Histologic Analysis with AI*), desarrollada como parte de mi investigación doctoral.

## Descripción del sistema

LCHAI v2.0 es un sistema de apoyo a la decisión clínica basado en inteligencia artificial que analiza imágenes histopatológicas de **adenocarcinoma de pulmón de células no pequeñas (NSCLC/LUAD)** para:

1. **Clasificar patrones histológicos de crecimiento** según la clasificación WHO 2021:
   - Lepidic, acinar, papillary, micropapillary, solid y cribriform

2. **Predecir mutaciones oncogénicas** a partir de la morfología del tejido:
   - TP53, EGFR, KRAS, STK11, KEAP1 y RBM10

3. **Proporcionar explicaciones multi-nivel** de cada predicción:
   - Mapas de atención espacial
   - Overlay de patrones sobre la imagen H&E
   - Descomposición SHAP (contribución de features visuales vs. patrones)
   - Valores Shapley de Choquet (interacciones entre patrones)
   - Comparación de ablación entre modelos
   - Etiquetas lingüísticas difusas para clasificar la intensidad de cada resultado

4. **Generar explicaciones en lenguaje natural** con referencias bibliográficas de PubMed, ancladas en un grafo de conocimiento biomédico (NCIt, MONDO, OncoKB)

El sistema está disponible en línea en:

> **https://lchai.gptfy.biz**

Se proporcionarán credenciales de acceso individuales para cada evaluador.

## Solicitud

Solicito que se designe un grupo de **6 a 10 expertos** de los siguientes perfiles para evaluar el sistema:

| Perfil | Cantidad sugerida | Rol en la evaluación |
|---|---|---|
| **Histopatólogos** | 2-3 | Evaluar la clasificación de patrones, overlays visuales, y herramienta de corrección |
| **Biólogos moleculares** | 2-3 | Evaluar la descomposición SHAP, valores Shapley de Choquet, y plausibilidad biológica |
| **Oncólogos** | 2-4 | Evaluar la utilidad clínica, el grafo de conocimiento, y las asociaciones gen-tratamiento |

## Procedimiento

Cada evaluador recibirá:
1. **Credenciales de acceso** al sistema (usuario y contraseña)
2. **Manual de uso** (adjunto) con instrucciones paso a paso
3. **Cuestionario de evaluación** (adjunto) con preguntas tipo Likert (escala 1-5) organizadas por perfil profesional

Se solicita que cada evaluador:
- Revise al menos **2 casos pre-cargados** en el sistema (slides TCGA-LUAD ya procesados)
- Opcionalmente, **suba imágenes propias** de adenocarcinoma de pulmón (formatos SVS, TIFF, BIF, PNG, JPEG) para que sean procesadas por el pipeline de IA
- Complete el cuestionario de evaluación (~20-30 minutos)

**Plazo sugerido:** 1 mes a partir de la activación de las credenciales.

## Aspectos éticos y de seguridad

- LCHAI v2.0 es una **herramienta de investigación**, NO un dispositivo de diagnóstico clínico
- Todas las predicciones incluyen disclaimers visibles indicando que requieren confirmación molecular
- Las imágenes subidas se almacenan de forma segura en servidores AWS (cifrado en reposo y en tránsito)
- Los resultados del cuestionario serán reportados de forma **anónima y agregada**
- La participación es **voluntaria**
- El protocolo cuenta con la aprobación del Comité de Investigación SOLCA-CISOL

## Archivos adjuntos

1. **LCHAI_v2_User_Manual.pdf** — Manual de uso completo con capturas de pantalla
2. **LCHAI_Explainability_Questionnaire_SOLCA.pdf** — Cuestionario de evaluación (escala Likert)

## Contacto

Quedo a su disposición para coordinar una sesión de demostración en vivo del sistema, crear las credenciales de acceso, y resolver cualquier consulta.

Atentamente,

**Servio Fernando Lima Reina**
Candidato Doctoral en Ciencias de la Computación
Universidad de Fribourg, Suiza
Email: [tu email]
Teléfono: [tu teléfono]
