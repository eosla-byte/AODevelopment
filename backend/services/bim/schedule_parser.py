
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
                    outline_level = task.find(f"{ns}OutlineLevel")
                    
                    if name is not None and uid is not None:
                        t_data = {
                            "activity_id": uid.text,
                            "name": name.text,
                            "start": None,
                            "finish": None,
                            "pct_complete": 0,
                            "predecessors": "",
                            "contractor": "",
                            "style": {} 
                        }
                        
                         # Indentation (WBS Level)
                        if outline_level is not None:
                            try:
                                lvl = int(outline_level.text)
                                t_data["style"] = {"indent": max(0, lvl - 1)}
                            except: pass
                            
                        # Dependencies
                        preds = []
                        for link in task.findall(f"{ns}PredecessorLink"):
                            pred_uid = link.find(f"{ns}PredecessorUID")
                            if pred_uid is not None:
                                preds.append(pred_uid.text)
                        if preds:
                            t_data["predecessors"] = ",".join(preds)

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
        

        
        # 2. Resources (Simple lookup map)
        resources = {}
        res_xml = root.find(f"{ns}Resources")
        if res_xml is not None:
            for res in res_xml.findall(f"{ns}Resource"):
                r_uid = res.find(f"{ns}UID")
                r_name = res.find(f"{ns}Name")
                if r_uid is not None and r_name is not None:
                    resources[r_uid.text] = r_name.text
        
        # Assignments
        assign_xml = root.find(f"{ns}Assignments")
        if assign_xml is not None and resources:
            for asn in assign_xml.findall(f"{ns}Assignment"):
                task_uid = asn.find(f"{ns}TaskUID")
                res_uid = asn.find(f"{ns}ResourceUID")
                
                if task_uid and res_uid and res_uid.text in resources:
                    target_task = next((t for t in tasks if t["activity_id"] == task_uid.text), None)
                    if target_task:
                        r_name = resources[res_uid.text]
                        if target_task["contractor"]:
                            target_task["contractor"] += f", {r_name}"
                        else:
                            target_task["contractor"] = r_name

        import json
        for t in tasks:
            # Serialize style for storage
            if t.get("style"):
                t["style"] = json.dumps(t["style"])
            else:
                t["style"] = None
        
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
    # Raising error to prompt user for XML
    raise ValueError("El formato .MPP requiere conversión. Por favor guarde su archivo como .XML en MS Project e intente nuevamente.")
