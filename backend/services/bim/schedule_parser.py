
import io
import datetime

def parse_schedule(file_content: bytes, filename: str) -> dict:
    """
    Parses a schedule file (.xer or .xml) and returns a standardized dict structure:
    {
        "project_name": "...",
        "activities": [
            {
                "activity_id": "A100", 
                "name": "Task 1", 
                "start": datetime, 
                "finish": datetime,
                "wbs": "WBS.1" 
            },
            ...
        ]
    }
    """
    filename = filename.lower()
    
    if filename.endswith(".xml"):
        return parse_xml(file_content)
    elif filename.endswith(".mpp"):
        return parse_mpp(file_content)
    else:
        raise ValueError("Formato no soportado. Use .xer, .xml o .mpp")

def parse_xer(content: bytes):
    # TODO: Implement robust XER parsing
    return {
        "project_name": "Imported from Primavera",
        "activities": []
    }

def parse_xml(content: bytes):
    # TODO: Implement MSP XML parsing
    return {
        "project_name": "Imported from MS Project",
        "activities": []
    }

def parse_mpp(content: bytes):
    """
    Stub for MS Project Binary format (.mpp).
    Real parsing requires heavy libs (like mpxj or Aspose).
    For now, we accept the file to store it, but return 0 activities.
    """
    return {
        "project_name": "MS Project File (.mpp)",
        "activities": []
    }
