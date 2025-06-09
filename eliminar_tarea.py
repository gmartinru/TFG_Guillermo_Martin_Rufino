"""
Función Lambda: eliminar_tarea
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

def eliminar_tarea_en_db(id_tarea: str) -> None:
    """
    Elimina una tarea existente de DynamoDB por su ID.
    
    Args:
        id_tarea: Identificador único de la tarea a eliminar
        
    Raises:
        Exception: Si ocurre un error al eliminar en DynamoDB
    """
    try:
        tabla = obtener_tabla_tareas()
        tabla.delete_item(
            Key={
                'id': id_tarea
            }
        )
        logger.info(f"Tarea eliminada correctamente (ID: {id_tarea})")
    except Exception as e:
        logger.error(f"Error al eliminar en DynamoDB: {str(e)}")
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Punto de entrada principal para la función Lambda.
    Procesa la solicitud de eliminación de una tarea existente.
    
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
        
        # Eliminar la tarea de la base de datos
        eliminar_tarea_en_db(id_tarea)
        
        # Respuesta exitosa
        return {
            'statusCode': HTTP_200_OK,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'mensaje': 'Tarea eliminada correctamente',
                'id': id_tarea,
                'timestamp': ahora_iso8601()
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