import os
import multiprocessing
import subprocess
import time
import shutil
import datetime
import glob
import asyncio
from typing import Union

from pathlib import Path
import requests
from aiogram import Bot

from consts import backups, THRESHOLD
from storage import FileUpload, FolderUpload, BackupRootFolder

def send_backup_files(bot: Bot, chat_id: int, backup_token: str, thread_id: int = None):
    """
    Sends all files associated with the backup identified by backup_token.
    Recursively traverses the backup's structure stored in backups,
    uploads each file (using its absolute_path), and updates its upload_id list.
    For split files (is_split=True), all parts are uploaded and each part's file_id
    is appended to the list.
    After sending, files are deleted from disk.
    
    Parameters:
      - bot: The Bot instance.
      - chat_id: The target chat id.
      - backup_token: The unique token identifying the backup (from a BackupRootFolder).
      - thread_id: (Optional) Message thread id if needed.
    """
    # Look up the backup with the matching token.
    backups.load()
    backup = next((b for b in backups.backups if b.token == backup_token), None)
    if backup is None:
        print(f"Backup with token {backup_token} not found.")
        return

    token = bot.token  # Bot token for URL construction

    def send_file(file_record):
        # Check if file_record.absolute_path exists.
        if not file_record.absolute_path or (not os.path.exists(file_record.absolute_path) \
            and not os.path.exists(file_record.absolute_path + ".001")):
            print(f"File {file_record.name} not found at {file_record.absolute_path}.")
            return
        
        # If the file is marked as split, we need to send all parts.
        if file_record.is_split:
            # Use a glob pattern to find all parts.
            pattern = file_record.absolute_path + ".*"
            parts = sorted(glob.glob(pattern))
            if not parts:
                print(f"No parts found for split archive {file_record.name}.")
                return
            
            for part in parts:
                try:
                    start_time = time.time()
                    with open(part, "rb") as f:
                        response = requests.post(
                            f"https://api.telegram.org/bot{token}/sendDocument",
                            files={"document": f},
                            data={"chat_id": chat_id, "message_thread_id": thread_id}
                        )
                    elapsed_time = time.time() - start_time
                    part_size_mb = os.path.getsize(part) / (1024 * 1024)
                    speed = part_size_mb / elapsed_time if elapsed_time > 0 else 0
                    print(f"Sent part {os.path.basename(part)} in {elapsed_time:.2f}s at {speed:.2f} MB/s")
                    resp_json = response.json()
                    if resp_json.get("ok"):
                        file_id = resp_json["result"]["document"]["file_id"]
                        print(f"File ID for part {os.path.basename(part)}: {file_id}")
                        file_record.upload_id.append(file_id)
                    else:
                        print(f"Error sending {os.path.basename(part)}: {resp_json}")
                    os.remove(part)
                    print(f"Deleted part {os.path.basename(part)} from disk.")
                except Exception as e:
                    print(f"Failed to send part {os.path.basename(part)}: {e}")
        else:
            # Normal (non-split) file processing.
            try:
                start_time = time.time()
                with open(file_record.absolute_path, "rb") as f:
                    response = requests.post(
                        f"https://api.telegram.org/bot{token}/sendDocument",
                        files={"document": f},
                        data={"chat_id": chat_id, "message_thread_id": thread_id}
                    )
                elapsed_time = time.time() - start_time
                file_size_mb = os.path.getsize(file_record.absolute_path) / (1024 * 1024)
                speed = file_size_mb / elapsed_time if elapsed_time > 0 else 0
                print(f"Sent {file_record.name} in {elapsed_time:.2f}s at {speed:.2f} MB/s")
                resp_json = response.json()
                if resp_json.get("ok"):
                    file_id = resp_json["result"]["document"]["file_id"]
                    print(f"File ID for {file_record.name}: {file_id}")
                    file_record.upload_id.append(file_id)
                else:
                    print(f"Error sending {file_record.name}: {resp_json}")
                os.remove(file_record.absolute_path)
                print(f"Deleted {file_record.name} from disk.")
            except Exception as e:
                print(f"Failed to send {file_record.name}: {e}")

    def process_item(item: Union["FolderUpload", "FileUpload"]):
        # If it's a FileUpload, send it.
        if hasattr(item, "absolute_path"):
            send_file(item)
        # If it's a FolderUpload, recursively process its children.
        if hasattr(item, "children") and item.children:
            for child in item.children:
                process_item(child)

    # Process each child of the backup root folder.
    for child in backup.children:
        process_item(child)
    
    time.sleep(3)
    backup.uploaded = True
    backups.save()
    print("Finished sending backup files.")

