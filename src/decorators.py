"""
Decorators - Decoradores para facilitar el uso de LabVIEW objects
"""
from typing import Optional
from functools import wraps


def lvclass(library: str = "", class_name: Optional[str] = None, 
            version: tuple = (1, 0, 0, 0)):
    """
    Decorador para convertir una clase Python en un LabVIEW Object.
    
    Args:
        library: Nombre de la librería LabVIEW (sin extensión .lvlib)
        class_name: Nombre de la clase (si None, usa el nombre de la clase Python)
        version: Versión de la clase como tupla (W, X, Y, Z)
    
    Examples:
        >>> @lvclass(library="Commander", class_name="echo general Msg")
        >>> class EchoMsg:
        >>>     message: str = ""
        >>>     status: int = 0
        >>> 
        >>> msg = EchoMsg()
        >>> msg.message = "Hello, LabVIEW!"
        >>> serialized = lvflatten(msg)  # Automático
    """
    def decorator(cls):
        # Guardar metadatos en la clase
        cls.__lv_library__ = library
        cls.__lv_class_name__ = class_name or cls.__name__
        cls.__lv_version__ = version
        
        # Marcar como LabVIEW class
        cls.__is_lv_class__ = True
        
        return cls
    
    return decorator
