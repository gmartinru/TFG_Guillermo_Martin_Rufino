"""
Función Lambda: actualizar_tarea
"""

import json
import boto3
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
# Constantes HTTP
HTTP_200_OK = 200
HTTP_400_BAD_REQUEST = 400
HTTP_404_NOT_FOUND = 404
HTTP_500_SERVER_ERROR = 500
# Estados válidos para una tarea
ESTADOS_VALIDOS = ['PENDIENTE', 'EN_PROGRESO', 'COMPLETADA', 'CANCELADA']
# Configuración de logging para CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Funciones auxiliares
def ahora_iso8601() -> str:
   """
   Genera una cadena de fecha/hora en formato ISO 8601 (UTC) sin microsegundos.
   
   Returns:
       str: Fecha y hora actual en formato ISO 8601 con sufijo 'Z'
   """
   return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
def obtener_tabla_tareas():
   """
   Inicializa y devuelve una referencia a la tabla tareas en DynamoDB.
   
   Returns:
       Referencia a la tabla DynamoDB para operaciones
   """
   return boto3.resource('dynamodb').Table('tareas')
def es_uuid_valido(valor: str) -> bool:
   """
   Verifica si una cadena tiene un formato UUID válido.
   
   Args:
       valor: La cadena a validar
       
   Returns:
       True si el formato es válido, False en caso contrario
   """
   try:
       uuid.UUID(valor)
       return True
   except ValueError:
       return False
def obtener_tarea_existente(id_tarea: str) -> Optional[Dict[str, Any]]:
   """
   Recupera una tarea existente por su ID para verificar su existencia.
   
   Args:
       id_tarea: Identificador único de la tarea
       
   Returns:
       Diccionario con los datos de la tarea existente o None si no existe
       
   Raises:
       Exception: Si ocurre un error al acceder a DynamoDB
   """
   try:
       tabla = obtener_tabla_tareas()
       respuesta = tabla.get_item(
           Key={
               'id': id_tarea
           }
       )
       return respuesta.get('Item')
   except Exception as e:
       logger.error(f"Error al obtener tarea existente: {str(e)}")
       raise
def validar_datos_actualizacion(datos: Dict[str, Any]) -> Dict[str, Any]:
   """
   Valida los datos de actualización de una tarea.
   Solo valida los campos proporcionados, sin requerir todos los campos.
   
   Args:
       datos: Diccionario con los datos a actualizar
       
   Returns:
       Dict[str, Any]: Datos validados y procesados
       
   Raises:
       ValueError: Si los datos no son válidos
   """
   if not isinstance(datos, dict):
       raise ValueError("Los datos deben ser un objeto JSON válido")
   
   # Verificar que se proporcione al menos un campo a actualizar
   campos_permitidos = {'titulo', 'descripcion', 'fecha', 'estado'}
   campos_proporcionados = set(datos.keys())
   campos_validos = campos_proporcionados.intersection(campos_permitidos)
   
   if not campos_validos:
       raise ValueError("Debe proporcionar al menos un campo válido para actualizar")
   
   datos_validados = {}
   
   # Validar título si está presente
   if 'titulo' in datos:
       titulo = datos.get('titulo')
       if not titulo or not isinstance(titulo, str):
           raise ValueError("El campo 'titulo' debe ser una cadena no vacía")
       if len(titulo) > 100:
           raise ValueError("El campo 'titulo' no puede superar los 100 caracteres")
       datos_validados['titulo'] = titulo.strip()
   
   # Validar descripción si está presente
   if 'descripcion' in datos:
       descripcion = datos.get('descripcion')
       if descripcion is not None:
           if not isinstance(descripcion, str):
               raise ValueError("El campo 'descripcion' debe ser una cadena")
           if len(descripcion) > 500:
               raise ValueError("El campo 'descripcion' no puede superar los 500 caracteres")
           datos_validados['descripcion'] = descripcion.strip()
       else:
           datos_validados['descripcion'] = ""
   
   # Validar fecha si está presente
   if 'fecha' in datos:
       fecha = datos.get('fecha')
       if fecha:
           try:
               fecha_obj = datetime.fromisoformat(fecha)
           except ValueError:
               raise ValueError("El campo 'fecha' debe tener formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)")
           
           # La fecha de actualización puede ser pasada o futura (diferente a crear_tarea)
           datos_validados['fecha'] = fecha
       else:
           datos_validados['fecha'] = ahora_iso8601()
   
   # Validar estado si está presente
   if 'estado' in datos:
       estado = datos.get('estado')
       if estado not in ESTADOS_VALIDOS:
           raise ValueError(f"El campo 'estado' debe ser uno de: {', '.join(ESTADOS_VALIDOS)}")
       datos_validados['estado'] = estado
   
   return datos_validados
