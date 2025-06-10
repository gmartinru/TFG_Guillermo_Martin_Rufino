# Sistema de gestión de tareas personales en AWS utilizando arquitectura *serverless*

Este repositorio contiene el código fuente del Trabajo de Fin de Grado titulado “Diseño e implementación de un sistema *serverless* en AWS para la gestión de tareas personales”, desarrollado por Guillermo Martín Rufino en la Universidad Pontificia de Salamanca, Facultad de Informática, durante el curso académico 2024–2025.

## Descripción general del proyecto

El objetivo del sistema es ofrecer una solución backend para la gestión de tareas personales mediante una interfaz de tipo API RESTful. El sistema ha sido diseñado sobre una arquitectura completamente *serverless* utilizando los servicios gestionados de Amazon Web Services (AWS). De este modo, se prioriza la escalabilidad automática, la ausencia de servidores dedicados y el modelo de pago por uso, minimizando así la necesidad de mantenimiento manual y mejorando la eficiencia operativa.

## Tecnologías empleadas

El sistema se apoya en los siguientes servicios de AWS:

- AWS Lambda: ejecución de funciones individuales sin necesidad de servidores
- Amazon DynamoDB: almacenamiento NoSQL de las tareas personales
- Amazon API Gateway: exposición de la API REST para integración externa
- AWS Step Functions: orquestación y validación automatizada del flujo CRUD
- AWS CloudWatch Logs: monitorización y análisis de registros
- AWS Identity and Access Management (IAM): gestión de roles y permisos

## Estructura del repositorio

Este repositorio incluye los siguientes archivos principales, correspondientes a las funciones Lambda que implementan el sistema CRUD:

- crear_tarea.py # Inserción de nuevas tareas (operación POST)
- listar_tareas.py # Recuperación y filtrado de tareas (operación GET)
- actualizar_tarea.py # Modificación de tareas existentes (operación PUT)
- eliminar_tarea.py # Eliminación de tareas por identificador (operación DELETE)

## Instrucciones de despliegue

Para ejecutar correctamente el sistema en AWS, deben seguirse los siguientes pasos:

1. Crear una tabla llamada *tareas* en Amazon DynamoDB, con el campo `id` como clave de partición.
2. Implementar cada una de las funciones Lambda utilizando los archivos proporcionados.
3. Configurar una API REST en Amazon API Gateway con los siguientes endpoints:
   - POST `/tareas` → función `crear_tarea`
   - GET `/tareas` → función `listar_tareas`
   - PUT `/tareas/{id}` → función `actualizar_tarea`
   - DELETE `/tareas/{id}` → función `eliminar_tarea`
4. (Opcional) Implementar una máquina de estados en AWS Step Functions para validar de forma encadenada la operativa CRUD.
5. Activar el registro de eventos y errores mediante AWS CloudWatch Logs.

## Autoría

Guillermo Martín Rufino  
Universidad Pontificia de Salamanca  
Ingeniería Informática 
Curso académico 2024–2025