def create_backup(path: str, mode: str):
    backups.load()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tmp_dir = os.path.join(script_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    base_name = os.path.basename(os.path.abspath(path))
    output_pattern = os.path.join(tmp_dir, f"{current_date}_{base_name}.7z")
    num_threads = max(1, int(multiprocessing.cpu_count() * 0.7))
    
    # Helper: if a file already exists (i.e. a split archive part exists), append (1), (2), etc.
    def get_unique_filename(filename: str) -> str:
        unique_name = filename
        counter = 1
        while os.path.exists(unique_name + ".001"):
            base, ext = os.path.splitext(filename)
            unique_name = f"{base} ({counter}){ext}"
            counter += 1
        return unique_name

    if mode == "archive":
        # Always create a BackupRootFolder so that it gets its own unique token.
        output_pattern = get_unique_filename(output_pattern)
        command = [
            "7z", "a", output_pattern,
            path, 
            "-m0=LZMA2",  # Use LZMA2 compression
            "-mx5",        # Medium compression level
            f"-v{int(THRESHOLD / 1024 / 1024)}m",       # Split into 48MB parts
            f"-mmt{num_threads}"  # Use 70% of available CPU cores
        ]
        
        subprocess.run(command, check=True)
        print(f"Created multi-volume archive: {output_pattern}*")
        
        # Instead of collecting all parts (which have appended suffixes), we store the base archive path.
        backup_folder = BackupRootFolder(name=base_name, children=[])
        file_upload = FileUpload(
            name=os.path.basename(output_pattern),
            upload_id=[],
            absolute_path=os.path.abspath(output_pattern),
            is_split=True
        )
        backup_folder.children.append(file_upload)
        backups.add_backup(backup_folder)
        backups.save()
        print(f"Updated backups storage with archive backup '{base_name}' (token: {backup_folder.token}).")
        
    else:
        # Non-archive mode: build the full directory structure.
        if os.path.isdir(path):
            folder_dict = {}
            abs_path = os.path.abspath(path)
            # Create top-level folder record as a BackupRootFolder (to have a unique token).
            folder_dict[abs_path] = BackupRootFolder(name=base_name, children=[])
            
            for root, dirs, files in os.walk(path):
                root_abs = os.path.abspath(root)
                if root_abs not in folder_dict:
                    folder_dict[root_abs] = FolderUpload(name=os.path.basename(root_abs), upload_id="", children=[])
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    if file_size < THRESHOLD:
                        dest_file = os.path.join(tmp_dir, file)
                        shutil.copy2(file_path, dest_file)
                        print(f"Copied {file} to {tmp_dir}")
                        file_record = FileUpload(
                            name=file,
                            upload_id=[],
                            absolute_path=os.path.abspath(dest_file),
                            is_split=False
                        )
                    else:
                        output_file = os.path.join(tmp_dir, f"{current_date}_{file}.7z")
                        output_file = get_unique_filename(output_file)
                        command = [
                            "7z", "a", output_file,
                            file_path,
                            "-m0=LZMA2",
                            "-mx5",
                            f"-v{int(THRESHOLD / 1024 / 1024)}m",
                            f"-mmt{num_threads}"
                        ]
                        subprocess.run(command, check=True)
                        print(f"Compressed {file} into multi-volume archive {output_file}")
                        file_record = FileUpload(
                            name=os.path.basename(output_file),
                            upload_id=[],
                            absolute_path=os.path.abspath(output_file),
                            is_split=True
                        )
                    folder_dict[root_abs].children.append(file_record)
                
                for d in dirs:
                    subdir_abs = os.path.abspath(os.path.join(root, d))
                    if subdir_abs not in folder_dict:
                        folder_dict[subdir_abs] = FolderUpload(name=d, upload_id="", children=[])
                    parent_dir = os.path.abspath(root)
                    if not any(isinstance(child, FolderUpload) and child.name == d for child in folder_dict[parent_dir].children):
                        folder_dict[parent_dir].children.append(folder_dict[subdir_abs])
            
            backup_folder = folder_dict[abs_path]
            backups.add_backup(backup_folder)
            backups.save()
            print(f"Updated backups storage with folder structure backup '{base_name}' (token: {backup_folder.token}).")
        elif os.path.isfile(path):
            file_size = os.path.getsize(path)
            if file_size < THRESHOLD:
                dest_file = os.path.join(tmp_dir, base_name)
                shutil.copy2(path, dest_file)
                print(f"Copied file {base_name} to {tmp_dir}")
                file_record = FileUpload(
                    name=base_name,
                    upload_id=[],
                    absolute_path=os.path.abspath(dest_file),
                    is_split=False
                )
            else:
                output_file = os.path.join(tmp_dir, f"{current_date}_{base_name}.7z")
                output_file = get_unique_filename(output_file)
                command = [
                    "7z", "a", output_file,
                    path,
                    "-m0=LZMA2",
                    "-mx5",
                    f"-v{int(THRESHOLD / 1024 / 1024)}m",
                    f"-mmt{num_threads}"
                ]
                subprocess.run(command, check=True)
                print(f"Compressed file {base_name} into multi-volume archive {output_file}")
                file_record = FileUpload(
                    name=os.path.basename(output_file),
                    upload_id=[],
                    absolute_path=os.path.abspath(output_file),
                    is_split=True
                )
            backup_folder = BackupRootFolder(name=base_name, children=[file_record])
            backups.add_backup(backup_folder)
            backups.save()
            print(f"Updated backups storage with backup for file '{base_name}' (token: {backup_folder.token}).")
    
    # Return the token of the backup root folder.
    return backup_folder.token

async def download(backup_token: str, bot: Bot):
    """
    Downloads all files associated with the backup identified by backup_token
    from Telegram into the default system Downloads folder. The backup structure
    is retrieved from the global backups storage.
    
    For each FileUpload, every file part (as indicated by its upload_id list) is downloaded.
    After downloading, any file that was split into a multi-volume archive is extracted
    into its own folder (i.e. the folder where its parts reside) and its downloaded archive parts are deleted.
    
    Parameters:
      - backup_token: The unique token for the backup (from a BackupRootFolder).
      - bot: The aiogram Bot instance.
    """
    # Reload backups storage
    backups.load()
    
    # Find the backup root folder with the given token.
    backup = next((b for b in backups.backups if b.token == backup_token), None)
    if backup is None:
        print(f"Backup with token {backup_token} not found.")
        return False
    if not backup.uploaded:
        return False
    # Determine the default system Downloads folder.
    downloads_dir = Path.home() / "Downloads" / f"Backup_{backup.name}_{backup.creatin_date}"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading backup '{backup.name}' into: {downloads_dir}")

    async def download_item(item, current_path: Path):
        # If the item is a folder, create a subfolder and process children.
        if hasattr(item, "children") and item.children:
            subfolder = current_path / item.name
            subfolder.mkdir(parents=True, exist_ok=True)
            for child in item.children:
                await download_item(child, subfolder)
        else:
            # For FileUpload items:
            if not item.upload_id:
                print(f"No upload IDs for file '{item.name}', skipping download.")
                return
            part_counter = 1
            for file_id in item.upload_id:
                try:
                    file_info = await bot.get_file(file_id)
                    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
                    # For split files, append a part number.
                    if len(item.upload_id) > 1:
                        filename = f"{item.name}.{part_counter:03d}"
                    else:
                        filename = item.name
                    destination = current_path / filename
                    print(f"Downloading '{filename}' from {file_url}...")
                    response = requests.get(file_url)
                    if response.status_code == 200:
                        with open(destination, "wb") as f:
                            f.write(response.content)
                        print(f"Downloaded '{filename}' to {destination}")
                    else:
                        print(f"Failed to download '{filename}': HTTP {response.status_code}")
                    part_counter += 1
                except Exception as e:
                    print(f"Error downloading part of '{item.name}': {e}")

    await download_item(backup, downloads_dir)
    print("Backup download complete.")

    # Now, find all split archive first parts and extract them.
    # Use a recursive glob search for files ending with ".001".
    split_pattern = str(downloads_dir / "**" / "*.001")
    split_archives = glob.glob(split_pattern, recursive=True)
    for part in split_archives:
        # Extract into the same folder where the parts reside.
        extract_folder = os.path.dirname(part)
        base_archive = part[:-4]  # remove the ".001" suffix
        print(f"Extracting archive from {part} into {extract_folder}...")
        
        # Run extraction asynchronously.
        process = await asyncio.create_subprocess_exec(
            "7z", "x", part, f"-o{extract_folder}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print(f"Extraction successful for {part}. Now deleting all parts for archive '{base_archive}'...")
            # Delete all parts matching the base archive name in the same folder.
            deletion_pattern = os.path.join(extract_folder, Path(base_archive).name + ".*")
            for f in glob.glob(deletion_pattern):
                try:
                    os.remove(f)
                    print(f"Deleted {f}")
                except Exception as e:
                    print(f"Failed to delete {f}: {e}")
        else:
            print(f"Extraction failed for {part}: {stderr.decode().strip()}")

    print("Backup extraction complete.")
    return True