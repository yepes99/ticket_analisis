# 📊 Proyecto Python - Procesamiento de Tickets

Este proyecto procesa y analiza tickets a partir de un archivo CSV, aplicando limpieza de datos, normalización de clientes, cálculo de SLAs y generación de métricas analíticas.

---

## 🚀 Características

- Limpieza y transformación de datos de tickets
- Normalización de clientes (dominios y URLs)
- Cálculo de tiempos de resolución
- Evaluación de SLA por prioridad y tamaño
- Clasificación automática de categorías
- Preparado para uso en Streamlit o análisis posterior

---

## 📁 Estructura del proyecto
mi-proyecto/
│
├── app.py # Interfaz (Streamlit u otro)
├── process.py # Lógica de procesamiento
├── data.csv # Dataset de entrada
├── requirements.txt # Dependencias
├── .gitignore
└── README.md


---

## ⚙️ Instalación

### 1. Clonar el repositorio


git clone https://github.com/TU_USUARIO/TU_REPO.git
cd TU_REPO

🐍 Crear entorno virtual

🔹 En Windows

python -m venv venv
venv\Scripts\activate

🔹 En Linux / macOS

python3 -m venv venv
source venv/bin/activate

📦 Instalar dependencias
pip install -r requirements.txt

📦 Instalar dependencias
pip install -r requirements.txt

▶️ Ejecutar el proyecto
Si es un script Python:
python app.py

Si usas Streamlit:
streamlit run app.py

🧠 Generar requirements.txt (si lo necesitas)
pip freeze > requirements.txt


🐧 Consideraciones para Linux

Si usas Linux y tienes errores con python:

sudo apt update
sudo apt install python3 python3-venv python3-pip

Crear entorno:

python3 -m venv venv
source venv/bin/activate