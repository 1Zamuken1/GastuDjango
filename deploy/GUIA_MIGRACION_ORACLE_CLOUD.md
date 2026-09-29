# Guía de Migración y Despliegue en Oracle Cloud (OCI Always Free)

Esta guía explica paso a paso cómo desplegar **GastuApp** en una máquina virtual de Oracle Cloud Always Free con **costo $0**.

---

## 1. Crear la Instancia en Oracle Cloud

1. Entra a la consola de [Oracle Cloud](https://cloud.oracle.com/).
2. Ve a **Compute > Instances > Create Instance**.
3. **Imagen:** Elige **Ubuntu 24.04 LTS** (o 22.04 LTS).
4. **Shape (Hardware):**
   - **Opción A (Recomendada):** `Ampere (ARM)` — Selecciona 2 a 4 OCPUs y 12 a 24 GB de RAM (100% Gratis dentro de la cuota Always Free de 3000 OCPU hours / 18000 GB hours al mes).
   - **Opción B:** `VM.Standard.E2.1.Micro (AMD)` — 1 OCPU y 1 GB de RAM.
5. **Red (VCN):** Asigna una IP pública IPv4.
6. **Claves SSH:** Descarga la clave privada `.key` para conectarte desde tu terminal.

---

## 2. Abrir los Puertos de Red (Doble Firewall)

### A. Firewall de Oracle Cloud (Security Lists)
1. En la consola de OCI, ve a **Networking > Virtual Cloud Networks > [Tu VCN] > Security Lists > Default Security List**.
2. Haz clic en **Add Ingress Rules**:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `80,443`
   - Guarda los cambios.

### B. Firewall del Sistema Operativo en la VM
Conéctate por SSH a tu instancia:
```bash
ssh -i tu_clave.key ubuntu@TU_IP_PUBLICA
```

Ejecuta en la terminal de la VM:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save || sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

---

## 3. Despliegue con Docker (Método Recomendado)

### A. Instalar Docker y Docker Compose
En la máquina virtual ejecuta:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### B. Clonar el Repositorio y Configurar `.env`
```bash
git clone https://github.com/1Zamuken1/GastuDjango.git
cd GastuDjango
cp .env.example .env
nano .env
```

Edita las siguientes variables en `.env`:
```env
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,TU_IP_PUBLICA,tudominio.com
CSRF_TRUSTED_ORIGINS=http://TU_IP_PUBLICA,https://tudominio.com

# Base de datos (con Docker Compose se conecta al contenedor db)
USE_SQLITE=False
DATABASE_URL=postgresql://gastu_user:gastu_password123@db:5432/gastu_db

# Redis local en Docker
REDIS_URL=redis://redis:6379/0

# API Keys y Correos
GROQ_API_KEY=gsk_...
EMAIL_HOST_USER=soporte.gastuapp@gmail.com
EMAIL_HOST_PASSWORD=...
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
```

### C. Iniciar los Contenedores
```bash
docker compose up -d --build
```

Esto levantará automáticamente:
- **PostgreSQL 16**
- **Redis**
- **Daphne (Django + WebSockets + Migraciones automáticas + Collectstatic)**
- **Nginx (Reverse proxy en puertos 80 y 443)**

Para verificar que todo esté corriendo:
```bash
docker compose ps
docker compose logs -f web
```

---

## 4. (Opcional) Configurar Dominio y SSL Gratis (HTTPS) con Certbot

Si asocias un dominio (ej. `app.midominio.com` o uno gratuito de DuckDNS):

1. Instala Certbot en la VM:
   ```bash
   sudo apt install -y certbot
   ```
2. Detén temporalmente Nginx o genera el certificado:
   ```bash
   sudo certbot certonly --standalone -d tudominio.com
   ```
3. O monta los certificados en el contenedor de Nginx.

---

## 5. Comandos Útiles

- **Ver logs en vivo:** `docker compose logs -f web`
- **Reiniciar servicios:** `docker compose restart`
- **Actualizar cambios de código:**
  ```bash
  git pull origin main
  docker compose up -d --build web
  ```
- **Hacer backup de la base de datos:**
  ```bash
  docker compose exec db pg_dump -U gastu_user gastu_db > backup_$(date +%Y%m%d).sql
  ```
