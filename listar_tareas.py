"""
Función Lambda: listar_tareas
"""

import json
import boto3
import uuid
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Constantes HTTP
HTTP_200_OK = 200
HTTP_400_BAD_REQUEST = 400
HTTP_404_NOT_FOUND = 404
HTTP_500_SERVER_ERROR = 500

# Estados válidos para filtrar tareas
ESTADOS_VALIDOS = ['PENDIENTE', 'EN_PROGRESO', 'COMPLETADA', 'CANCELADA']

# Configuración de logging para CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clase para manejar la serialización de tipos de datos especiales en JSON
class JSONEncoder(json.JSONEncoder):
   """
   Extiende el serializador JSON estándar para manejar tipos específicos de DynamoDB.
   En particular, convierte Decimal a float o int según corresponda.
   """
   def default(self, obj):
       if isinstance(obj, Decimal):
           return float(obj) if obj % 1 else int(obj)
       return super(JSONEncoder, self).default(obj)

# Función para validar formato UUID
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

# Inicialización de tabla DynamoDB
def obtener_tabla_tareas():
   """
   Inicializa y devuelve una referencia a la tabla tareas en DynamoDB.
   
   Returns:
       Referencia a la tabla DynamoDB para operaciones
   """
   return boto3.resource('dynamodb').Table('tareas')

# Función para obtener todas las tareas
def obtener_todas_tareas(limite: Optional[int] = None) -> List[Dict]:
   """
   Recupera todas las tareas de la tabla DynamoDB.
   
   Args:
       limite: Número máximo de resultados a devolver (opcional)
       
   Returns:
       Lista de diccionarios con los datos de las tareas
       
   Raises:
       Exception: Si ocurre un error al acceder a DynamoDB
   """
   try:
       tabla = obtener_tabla_tareas()
       if limite and limite > 0:
           respuesta = tabla.scan(Limit=limite)
       else:
           respuesta = tabla.scan()
       return respuesta.get('Items', [])
   except Exception as e:
       logger.error(f"Error al obtener tareas: {str(e)}")
       raise

# Función para obtener tareas filtradas por estado
def obtener_tareas_por_estado(estado: str, limite: Optional[int] = None) -> List[Dict]:
   """
   Filtra las tareas por su estado usando scan() con expresión de filtro.
   
   Args:
       estado: Estado de las tareas a filtrar
       limite: Número máximo de resultados a devolver (opcional)
       
   Returns:
       Lista de diccionarios con los datos de las tareas filtradas
       
   Raises:
       ValueError: Si el estado no es válido
       Exception: Si ocurre un error al acceder a DynamoDB
   """
   if estado not in ESTADOS_VALIDOS:
       raise ValueError(f"Estado no válido. Debe ser uno de: {', '.join(ESTADOS_VALIDOS)}")
   
   try:
       tabla = obtener_tabla_tareas()
       params = {
           'FilterExpression': '#estado = :estado_val',
           'ExpressionAttributeNames': {
               '#estado': 'estado'
           },
           'ExpressionAttributeValues': {
               ':estado_val': estado
           }
       }
       
       if limite and limite > 0:
           params['Limit'] = limite
           
       respuesta = tabla.scan(**params)
       return respuesta.get('Items', [])
   except Exception as e:
       logger.error(f"Error al filtrar tareas por estado: {str(e)}")
       raise

