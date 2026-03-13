"""
Local filesystem backend for LLM06. Files stored in local_box_data/root/.
"""
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LLM06] %(levelname)s: %(message)s")
log = logging.getLogger("file_utils")

# Base path: challenges/LLM06_Excessive_Agency/local_box_data
_utils_dir = os.path.dirname(os.path.abspath(__file__))
_challenge_dir = os.path.dirname(os.path.dirname(os.path.dirname(_utils_dir)))
LOCAL_BOX_BASE = os.path.join(_challenge_dir, "local_box_data", "root")

# Folder paths - match structure: User_Accessible_Folder, Logs, Restricted_Access_Folder
ACCESSIBLE_PATH = os.path.join(LOCAL_BOX_BASE, 'User_Accessible_Folder')
RESTRICTED_PATH = os.path.join(LOCAL_BOX_BASE, 'Restricted_Access_Folder')

WHOLE_BOX_FOLDER_ID = LOCAL_BOX_BASE
ACCESSIBLE_BOX_FOLDER_ID = ACCESSIBLE_PATH
RESTRICTED_BOX_FOLDER_ID = RESTRICTED_PATH

# Set env vars so llm06_2025_service gets the same paths
os.environ['WHOLE_BOX_FOLDER_ID'] = WHOLE_BOX_FOLDER_ID
os.environ['ACCESSIBLE_BOX_FOLDER_ID'] = ACCESSIBLE_BOX_FOLDER_ID
os.environ['RESTRICTED_BOX_FOLDER_ID'] = RESTRICTED_BOX_FOLDER_ID

if not os.path.exists(LOCAL_BOX_BASE):
    os.makedirs(LOCAL_BOX_BASE, exist_ok=True)
    for sub in ['User_Accessible_Folder', 'Logs', 'Restricted_Access_Folder']:
        os.makedirs(os.path.join(LOCAL_BOX_BASE, sub), exist_ok=True)

log.info("Using local filesystem: base=%s", LOCAL_BOX_BASE)


def search_file_recursive(folder_id, file_name):
    """Search for file in folder (and subfolders). Returns (found, path, content)."""
    found_file = False
    file_id = ""
    file_content = "File not found in the accessible folder."
    folder_path = folder_id or WHOLE_BOX_FOLDER_ID

    if not os.path.isdir(folder_path):
        log.warning("search_file_recursive: folder not found %s", folder_path)
        return found_file, file_id, file_content

    try:
        log.info("search_file_recursive folder_id=%s file_name=%s", folder_path, file_name)
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                if f.lower() == file_name.lower():
                    found_file = True
                    full_path = os.path.join(root, f)
                    file_id = full_path
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='replace') as fp:
                            file_content = fp.read()
                        log.info("File found: %s", full_path)
                    except Exception as e:
                        log.error("Failed to read file %s: %s", full_path, e)
                        file_content = f"Error reading file: {e}"
                    return found_file, file_id, file_content
    except Exception as e:
        log.error("search_file_recursive FAILED folder_id=%s: %s", folder_path, e)
        return found_file, file_id, file_content

    log.info("search_file_recursive: file not found (%s)", file_name)
    return found_file, file_id, file_content


def list_all_files(folder_id):
    """List files in folder, returning dict of {folder_name: [files]}."""
    folder_content = {}
    folder_path = folder_id
    if not folder_path:
        log.warning("list_all_files: folder_id is None")
        return folder_content

    if not os.path.isdir(folder_path):
        log.warning("list_all_files: folder not found %s", folder_path)
        return folder_content

    try:
        log.info("list_all_files folder_id=%s", folder_path)
        root_name = os.path.basename(folder_path.rstrip(os.sep))
        folder_content[root_name] = []

        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                folder_content[root_name].append(item)
            elif os.path.isdir(item_path):
                nested = list_all_files(item_path)
                folder_content[f"{root_name}/{item}"] = nested.get(os.path.basename(item), [])

        log.info("list_all_files OK folder_id=%s keys=%s", folder_path, list(folder_content.keys()))
        return folder_content
    except Exception as e:
        log.error("list_all_files FAILED folder_id=%s: %s", folder_path, e)
        return folder_content


def create_file(folder_id, filename, content):
    """Create a new file in the folder."""
    try:
        folder_path = folder_id
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        log.info("create_file OK folder_id=%s filename=%s", folder_path, filename)
        return f"✅ File '{filename}' created successfully"
    except Exception as e:
        log.error("create_file FAILED folder_id=%s filename=%s: %s", folder_id, filename, e)
        return f"❌ Error creating file: {e}"


def update_file(folder_id, file_name, new_content):
    """Update an existing file."""
    found_file, file_id, _ = search_file_recursive(folder_id, file_name)
    if found_file:
        try:
            with open(file_id, "w", encoding="utf-8") as f:
                f.write(new_content)
            log.info("update_file OK file_id=%s", file_id)
            return f"✅ File '{file_name}' updated successfully"
        except Exception as e:
            log.error("update_file FAILED file_id=%s: %s", file_id, e)
            return f"❌ Error updating file: {e}"
    return f"❌ File not found"


def delete_file(folder_id, file_name):
    """Delete a file."""
    found_file, file_id, _ = search_file_recursive(folder_id, file_name)
    if found_file:
        try:
            os.remove(file_id)
            log.info("delete_file OK file_id=%s", file_id)
            return f"✅ File deleted successfully"
        except Exception as e:
            log.error("delete_file FAILED file_id=%s: %s", file_id, e)
            return f"❌ Error deleting file: {e}"
    return f"❌ File not found"
