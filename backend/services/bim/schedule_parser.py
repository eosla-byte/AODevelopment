
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

def parse_mpp(content: bytes) -> dict:
    """
    Parses .mpp file using MPXJ (via JPype).
    Requires 'jdk' in system and 'jpype1', 'mpxj' python packages.
    """
    import jpype
    import mpxj # This automatically adds mpxj jars to jpype classpath on import
    import tempfile
    import os
    
    # 1. Ensure JVM is started
    if not jpype.isJVMStarted():
        try:
            # Explicitly pass classpath from jpype.getClassPath() which mpxj populated
            # This is robust against environments where default startJVM() ignores accumulated paths
            jpype.startJVM(classpath=jpype.getClassPath())
        except Exception as e:
            print(f"JVM Start Error: {e}")
            pass

    # 2. Import Java Classes via JPype
    try:
        from org.mpxj.reader import UniversalProjectReader
        # from java.io import File # Not strictly needed with MPXJ string path support?
    except ImportError:
         print("Failed to import org.mpxj packages. Check JPype/MPXJ version.")
         # Fallback or error?
         # If using ancient mpxj, it might be net.sf.mpxj
         try:
             from net.sf.mpxj.reader import UniversalProjectReader
         except:
             raise ImportError("Could not find UniversalProjectReader in org.mpxj or net.sf.mpxj")

    
    # 3. Write bytes to temp file (MPXJ handles files best)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mpp") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # 4. Read Project
        reader = UniversalProjectReader()
        project = reader.read(tmp_path)
        
        # 5. Extract Tasks
        tasks = []
        # getTasks() returns a java.util.List<Task>
        # Iterate over java list
        for task in project.getTasks():
            # Skip root/null tasks if any (often ID 0 is Project Summary)
            if not task: continue
            
            # Extract basics
            
            t_id = task.getUniqueID() # Integer
            t_name = task.getName()
            t_start = task.getStart()
            t_finish = task.getFinish()
            t_pct = task.getPercentageComplete() 
            t_outline = task.getOutlineLevel() # Integer
            
            # Skip tasks without ID?
            if not t_id: continue 
            
            # --- Field Conversion ---
            # ID
            act_id = str(t_id)
            
            # Name
            name = str(t_name) if t_name else "Unnamed Task"
            
            # Dates
            start_val = None
            if t_start:
                 # MPXJ Date .toString() -> "Fri Jan 26 ..."
                 # Try using start.toInstant() if available (Java 8+)
                 try:
                     start_val = t_start.toInstant().toString() # "2024-01-26T14:00:00Z"
                     start_val = datetime.datetime.fromisoformat(str(start_val).replace('Z', '+00:00'))
                 except: 
                     # Fallback to simple str
                     pass

            finish_val = None
            if t_finish:
                 try:
                     finish_val = t_finish.toInstant().toString()
                     finish_val = datetime.datetime.fromisoformat(str(finish_val).replace('Z', '+00:00'))
                 except: pass

            # Percent
            pct_val = 0.0
            if t_pct:
                 pct_val = float(str(t_pct)) 
            
            # Outline / Indent
            indent_level = 0
            if t_outline:
                indent_level = int(str(t_outline)) - 1
                if indent_level < 0: indent_level = 0
            
            # Predecessors
            preds_str = ""
            rels = task.getPredecessors()
            if rels:
                p_ids = []
                for rel in rels:
                     # org.mpxj.Relation
                     pt = rel.getSourceTask() # Predecessor
                     if pt:
                         p_ids.append(str(pt.getUniqueID()))
                preds_str = ",".join(p_ids)

            # Resources (Contractor)
            contractor_str = ""
            assignments = task.getResourceAssignments()
            if assignments:
                r_names = []
                for asn in assignments:
                    res = asn.getResource()
                    if res:
                        r_name = res.getName()
                        if r_name: r_names.append(str(r_name))
                contractor_str = ", ".join(r_names)

            # Construct Dict
            row = {
                "activity_id": act_id,
                "name": name,
                "start": start_val,
                "finish": finish_val,
                "pct_complete": pct_val,
                "predecessors": preds_str,
                "contractor": contractor_str,
                "style": {"indent": indent_level}
            }
            
            tasks.append(row)
            
        return {
            "project_name": str(project.getProjectProperties().getName() or "Imported Project"),
            "activities": tasks
        }
        
    except Exception as e:
        print(f"MPXJ Parsing Error: {e}")
        # import traceback; traceback.print_exc()
        raise ValueError(f"Error parsing .MPP file: {e}")
        
    finally:
        # Cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except: pass
