import requests
import json
import urllib.parse
from .auth import get_access_token

API_BASE = "https://developer.api.autodesk.com"

class AccCopier:
    def __init__(self):
        self.ensure_token()

    def ensure_token(self):
        self.token = get_access_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/vnd.api+json"
        }

    # ========================
    # NAVIGATION
    # ========================

    def get_hubs(self):
        url = f"{API_BASE}/project/v1/hubs"
        res = requests.get(url, headers=self.headers)
        if res.status_code != 200:
            print(f"Error getting hubs: {res.text}")
            return []
        return res.json().get("data", [])

    def get_projects(self, hub_id):
        url = f"{API_BASE}/project/v1/hubs/{hub_id}/projects"
        res = requests.get(url, headers=self.headers)
        if res.status_code != 200:
            print(f"Error getting projects: {res.text}")
            return []
        return res.json().get("data", [])

    def get_top_folders(self, hub_id, project_id):
        url = f"{API_BASE}/project/v1/hubs/{hub_id}/projects/{project_id}/topFolders"
        res = requests.get(url, headers=self.headers)
        if res.status_code != 200:
            print(f"Error getting top folders: {res.text}")
            return []
        data = res.json().get("data", [])
        # Strict Whitelist for Top Level to match UI
        whitelist = ["Project Files", "Plans"]
        filtered = [x for x in data if x["attributes"]["name"] in whitelist]
        return filtered

    def get_folder_contents(self, project_id, folder_id):
        """
        Returns (folders, items) in the directory
        """
        url = f"{API_BASE}/data/v1/projects/{project_id}/folders/{folder_id}/contents"
        res = requests.get(url, headers=self.headers)
        if res.status_code != 200:
            print(f"Error getting contents: {res.text}")
            return [], []
            
        data = res.json().get("data", [])
        # Filter hidden items
        visible_data = [x for x in data if not x["attributes"].get("hidden", False)]
        
        folders = [x for x in visible_data if x["type"] == "folders"]
        items = [x for x in visible_data if x["type"] == "items"]
        return folders, items

    # ========================
    # ACTIONS
    # ========================

    def create_folder(self, project_id, parent_folder_id, folder_name):
        url = f"{API_BASE}/data/v1/projects/{project_id}/folders"
        body = {
            "jsonapi": {"version": "1.0"},
            "data": {
                "type": "folders",
                "attributes": {
                    "name": folder_name,
                    "extension": {
                        "type": "folders:autodesk.bim360:Folder",
                        "version": "1.0"
                    }
                },
                "relationships": {
                    "parent": {
                        "data": {
                            "type": "folders",
                            "id": parent_folder_id
                        }
                    }
                }
            }
        }
        res = requests.post(url, headers=self.headers, json=body)
        if res.status_code in [201, 200]:
            return res.json()["data"]
        else:
            print(f"Error creating folder {folder_name}: {res.text}")
            return None

    def copy_item(self, project_id, item_id, target_folder_id, name_override=None):
        """
        Server-side copy of an ITEM (File) to a target folder.
        Note: The URL format for COPY is specific.
        Docs: https://aps.autodesk.com/en/docs/data/v2/reference/http/projects-project_id-items-item_id-copy-POST/
        Endpoint: POST /data/v1/projects/:project_id/items/:item_id/copy
        Query: ?copy_to=:target_project_id (Required if different project? Optional if same?)
        We assume same project for now or handle cross-project? 
        The 'copy_to' query param is largely for cross-project setups. If omitted, assumes same bucket? 
        Wait, 'parent' in body defines destination.
        """
        # Ensure item_id is URL encoded? Usually not if just a UUID/URN string, but safely handling quotes.
        # But URNs have ':', '/', etc.
        # Usually URL param doesn't need encoding if path param, but special chars might.
        # requests handles it usually? No, path params must be strictly valid.
        
        # NOTE: Autodesk Item IDs are URL Safe Base64 usually (urn:...).
        
        url = f"{API_BASE}/data/v1/projects/{project_id}/items/{item_id}/copy"
        
        # If target is a different project, we might need ?copy_to argument.
        # For now, simplistic same-project implementation.
        
        body = {
            "jsonapi": {"version": "1.0"},
            "data": {
                "type": "items",
                "relationships": {
                    "parent": {
                        "data": {
                            "type": "folders",
                            "id": target_folder_id
                        }
                    }
                }
            }
        }
        
        if name_override:
            body["data"]["attributes"] = {"displayName": name_override}

        # Need to re-auth? copy operations can take time but call is async?
        # No, usually sync response with 201 Created for the new item version.
        
        res = requests.post(url, headers=self.headers, json=body)
        if res.status_code in [201, 200]:
            # print(f"File copied successfully.")
            return res.json()["data"]
        else:
            print(f"Error copying item {item_id}: {res.text}")
            return None

    def recursive_copy(self, project_id, source_folder, target_parent_id, depth=0):
        """
        1. Create 'source_folder.name' inside 'target_parent_id'
        2. Copy all files from source to new folder
        3. Recurse for subfolders
        """
        folder_name = source_folder["attributes"]["name"]
        print(f"{'  '*depth}📂 Creating folder: {folder_name}")
        
        # 1. Create Folder
        new_folder = self.create_folder(project_id, target_parent_id, folder_name)
        if not new_folder:
            print(f"Skipping {folder_name} due to creation failure")
            return
            
        new_folder_id = new_folder["id"]
        
        # 2. Get Contents
        source_id = source_folder["id"]
        sub_folders, items = self.get_folder_contents(project_id, source_id)
        
        # 3. Copy Files
        print(f"{'  '*depth}   Found {len(items)} files, {len(sub_folders)} subfolders.")
        for item in items:
            item_name = item["attributes"]["displayName"]
            print(f"{'  '*depth}   📄 Copying file: {item_name}")
            self.copy_item(project_id, item["id"], new_folder_id)
            
        # 4. Recurse

    def get_folder(self, project_id, folder_id):
        url = f"{API_BASE}/data/v1/projects/{project_id}/folders/{folder_id}"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            return res.json()["data"]
        return None

    def upload_file(self, project_id, folder_id, file_path, file_name):
        """
        Uploads a local file to ACC.
        Step 1: Create Storage
        Step 2: Upload Stream
        Step 3: Create Item
        """
        # 1. Create Storage
        storage_url = f"{API_BASE}/data/v1/projects/{project_id}/storage"
        body = {
            "jsonapi": {"version": "1.0"},
            "data": {
                "type": "objects",
                "attributes": {
                    "name": file_name
                },
                "relationships": {
                    "target": {
                        "data": {"type": "folders", "id": folder_id}
                    }
                }
            }
        }
        res = requests.post(storage_url, headers=self.headers, json=body)
        if res.status_code != 201:
            print(f"Error creating storage: {res.text}")
            return None
            
        storage_data = res.json()["data"]
        storage_id = storage_data["id"]
        bucket_key = storage_id.split(":")[3].split("/")[0] # approximate parsing or use from response?
        # Usually storage id: urn:adsk.objects:os.object:wip.dm.prod/UUID
        # The response usually contains 'links' for upload if it's OSS?
        # For Data Management API, we usually upload to the bucket.
        # Actually, Data V1 Storage endpoint returns data.id.
        # We simply upload to the OBJECTS API using the bucket/key derived?
        # NO, Data V1 is simpler:
        # Actually for BIM 360/ACC, Create Storage returns an ID.
        # Then we PUT to that storage location?
        
        # Simpler: The response usually doesn't give a direct S3 link unless we ask or use OSS directly.
        # But we must use Create Storage to register it in DM.
        
        # Let's inspect the ID.
        # If ID = "urn:adsk.objects:os.object:wip.dm.prod/1234..."
        # We upload to OSS: PUT https://developer.api.autodesk.com/oss/v2/buckets/{bucketKey}/objects/{objectName}
        # Bucket Key is the part after os.object:
        
        # 2. Extract Bucket Key
        try:
            # ID format: urn:adsk.objects:os.object:wip.dm.prod/UUID
            # Robust parsing: Split by ':' and take the last segment, then split by '/'
            urn_parts = storage_id.split(':')
            if len(urn_parts) > 0:
                last_part = urn_parts[-1] # wip.dm.prod/UUID
                if '/' in last_part:
                    bucket_key = last_part.split('/')[0]
                    object_key = last_part.split('/', 1)[1]
                else:
                    raise Exception("Invalid URN format (no slash)")
            else:
                 raise Exception("Invalid URN format (empty)")
            
            # debug
            print(f"Uploading to Bucket: {bucket_key}, Object: {object_key}")
        except Exception as e:
             print(f"Error parsing storage ID '{storage_id}': {e}")
             return None
        
        # 2. Upload to OSS
        with open(file_path, "rb") as f:
            content = f.read()

        # Limit check
        if len(content) > 100 * 1024 * 1024:
            print("Error: File too large (>100MB) for simple upload.")
            return None
            
        oss_url = f"{API_BASE}/oss/v2/buckets/{bucket_key}/objects/{object_key}"
        auth = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/octet-stream"
        }
        
        try:
            res_upload = requests.put(oss_url, headers=auth, data=content)
            res_upload.raise_for_status()
        except Exception as e:
            print(f"Upload failed: {e}")
            if res_upload: 
                print(f"OSS Response: {res_upload.status_code} - {res_upload.text}")
            return None
        
        if res_upload.status_code != 200:
             print(f"Error uploading bytes: {res_upload.text}")
             return None
             
        # 3. Create Item (The File Version in Doc Mgmt)
        item_url = f"{API_BASE}/data/v1/projects/{project_id}/items"
        item_body = {
            "jsonapi": {"version": "1.0"},
            "data": {
                "type": "items",
                "attributes": {
                    "displayName": file_name,
                    "extension": {
                        "type": "items:autodesk.bim360:File",
                        "version": "1.0"
                    }
                },
                "relationships": {
                    "tip": {
                        "data": {
                            "type": "versions", "id": "1" # Temp ID
                        }
                    },
                    "parent": {
                        "data": {
                            "type": "folders", "id": folder_id
                        }
                    }
                }
            },
            "included": [
                {
                    "type": "versions",
                    "id": "1",
                    "attributes": {
                        "name": file_name,
                        "extension": {
                            "type": "versions:autodesk.bim360:File",
                            "version": "1.0"
                        }
                    },
                    "relationships": {
                        "storage": {
                            "data": {
                                "type": "objects",
                                "id": storage_id
                            }
                        }
                    }
                }
            ]
        }
        
        res_item = requests.post(item_url, headers=self.headers, json=item_body)
        if res_item.status_code in [201, 200]:
            return res_item.json()["data"]
        else:
            print(f"Error creating item: {res_item.text}")
            return None