# Función para obtener una tarea específica por su ID
def obtener_tarea_por_id(id_tarea: str) -> Optional[Dict]:
   """
   Recupera una tarea específica por su ID usando get_item.
   
   Args:
       id_tarea: Identificador único de la tarea a buscar
       
   Returns:
       Diccionario con los datos de la tarea o None si no existe
       
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
       logger.error(f"Error al obtener tarea por ID: {str(e)}")
       raise

# Función principal Lambda
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
   """
   Punto de entrada principal para la función Lambda.
   Procesa los parámetros de la petición y determina la operación a realizar.
   
   Args:
       event: Objeto con la información del evento que invocó la función
       context: Objeto con información del contexto de ejecución
       
   Returns:
       Diccionario con la respuesta HTTP formateada
   """
   # Extracción de parámetros de la petición
   # Para API Gateway con parámetros de consulta en la URL
   query_params = event.get('queryStringParameters', {}) or {}
   
   # Obtener identificador de solicitud para trazabilidad
   request_id = context.aws_request_id if context else 'unknown'
   logger.info(f"[{request_id}] Evento recibido: {json.dumps(event)}")
   
   try:
       id_tarea = query_params.get('id')
       estado = query_params.get('estado')
       
       # Procesamiento del parámetro de límite
       limite = None
       if 'limite' in query_params:
           try:
               limite = int(query_params.get('limite'))
               if limite <= 0:
                   raise ValueError("El límite debe ser un número positivo")
           except ValueError:
               return {
                   'statusCode': HTTP_400_BAD_REQUEST,
                   'headers': {'Content-Type': 'application/json'},
                   'body': json.dumps({
                       'error': 'Parámetro inválido',
                       'mensaje': 'El parámetro "limite" debe ser un número entero positivo'
                   })
               }
       
       # Prioridad: 1. ID específico, 2. Filtro por estado, 3. Todas las tareas
       if id_tarea:
           # Validar formato UUID
           if not es_uuid_valido(id_tarea):
               return {
                   'statusCode': HTTP_400_BAD_REQUEST,
                   'headers': {'Content-Type': 'application/json'},
                   'body': json.dumps({
                       'error': 'Parámetro inválido',
                       'mensaje': 'El ID proporcionado no tiene formato UUID válido'
                   })
               }
               
           logger.info(f"[{request_id}] Buscando tarea con ID: {id_tarea}")
           tarea = obtener_tarea_por_id(id_tarea)
           
           if not tarea:
               return {
                   'statusCode': HTTP_404_NOT_FOUND,
                   'headers': {'Content-Type': 'application/json'},
                   'body': json.dumps({
                       'error': 'Tarea no encontrada',
                       'mensaje': f'No existe una tarea con el ID: {id_tarea}'
                   })
               }
           
           return {
               'statusCode': HTTP_200_OK,
               'headers': {'Content-Type': 'application/json'},
               'body': json.dumps({'tarea': tarea}, cls=JSONEncoder)
           }
       
       elif estado:
           try:
               logger.info(f"[{request_id}] Filtrando tareas por estado: {estado}")
               tareas = obtener_tareas_por_estado(estado, limite)
               return {
                   'statusCode': HTTP_200_OK,
                   'headers': {'Content-Type': 'application/json'},
                   'body': json.dumps({
                       'tareas': tareas,
                       'total': len(tareas)
                   }, cls=JSONEncoder)
               }
           except ValueError as ve:
               return {
                   'statusCode': HTTP_400_BAD_REQUEST,
                   'headers': {'Content-Type': 'application/json'},
                   'body': json.dumps({
                       'error': 'Parámetro inválido',
                       'mensaje': str(ve)
                   })
               }
       
       else:
           logger.info(f"[{request_id}] Listando todas las tareas" + (f" (limite: {limite})" if limite else ""))
           tareas = obtener_todas_tareas(limite)
           return {
               'statusCode': HTTP_200_OK,
               'headers': {'Content-Type': 'application/json'},
               'body': json.dumps({
                   'tareas': tareas,
                   'total': len(tareas)
               }, cls=JSONEncoder)
           }
           
   except Exception as e:
       logger.error(f"[{request_id}] Error inesperado: {str(e)}")
       return {
           'statusCode': HTTP_500_SERVER_ERROR,
           'headers': {'Content-Type': 'application/json'},
           'body': json.dumps({
               'error': 'Error interno del servidor',
               'mensaje': 'Ha ocurrido un error al procesar la solicitud'
           })
       }