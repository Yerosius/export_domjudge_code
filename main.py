#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import getpass
import sys
import subprocess
import tempfile
import zipfile
import shutil

def install_and_import(package, import_name=None):
    import_name = import_name or package
    try:
        __import__(import_name)
    except ImportError:
        print(f"[INFO] Module '{package}' not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
        print(f"[INFO] Module '{package}' installed.")

if __name__ == '__main__':

    install_and_import("mysql-connector-python", "mysql.connector")
    install_and_import("tqdm")

    import mysql.connector
    from tqdm import tqdm

    print("DOMJudge Contest Source Code Export Tool")

    db_host = input("Enter database host (default: localhost): ").strip() or "localhost"
    db_user = input("Enter database username (default: root): ").strip() or "root"
    db_pass = getpass.getpass("Enter database password: ").strip()
    db_name = input("Enter database name (default: domjudge): ").strip() or "domjudge"
    contest_id = input("Enter contest ID: ").strip()

    temp_dir = tempfile.mkdtemp(prefix=f"contest_{contest_id}_")

    try:
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name
        )
    except mysql.connector.Error as err:
        print(f"[ERROR] Could not connect to database: {err}")
        sys.exit(1)

    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT s.submitid, s.teamid, s.probid, s.langid, f.sourcecode, f.filename
    FROM submission s
    JOIN submission_file f ON s.submitid = f.submitid
    WHERE s.cid = %s
    ORDER BY s.teamid, s.probid, s.submitid
    """
    cursor.execute(query, (contest_id,))
    rows = cursor.fetchall()
    total_files = len(rows)
    if total_files == 0:
        print("[WARNING] No submissions found for this contest.")
        sys.exit(0)

    LANG_EXT = {
        'c': 'c',
        'cpp': 'cpp',
        'java': 'java',
        'python3': 'py'
    }

    for row in tqdm(rows, desc="Exporting submissions", unit="file"):
        team = row['teamid']
        problem = row['probid']
        lang = row['langid']
        submitid = row['submitid']
        filename = row['filename'] if row['filename'] else f"{submitid}.{LANG_EXT.get(lang,'txt')}"

        dir_path = os.path.join(temp_dir, f"team_{team}", f"problem_{problem}")
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "wb") as f:
            f.write(row['sourcecode'])

    cursor.close()
    conn.close()

    archive_name = f"contest_{contest_id}_submissions.zip"
    with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname = os.path.relpath(abs_path, temp_dir)
                zipf.write(abs_path, arcname)

    print(f"All submissions packaged into: {os.path.abspath(archive_name)}")

    shutil.rmtree(temp_dir)