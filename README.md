# Mortalidad en Colombia 2019 — App Web

# Introducción
Esta aplicación web interactiva permite explorar y visualizar la mortalidad no fetal en Colombia para el año 2019. Integra gráficos dinámicos con filtros por sexo y departamento con la intención de apoyar el analísis en patrones temporales, geográficos y demográficos.

# Objetivos

Analizar la distribución de muertes por departamento y mes.

Identificar ciudades con mayor violencia.

Visualizar causas principales de muerte y diferencias por sexo.

Explorar la distribución por ciclo de vida usando la agrupación oficial de GRUPO_EDAD1.

#Estructura del proyecto

.
├─ app.py                    # App Dash
├─ requirements.txt          # Dependencias exactas
├─ Procfile                  # Arranque en PaaS (Gunicorn)
├─ app.yaml                  # (Opcional) Google App Engine
├─ departments_centroids.json# Coordenadas aproximadas por dpto
├─ data/
│  ├─ NoFetal2019.xlsx       # Mortalidad no fetal 2019
│  ├─ CodigosDeMuerte.xlsx   # Catálogo CIE-10 (4 caracteres + descripción)
│  └─ Divipola.xlsx          # DIVIPOLA (dptos/municipios)
└─ docs/
   └─ img/                   # Capturas para el README (añádelas tú)
      ├─ fig-mapa.png
      ├─ fig-linea.png
      ├─ fig-violentas.png
      ├─ fig-minimas.png
      ├─ fig-sexo-dep.png
      └─ fig-edad.png

# Requisitos

dash==2.18.2

plotly==5.24.1

pandas==2.2.2

openpyxl==3.1.5

gunicorn==22.0.0 (para despliegue)

dash-ag-grid==31.2.0

(indirectas) Flask 3.0.3, numpy 2.3.4, etc.

Todo está en requirements.txt

# Despliegue en Render (PaaS)

Sube este proyecto a un repositorio GitHub.

En Render.com → New → Web Service → conecta tu repo.

Configura:

Environment: Python (3.11/3.12).

Build Command: pip install -r requirements.txt

Start Command: gunicorn app:server

Deploy. Render asigna la URL pública automáticamente.

# Software utilizado

Python (3.11/3.12)

Dash (framework web)

Plotly (gráficos interactivos)

Pandas (ETL/transformación de datos)

OpenPyXL (lectura Excel)

Gunicorn (servidor WSGI para PaaS)
