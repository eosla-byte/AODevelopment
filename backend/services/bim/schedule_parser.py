
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
    
    if filename.endswith(".xer"):
        return parse_xer(file_content)
    elif filename.endswith(".xml"):
        return parse_xml(file_content)
    else:
        raise ValueError("Formato no soportado. Use .xer (Primavera) o .xml (MS Project)")

def parse_xer(content: bytes):
    # TODO: Implement robust XER parsing
    # XER is a tab-separated text format (CP1252 usually)
    # This is a stub.
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
