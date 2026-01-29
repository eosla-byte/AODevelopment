
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
    import xml.etree.ElementTree as ET
    from datetime import datetime
    
    try:
        root = ET.fromstring(content)
        
        # MSP XML usually has a namespace. Let's handle it or strip it.
        # Simple strategy: iterate all elements and check tag name ending.
        
        ns = ""
        if '}' in root.tag:
            ns = root.tag.split('}')[0] + '}'
            
        tasks = []
        
        # Find Tasks
        tasks_xml = root.find(f"{ns}Tasks")
        if tasks_xml is not None:
            for task in tasks_xml.findall(f"{ns}Task"):
                try:
                    # Skip summary tasks or project summary if desired?
                    # For now keep all.
                    
                    uid = task.find(f"{ns}UID")
                    name = task.find(f"{ns}Name")
                    start = task.find(f"{ns}Start")
                    finish = task.find(f"{ns}Finish")
                    percent = task.find(f"{ns}PercentComplete")
                    
                    if name is not None and uid is not None:
                        t_data = {
                            "activity_id": uid.text,
                            "name": name.text,
                            "start": None,
                            "finish": None,
                            "pct_complete": 0
                        }
                        
                        if start is not None and start.text:
                            # MSP date format: 2024-01-29T08:00:00
                            t_data["start"] = start.text # Keep string or parse? Main expects datetime for SQL?
                            # Let's keep strict text for now, main can convert if needed, or convert here.
                            # SQL Alchemy DateTime expects python datetime.
                            try:
                                t_data["start"] = datetime.fromisoformat(start.text)
                            except: pass
                            
                        if finish is not None and finish.text:
                             try:
                                t_data["finish"] = datetime.fromisoformat(finish.text)
                             except: pass

                        if percent is not None and percent.text:
                            try:
                                t_data["pct_complete"] = float(percent.text)
                            except: pass
                            
                        tasks.append(t_data)
                except Exception as e:
                    print(f"Error parsing task: {e}")
                    continue
        
                        tasks.append(t_data)
                except Exception as e:
                    print(f"Error parsing task: {e}")
                    continue
        
        # 2. Extract Assignments / Resources if needed for "Contractor"
        # For now, we will add default fields to tasks
        for t in tasks:
            t['contractor'] = "AO" # Default or extract from XML if avail
            t['predecessors'] = "" 
            # TODO: Extract <PredecessorLink> if available in Task element
        
        return {
            "project_name": "Imported Project",
            "activities": tasks
        }
    except Exception as e:
        print(f"XML Parsing Error: {e}")
        raise ValueError("Invalid XML File")

def parse_mpp(content: bytes):
    """
    Stub for MS Project Binary format (.mpp).
    """
    return {
        "project_name": "MS Project File (.mpp) - Parsing Not Supported",
        "activities": [] # Empty for now
    }
