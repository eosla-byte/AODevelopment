
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
    import shutil
    import sys
    import glob
    
    import tarfile
    import urllib.request
    
    # 1. Ensure JVM is started
    if not jpype.isJVMStarted():
        
        def download_jdk():
            """Downloads and extracts JDK to /tmp/jdk if missing."""
            JDK_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.9%2B9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.9_9.tar.gz"
            DEST_DIR = "/tmp/jdk"
            LIBJVM_PATH = os.path.join(DEST_DIR, "lib", "server", "libjvm.so")
            
            # Check if likely already installed (e.g. from previous run if persistent /tmp?)
            # Actually /tmp is usually ephemeral, so we assume fresh download or check existence
            if os.path.exists(LIBJVM_PATH):
                return LIBJVM_PATH

            print(f"DEBUG: Downloading JDK from {JDK_URL}...")
            try:
                if not os.path.exists(DEST_DIR):
                    os.makedirs(DEST_DIR)
                
                tar_path = os.path.join(DEST_DIR, "jdk.tar.gz")
                urllib.request.urlretrieve(JDK_URL, tar_path)
                
                print("DEBUG: Extracting JDK...")
                with tarfile.open(tar_path, "r:gz") as tar:
                    # Strip first component (jdk-17...) to extract directly to DEST_DIR
                    # Python tarfile doesn't support strip_components easily like cli
                    # So we verify member names
                    for member in tar.getmembers():
                        # remove first path segment
                        api_path = member.name.split('/', 1)
                        if len(api_path) > 1:
                            member.name = api_path[1]
                            tar.extract(member, path=DEST_DIR)
                
                print("DEBUG: JDK Extracted.")
                # Verify
                # Recursive search in /tmp/jdk because structure might vary
                found = find_libjvm(DEST_DIR)
                if found: return found
                
            except Exception as e:
                print(f"CRITICAL: Runtime JDK Download failed: {e}")
                import traceback
                traceback.print_exc()
            
            return None

        # Helper to recursively find libjvm.so
        def find_libjvm(root_path):
            if not root_path or not os.path.exists(root_path): return None
            for root, dirs, files in os.walk(root_path):
                if "libjvm.so" in files:
                    return os.path.join(root, "libjvm.so")
            return None

        # A. Resolve JAVA_HOME (Existing logic)
        java_home = os.environ.get("JAVA_HOME")
        jvm_path = None
        
        # ... existing search logic ...
        
        # Strategy 3: RUNTIME DOWNLOAD (The Ultra-Nuclear Option)
        if not jvm_path:
            print("WARNING: No JVM found. Attempting Runtime Download...")
            jvm_path = download_jdk()
            if jvm_path:
                print(f"DEBUG: Runtime Download successful. JVM at {jvm_path}")
                # Set env vars for other tools if needed
                os.environ["JAVA_HOME"] = os.path.dirname(os.path.dirname(os.path.dirname(jvm_path)))

        if not jvm_path:
             print("CRITICAL: libjvm.so not found via any method.")
             # ... error handling ...
        if not java_home:
            java_path = shutil.which("java")
            print(f"DEBUG: shutil.which('java') returned: {java_path}")
            
            if java_path:
                # /nix/store/.../bin/java -> go up two levels
                real_path = os.path.realpath(java_path)
                java_home = os.path.dirname(os.path.dirname(real_path))
                os.environ["JAVA_HOME"] = java_home
                print(f"Auto-detected JAVA_HOME: {java_home}")
            else:
                print(f"DEBUG: PATH env var: {os.environ.get('PATH')}")
        
        # B. Hunt for libjvm.so
        jvm_path = None
        
        # Strategy 1: Standard Search in Home
        if java_home:
            # Try specific common subpaths first for speed
            candidates = [
                os.path.join(java_home, "lib", "server", "libjvm.so"),
                os.path.join(java_home, "lib", "amd64", "server", "libjvm.so"),
                os.path.join(java_home, "jre", "lib", "amd64", "server", "libjvm.so"),
                os.path.join(java_home, "lib", "jvm.cfg"), # Check existence
            ]
            for c in candidates:
                if os.path.exists(c) and c.endswith("libjvm.so"):
                    jvm_path = c
                    break
            
            # If not in obvious spots, deep search inside Home
            if not jvm_path:
                jvm_path = find_libjvm(java_home)

        # Strategy 1.5: System Paths (Apt/Debian/Ubuntu/Manual)
        if not jvm_path:
             print("Searching /app/jdk and /usr/lib/jvm for libjvm.so...")
             if os.path.exists("/app/jdk"):
                 jvm_path = find_libjvm("/app/jdk")
             
             if not jvm_path:
                 jvm_path = find_libjvm("/usr/lib/jvm")
             
        if not jvm_path and os.path.exists("/usr/java"):
             jvm_path = find_libjvm("/usr/java")

        # Strategy 2: Nix Store Wildcards (Last Resort - Very Broad)
        if not jvm_path:
            print("Searching /nix/store for libjvm.so (Broad Search)...")
            
            # DEBUG: Walk nix store level 2 to see what packages exist
            try:
                print("DEBUG: Walking /nix/store to find jdk...")
                for root, dirs, files in os.walk("/nix/store"):
                    if root.count(os.sep) - "/nix/store".count(os.sep) > 2:
                        del dirs[:] # Don't go deep
                        continue
                    for d in dirs:
                        if "jdk" in d or "jvm" in d or "headless" in d:
                            print(f"DEBUG: Found candidate dir: {d}")
                            # Check if libjvm exists inside
                            find_libjvm(os.path.join(root, d))
            except Exception as e:
                print(f"DEBUG: Error walking nix store: {e}")

            # 1. Broadest Search: Any package having lib/server/libjvm.so
            # 1. Broadest Search: Any package having lib/server/libjvm.so
            nix_dirs = glob.glob("/nix/store/*/lib/server/libjvm.so") 
            
            # 2. Arch specific
            if not nix_dirs:
                nix_dirs = glob.glob("/nix/store/*/lib/*/server/libjvm.so")

            if nix_dirs:
                # Prefer one that looks like 'jdk' or 'headless'
                best_match = nix_dirs[0]
                for p in nix_dirs:
                    if "jdk" in p and "headless" in p:
                         best_match = p
                         break
                jvm_path = best_match
                print(f"DEBUG: Found libjvm.so in nix store: {jvm_path}")

        if not jvm_path:
             # Final fallback: use default and pray (likely fails based on logs)
             try:
                 jvm_path = jpype.getDefaultJVMPath()
             except: pass

        if not jvm_path:
             print("CRITICAL: libjvm.so not found via any method.")
             print(f"DEBUG: CWD is {os.getcwd()}")
             print("DEBUG: Listing /nix/store top level (filtered)...")
             try:
                 # Last ditch debug: print what jdk libs exist
                 debug_glob = glob.glob("/nix/store/*jdk*") + glob.glob("/nix/store/*openjdk*")
                 print(f"DEBUG: Available JDK paths in store: {debug_glob[:5]}")
                 print(f"DEBUG: All Keys: {list(os.environ.keys())}")
                 if "JAVA_HOME" in os.environ:
                     print(f"DEBUG: JAVA_HOME={os.environ['JAVA_HOME']}")
             except: pass
             
             raise ValueError("CRITICAL: libjvm.so not found! Please set JAVA_HOME validly.")

        print(f"Starting JVM with lib: {jvm_path}")

        try:
            # Explicitly pass classpath from jpype.getClassPath() which mpxj populated
            jpype.startJVM(jvm_path, classpath=jpype.getClassPath())
        except Exception as e:
            if "JVM is already started" in str(e):
                pass
            else:
                print(f"JVM Start Error: {e}")
                # Analyze common crashers
                if "libjvm.so" in str(e):
                     raise ValueError(f"JVM Link Error: {e}")
                raise e

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
                     pt = rel.getPredecessorTask() 
                     if pt:
                         p_ids.append(str(pt.getUniqueID()))
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