def actualizar_tarea_en_db(id_tarea: str, datos_actualizados: Dict[str, Any]) -> Dict[str, Any]:
   """
   Actualiza una tarea existente en DynamoDB.
   
   Args:
       id_tarea: Identificador único de la tarea
       datos_actualizados: Diccionario con los campos validados a actualizar
       
   Returns:
       Dict[str, Any]: Diccionario con todos los campos de la tarea actualizada
       
   Raises:
       Exception: Si ocurre un error al actualizar en DynamoDB
   """
   try:
       tabla = obtener_tabla_tareas()
       
       # Construir la expresión de actualización dinámicamente
       update_expression = "SET actualizado_en = :actualizado_en"
       expression_attribute_values = {
           ':actualizado_en': ahora_iso8601()
       }
       
       # Añadir cada campo a actualizar a la expresión
       for campo, valor in datos_actualizados.items():
           update_expression += f", {campo} = :{campo}"
           expression_attribute_values[f':{campo}'] = valor
       
       # Realizar la actualización
       respuesta = tabla.update_item(
           Key={'id': id_tarea},
           UpdateExpression=update_expression,
           ExpressionAttributeValues=expression_attribute_values,
           ReturnValues='ALL_NEW'
       )
       
       logger.info(f"Tarea actualizada correctamente (ID: {id_tarea})")
       return respuesta.get('Attributes', {})
       
   except Exception as e:
       logger.error(f"Error al actualizar en DynamoDB: {str(e)}")
       raise
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
   """
   Punto de entrada principal para la función Lambda.
   Procesa la solicitud de actualización de una tarea existente.
   
   Args:
       event: Objeto con la información del evento que invocó la función
       context: Objeto con información del contexto de ejecución
       
   Returns:
       Dict[str, Any]: Diccionario con la respuesta HTTP formateada
   """
   # Obtener identificador de solicitud para trazabilidad
   request_id = context.aws_request_id if context else str(uuid.uuid4())
   logger.info(f"[{request_id}] Evento recibido: {json.dumps(event)}")
   
   try:
       # Extraer el ID de la tarea de los parámetros de ruta
       path_params = event.get('pathParameters', {}) or {}
       id_tarea = path_params.get('id')
       
       # Validar que se haya proporcionado un ID
       if not id_tarea:
           return {
               'statusCode': HTTP_400_BAD_REQUEST,
               'headers': {'Content-Type': 'application/json'},
               'body': json.dumps({
                   'error': 'Parámetro faltante',
                   'mensaje': 'El ID de la tarea es obligatorio'
               })
           }
       
       # Validar formato UUID del ID
       if not es_uuid_valido(id_tarea):
           return {
               'statusCode': HTTP_400_BAD_REQUEST,
               'headers': {'Content-Type': 'application/json'},
               'body': json.dumps({
                   'error': 'Parámetro inválido',
                   'mensaje': 'El ID proporcionado no tiene formato UUID válido'
               })
           }
       
       # Verificar que la tarea existe
       tarea_existente = obtener_tarea_existente(id_tarea)
       if not tarea_existente:
           return {
               'statusCode': HTTP_404_NOT_FOUND,
               'headers': {'Content-Type': 'application/json'},
               'body': json.dumps({
                   'error': 'Tarea no encontrada',
                   'mensaje': f'No existe una tarea con el ID: {id_tarea}'
               })
           }
       
       # Obtener el cuerpo de la petición
       body = event.get("body", "")
       if isinstance(body, str):
           try:
               datos_entrada = json.loads(body)
           except json.JSONDecodeError:
               return {
                   'statusCode': HTTP_400_BAD_REQUEST,
                   'headers': {'Content-Type': 'application/json'},
                   'body': json.dumps({
                       'error': 'Formato inválido',
                       'mensaje': 'El cuerpo de la petición debe ser JSON válido'
                   })
               }
       else:
           datos_entrada = body
       
       # Validar los datos de actualización
       datos_validados = validar_datos_actualizacion(datos_entrada)

       
       # Actualizar la tarea en la base de datos
       tarea_actualizada = actualizar_tarea_en_db(id_tarea, datos_validados)
       
       # Respuesta exitosa con la tarea actualizada
       return {
           'statusCode': HTTP_200_OK,
           'headers': {'Content-Type': 'application/json'},
           'body': json.dumps({
               'mensaje': 'Tarea actualizada correctamente',
               'tarea': tarea_actualizada,
               'timestamp': ahora_iso8601()
           })
       }
       
   except ValueError as ve:
       # Error de validación de datos
       logger.warning(f"[{request_id}] Error de validación: {str(ve)}")
       return {
           'statusCode': HTTP_400_BAD_REQUEST,
           'headers': {'Content-Type': 'application/json'},
           'body': json.dumps({
               'error': 'Datos inválidos',
               'mensaje': str(ve)
           })
       }
   except Exception as e:
       # Error interno del servidor
       logger.error(f"[{request_id}] Error inesperado: {str(e)}")
       return {
           'statusCode': HTTP_500_SERVER_ERROR,
           'headers': {'Content-Type': 'application/json'},
           'body': json.dumps({
               'error': 'Error interno del servidor',
               'mensaje': 'Ha ocurrido un error al procesar la solicitud'
           })
       }