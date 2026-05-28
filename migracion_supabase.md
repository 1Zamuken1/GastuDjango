# Guía de Migración de Base de Datos: Supabase (Sao Paulo -> N. Virginia)

Esta guía detalla los pasos para migrar la base de datos de producción a una región más cercana al servidor de Render (Virginia) con el fin de reducir la latencia de red, sin perder tablas ni datos.

## 1. Crear el nuevo proyecto en Supabase
1. Ve a tu panel de Supabase y crea un **New Project**.
2. En **Region**, selecciona **US East (N. Virginia)**.
3. Configura una contraseña segura para la base de datos y guárdala.

## 2. Migrar Esquema y Datos

Existen dos alternativas principales para mover los datos:

### Opción A: Usando consola (pg_dump y psql)
Requisito: Tener PostgreSQL instalado localmente.

**Paso 1: Exportar la base de datos actual (Sao Paulo)**
Abre tu terminal y ejecuta el siguiente comando reemplazando con la URL de conexión antigua:
```bash
pg_dump --clean --if-exists --quote-all-identifiers --no-owner --no-privileges -d "TU_DATABASE_URL_ANTIGUA_AQUI" > gastuapp_backup.sql
```
*(Usa la URL con puerto `6543` o `5432` de tu proyecto antiguo)*.

**Paso 2: Importar a la nueva base de datos (Virginia)**
```bash
psql -d "TU_DATABASE_URL_NUEVA_AQUI" -f gastuapp_backup.sql
```

### Opción B: Interfaz Gráfica (DBeaver o pgAdmin)
1. Descarga e instala [DBeaver](https://dbeaver.io/).
2. Conecta ambas bases de datos (la antigua y la nueva) utilizando sus respectivas URL.
3. Haz clic derecho en la base de datos de **Sao Paulo** -> *Tools* -> *Backup* y guarda el archivo.
4. Haz clic derecho en la base de datos de **Virginia** -> *Tools* -> *Restore* y carga el archivo generado.

## 3. Actualizar la conexión en Render
Una vez que hayas comprobado que las tablas y los datos están en el nuevo proyecto:
1. Ve al panel de control de tu aplicación en **Render**.
2. Entra a la pestaña **Environment**.
3. Cambia el valor de tu variable **`DATABASE_URL`** y ponle la cadena de conexión de tu **nuevo** proyecto de Supabase (el de Virginia). 
   * Recuerda usar el puerto `6543` (Transaction pooler) tal como lo tenías antes.
4. Guarda los cambios. Esto automáticamente reiniciará el servidor de Render apuntando a la nueva base de datos en Virginia.

## 4. Pruebas y Apagado
1. Entra a tu app web y verifica que el login, los movimientos y los datos carguen correctamente.
2. Deberías notar una mejora significativa en los tiempos de carga (latencia).
3. Una vez confirmes que todo está perfecto, ve a tu antiguo proyecto de Supabase (Sao Paulo) y ponlo en pausa o elimínalo para liberar cupos de tu plan gratuito.
