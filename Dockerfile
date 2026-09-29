# Dockerfile para GastuApp (Producción)
FROM python:3.12-slim

# Evitar escritura de bytecode y buffer en stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema requeridas para compilación y utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . /app/

# Crear carpeta para archivos estáticos
RUN mkdir -p /app/staticfiles /app/media

# Exponer el puerto del servidor ASGI (Daphne)
EXPOSE 8000

# Script de entrada o comando por defecto
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "gastu_django.asgi:application"]
