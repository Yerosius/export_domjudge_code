#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import zipfile
import shutil
import getpass
import mysql.connector
from tqdm import tqdm
import pwinput

LANG_EXT = {
    'c': 'c',
    'cpp': 'cpp',
    'java': 'java',
    'python3': 'py'
}

def connect_db():
    db_host = input("Enter database host (default: localhost): ").strip() or "localhost"
    db_user = input("Enter database username (default: root): ").strip() or "root"
    db_pass = pwinput.pwinput("Enter database password: ", mask="*")
    db_name = input("Enter database name (default: domjudge): ").strip() or "domjudge"
    contest_id = input("Enter contest ID: ").strip()

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

    return conn, contest_id

def query_submissions(conn, contest_id):
    cursor = conn.cursor(dictionary=True)
    query = """
    SELECT s.submitid, s.teamid, s.probid, s.langid, f.sourcecode, f.filename
    FROM submission s
    JOIN submission_file f ON s.submitid = f.submitid
    WHERE s.cid = %s
    ORDER BY s.langid, s.teamid, s.probid, s.submitid
    """
    cursor.execute(query, (contest_id,))
    rows = cursor.fetchall()
    cursor.close()
    return rows

def export_submissions(rows, temp_dir):
    total_files = len(rows)
    if total_files == 0:
        print("[WARNING] No submissions found for this contest.")
        return 0

    for row in tqdm(rows, desc="Exporting submissions", unit="file"):
        lang = row['langid']
        team = row['teamid']
        problem = row['probid']
        submitid = row['submitid']
        filename = row['filename'] if row['filename'] else f"{submitid}.{LANG_EXT.get(lang,'txt')}"

        dir_path = os.path.join(temp_dir, lang, f"team_{team}", f"problem_{problem}")
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "wb") as f:
            f.write(row['sourcecode'])
    return total_files

def create_zip(temp_dir, contest_id):
    archive_name = f"contest_{contest_id}_submissions.zip"
    with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname = os.path.relpath(abs_path, temp_dir)
                zipf.write(abs_path, arcname)
    print(f"[INFO] All submissions packaged into: {os.path.abspath(archive_name)}")
    return archive_name

def main():
    print("DOMJudge Contest Source Code Export Tool")

    conn, contest_id = connect_db()

    temp_dir = tempfile.mkdtemp(prefix=f"contest_{contest_id}_")

    rows = query_submissions(conn, contest_id)
    conn.close()
    total_files = export_submissions(rows, temp_dir)

    if total_files == 0:
        shutil.rmtree(temp_dir)
        return

    create_zip(temp_dir, contest_id)
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()