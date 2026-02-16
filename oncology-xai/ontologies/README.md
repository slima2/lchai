# Ontologías OWL para el grafo de conocimiento

Coloca aquí los archivos OWL para que el **graph-service** construya el grafo desde ontologías reales (en lugar del mock):

- **ncit.owl** — NCI Thesaurus (genes, patrones histológicos, diagnósticos)
- **mondo.owl** — Mondo Disease Ontology (opcional, para diagnósticos)

## Dónde descargarlos

- **NCIt:** https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/ (requiere registro EVS) o versión pública en formato OWL si está disponible.
- **MONDO:** https://github.com/monarch-initiative/mondo/releases — descargar `mondo.owl` del último release.

Tras colocar los archivos en esta carpeta, reinicia el graph-service y usa **"Rebuild Graph"** en la pestaña Graph de la UI.
