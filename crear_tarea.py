"""
Función Lambda: crear_tarea
"""

import json
import boto3
import uuid
import logging
from datetime import datetime
from typing import Dict, Any

# Constantes HTTP
HTTP_201_CREATED = 201
HTTP_400_BAD_REQUEST = 400
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

def validar_datos_tarea(datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida los datos de una tarea antes de su almacenamiento.
    
    Args:
        datos: Diccionario con los datos de la tarea a validar
        
    Returns:
        Dict[str, Any]: Datos validados y procesados
        
    Raises:
        ValueError: Si los datos no son válidos
    """
    if not isinstance(datos, dict):
        raise ValueError("Los datos deben ser un objeto JSON válido")

    titulo = datos.get('titulo')
    descripcion = datos.get('descripcion')
    fecha = datos.get('fecha')
    estado = datos.get('estado', 'PENDIENTE')

    if not titulo or not isinstance(titulo, str):
        raise ValueError("El campo 'titulo' es obligatorio y debe ser una cadena")
    if len(titulo) > 100:
        raise ValueError("El campo 'titulo' no puede superar los 100 caracteres")

    if descripcion is not None:
        if not isinstance(descripcion, str):
            raise ValueError("El campo 'descripcion' debe ser una cadena")
        if len(descripcion) > 500:
            raise ValueError("El campo 'descripcion' no puede superar los 500 caracteres")

    if fecha:
        try:
            fecha_obj = datetime.fromisoformat(fecha)
        except ValueError:
            raise ValueError("El campo 'fecha' debe tener formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)")
        
        # Una vez validado el formato, comprobamos que no sea una fecha pasada
        if fecha_obj < datetime.utcnow():
            raise ValueError("La fecha no puede ser anterior al momento actual")
    else:
        fecha = ahora_iso8601()

    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"El campo 'estado' debe ser uno de: {', '.join(ESTADOS_VALIDOS)}")

    return {
        'titulo': titulo.strip(),
        'descripcion': descripcion.strip() if descripcion else "",
        'fecha': fecha,
        'estado': estado
    }

def crear_tarea_en_db(datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una nueva tarea en la tabla DynamoDB con un identificador único.
    
    Args:
        datos: Diccionario con los datos validados de la tarea
        
    Returns:
        Dict[str, Any]: Diccionario con todos los campos de la tarea creada
        
    Raises:
        Exception: Si ocurre un error al insertar en DynamoDB
    """
    id_tarea = str(uuid.uuid4())
    timestamp_actual = ahora_iso8601()

    item = {
        'id': id_tarea,
        'titulo': datos['titulo'],
        'descripcion': datos['descripcion'],
        'fecha': datos['fecha'],
        'estado': datos['estado'],
        'creado_en': timestamp_actual,
        'actualizado_en': timestamp_actual
    }

    try:
        tabla = obtener_tabla_tareas()
        tabla.put_item(Item=item)
        logger.info(f"Tarea creada correctamente (ID: {id_tarea})")
        return item
    except Exception as e:
        logger.error(f"Error al insertar en DynamoDB: {str(e)}")
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Punto de entrada principal para la función Lambda.
    Procesa la solicitud de creación de una nueva tarea.
    
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
        # Validar y procesar los datos de entrada
        body = event.get("body", "")
        if isinstance(body, str):
            try:
                datos_entrada = json.loads(body)
            except json.JSONDecodeError:
                raise ValueError("El cuerpo de la petición no es un JSON válido")
        else:
            datos_entrada = body

        datos_validados = validar_datos_tarea(datos_entrada)

        
        # Crear la tarea en la base de datos
        tarea = crear_tarea_en_db(datos_validados)

        # Respuesta exitosa con la tarea creada
        return {
            'statusCode': HTTP_201_CREATED,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({
                'mensaje': 'Tarea creada correctamente',
                'tarea': tarea,
                'timestamp': ahora_iso8601()
            })
        }
    except ValueError as ve:
        # Error de validación de datos
        logger.warning(f"[{request_id}] Error de validación: {str(ve)}")
        return {
            'statusCode': HTTP_400_BAD_REQUEST,
            'headers': { 'Content-Type': 'application/json' },
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
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({
                'error': 'Error interno del servidor',
                'mensaje': 'Ha ocurrido un error al procesar la solicitud'
            })
        }
