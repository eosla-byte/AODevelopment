
import io
import datetime
import os
import sys
import shutil
import glob

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
# --- JVM UTILS ---
def find_libjvm(root_path):
    """Recursively find libjvm.so"""
    if not root_path or not os.path.exists(root_path): return None
    for root, dirs, files in os.walk(root_path):
        if "libjvm.so" in files:
            return os.path.join(root, "libjvm.so")
    return None

def ensure_jvm_started():
    """Foundational function to find and start JVM"""
    import jpype
    import mpxj
    import os
    import shutil
    import glob
    import tarfile
    import urllib.request
    import sys

    if jpype.isJVMStarted():
        return "JVM Already Started"

    print("DEBUG: ensure_jvm_started() called. Hunting for libjvm.so...")

    # A. Resolve JAVA_HOME
    java_home = os.environ.get("JAVA_HOME")
    jvm_path = None

    # 1. Standard Search in JAVA_HOME
    if java_home:
        candidates = [
            os.path.join(java_home, "lib", "server", "libjvm.so"),
            os.path.join(java_home, "lib", "amd64", "server", "libjvm.so"),
            os.path.join(java_home, "jre", "lib", "amd64", "server", "libjvm.so"),
        ]
        for c in candidates:
            if os.path.exists(c):
                jvm_path = c
                break
        if not jvm_path:
            jvm_path = find_libjvm(java_home)

    # 2. Heuristic Search (shutil.which)
    if not jvm_path:
        java_bin = shutil.which("java")
        if java_bin:
            # /path/to/bin/java -> /path/to
            possible_home = os.path.dirname(os.path.dirname(os.path.realpath(java_bin)))
            print(f"DEBUG: Found java binary at {java_bin}, guessing home: {possible_home}")
            jvm_path = find_libjvm(possible_home)
            if jvm_path and not java_home:
                os.environ["JAVA_HOME"] = possible_home

    # 3. Nix Store Search (Robust)
    if not jvm_path and os.path.exists("/nix/store"):
        print("DEBUG: Searching /nix/store for libjvm.so...")
        nix_candidates = glob.glob("/nix/store/*jdk*/lib/server/libjvm.so")
        if not nix_candidates:
            nix_candidates = glob.glob("/nix/store/*headless*/lib/server/libjvm.so")
        
        if not nix_candidates:
             # Try deeper search for "libjvm.so" within any *jdk* dir
             # Use a generator to stop at first match to save time
             try:
                 for root, dirs, files in os.walk("/nix/store"):
                     if root.count(os.sep) > 6: # limit depth
                         del dirs[:]
                         continue 
                     # Optimization: only traverse dirs looking like jdk/jvm
                     # But "/nix/store" flat list is huge.
                     # Better: glob top level directories matching *jdk*
                     pass # Rely on glob above.
             except: pass

        if nix_candidates:
            jvm_path = nix_candidates[0]
            print(f"DEBUG: Found in Nix Store: {jvm_path}")
            # Try to infer JAVA_HOME
            new_home = os.path.dirname(os.path.dirname(os.path.dirname(jvm_path)))
            if not os.environ.get("JAVA_HOME"):
                 os.environ["JAVA_HOME"] = new_home

    # 4. System Paths
    if not jvm_path:
        sys_paths = ["/usr/lib/jvm", "/usr/java", "/opt/java", "/app/jdk", "/usr/local/openjdk-17"]
        for p in sys_paths:
            found = find_libjvm(p)
            if found:
                jvm_path = found
                break

    # 5. Runtime Download (Falbiack - The "Nuclear Option")
    # If Nixpacks failed or env is weird, download JDK manually to /tmp
    if not jvm_path:
        print("WARNING: No JVM found in system. Initiating Runtime Download (Fallback)...")
        try:
             # Define check inside
            def download_jdk():
                JDK_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.9%2B9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.9_9.tar.gz"
                DEST_DIR = "/tmp/jdk"
                LIBJVM_PATH = os.path.join(DEST_DIR, "lib", "server", "libjvm.so")
                
                if os.path.exists(LIBJVM_PATH):
                    return LIBJVM_PATH

                if not os.path.exists(DEST_DIR):
                     os.makedirs(DEST_DIR)
                
                print(f"DEBUG: Downloading JDK from {JDK_URL}...")
                tar_path = os.path.join(DEST_DIR, "jdk.tar.gz")
                urllib.request.urlretrieve(JDK_URL, tar_path)
                
                print("DEBUG: Extracting JDK...")
                with tarfile.open(tar_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        api_path = member.name.split('/', 1)
                        if len(api_path) > 1:
                            member.name = api_path[1]
                            tar.extract(member, path=DEST_DIR)
                
                print("DEBUG: JDK Extracted.")
                return find_libjvm(DEST_DIR)

            jvm_path = download_jdk()
            if jvm_path:
                 print(f"DEBUG: Runtime Download successful. JVM at {jvm_path}")
                 os.environ["JAVA_HOME"] = os.path.dirname(os.path.dirname(os.path.dirname(jvm_path)))
        
        except Exception as e:
            print(f"CRITICAL: Runtime Download Failed: {e}")

    # 6. Default Fallback
    if not jvm_path:
        try:
            jvm_path = jpype.getDefaultJVMPath()
        except: pass

    if not jvm_path:
        raise ValueError("CRITICAL: libjvm.so not found. Please install a JDK (e.g. jdk17 in nixpacks).")

    print(f"DEBUG: Starting JVM with {jvm_path}")
    
    # CALCULATE CLASSPATH
    # We must include MPXJ jars.
    classpath = []
    
    # 1. Automatic MPXJ detection (Recursive)
    try:
        import mpxj
        mpxj_dir = os.path.dirname(mpxj.__file__)
        print(f"DEBUG: Hunting for JARs in {mpxj_dir}")
        
        found_jars = []
        # Walk recursively to find jars in lib/, etc.
        for root, dirs, files in os.walk(mpxj_dir):
            for file in files:
                if file.endswith(".jar"):
                    full_path = os.path.join(root, file)
                    found_jars.append(full_path)
        
        if found_jars:
            print(f"DEBUG: Found {len(found_jars)} MPXJ jars: {[os.path.basename(j) for j in found_jars]}")
            classpath.extend(found_jars)
        else:
             print("WARNING: No JARs found in mpxj package directory recursively.")

    except Exception as e:
        print(f"WARNING: Could not auto-detect MPXJ jars: {e}")

    # 2. Add current directory
    classpath.append(".")
    
    # 3. System Classpath
    if os.environ.get("CLASSPATH"):
        classpath.append(os.environ.get("CLASSPATH"))

    cp_args = "-Djava.class.path=" + os.pathsep.join(classpath)
    print(f"DEBUG: JVM Classpath Args: {cp_args}")

    try:
        # Check if startJVM accepts arguments list or just args
        jpype.startJVM(jvm_path, cp_args, convertStrings=False)
        return jvm_path
    except Exception as e:
        if "JVM is already started" in str(e):
             return "JVM Already Started"
        raise e

def parse_mpp(content: bytes) -> dict:
    """
    Parses .mpp file using MPXJ.
    """
    import jpype
    import mpxj 
    import tempfile
    import os

    # Ensure JVM
    ensure_jvm_started()


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
        from net.sf.mpxj.reader import UniversalProjectReader
        reader = UniversalProjectReader()
        print(f"DEBUG: MPXJ Reading file {tmp_path} size={os.path.getsize(tmp_path)}")
        try:
            project = reader.read(tmp_path)
        except Exception as read_err:
             print(f"CRITICAL: MPXJ Reader crashed: {read_err}")
             raise read_err

        # 5. Extract Tasks
        tasks = []
        # getTasks() returns a java.util.List<Task>
        # Iterate over java list
        # Java List to generic list
        raw_tasks = project.getTasks()
        print(f"DEBUG: MPXJ found {raw_tasks.size()} raw tasks.")

        # Limit debug output
        debug_count = 0
        
        for task in raw_tasks:
            # Skip root/null tasks if any (often ID 0 is Project Summary)
            if not task: continue
            
            # Extract basics
            t_id = task.getUniqueID() # Integer
            t_name = task.getName()
            
            # Only debug first 5
            if debug_count < 5:
                print(f"DEBUG TASK: ID={t_id} Name={t_name} Outl={task.getOutlineLevel()}")
                debug_count += 1

            t_start = task.getStart()
            t_finish = task.getFinish()
            t_pct = task.getPercentageComplete() 
            t_outline = task.getOutlineLevel() # Integer
            
            # Skip tasks without ID?
            if not t_id: 
                 # Maybe it's a null task
                 continue 
            
            # --- Field Conversion ---
            # ID
            act_id = str(t_id)
            
            # Name
            name = str(t_name) if t_name else "Unnamed Task"
            
            # Dates
            start_val = None
            if t_start:
                 # Raw is like: 2024-01-26T14:00
                 try:
                     s_str = str(t_start)
                     if ' Mon ' in s_str or ' Tue ' in s_str: 
                          # Java Date toString() is crazy sometimes?
                          # Actually MPXJ returns java.util.Date usually converted to str by jpype
                          # But let's trust string conversion or use specific accessors
                          pass
                     
                     if 'T' in s_str:
                         start_val = datetime.datetime.fromisoformat(s_str)
                     else:
                         # Fallback if just YYYY-MM-DD
                         # sanitize
                         s_str = s_str.split(' ')[0] 
                         try:
                            start_val = datetime.datetime.strptime(s_str, "%Y-%m-%d")
                         except:
                            # Try other format?
                            pass
                 except: 
                     pass

            finish_val = None
            if t_finish:
                 try:
                     f_str = str(t_finish)
                     if 'T' in f_str:
                         finish_val = datetime.datetime.fromisoformat(f_str)
                     else:
                         f_str = f_str.split(' ')[0]
                         try:
                             finish_val = datetime.datetime.strptime(f_str, "%Y-%m-%d")
                         except: pass
                 except: pass

            # Percent
            pct_val = 0.0
            if t_pct:
                 try:
                     pct_val = float(str(t_pct))
                 except: pass
            
            # Duration 
            dur_val = "0 d"
            t_dur = task.getDuration()
            if t_dur:
                dur_val = str(t_dur) # "5.0d" normally

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
                     pt = rel.getPredecessorTask() 
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
                "duration": dur_val,
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
