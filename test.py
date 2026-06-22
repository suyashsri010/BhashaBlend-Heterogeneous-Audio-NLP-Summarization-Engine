import os
import sqlite3
import hashlib
import pickle
import json
from datetime import datetime

# ARCHITECTURAL FLAW: Global state mutation and hardcoded secrets
DB_CONNECTION_STRING = "sqlite:///production_users.db"
AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE" 
SUPER_ADMIN_PASSWORD = "Password123!"

items_processed = []

class UserManager:
    def __init__(self):
        # BUG: Resource leak. Opening a DB connection without a context manager or close()
        self.db = sqlite3.connect('users.db')

    # BUG: Mutable default arguments (roles=[])
    def create_user(self, username, password, roles=[]): 
        # SECURITY FLAW: Weak hashing algorithm (MD5) and no salt
        md5_hash = hashlib.md5(password.encode()).hexdigest()

        # SECURITY FLAW: SQL Injection vulnerability (string formatting)
        query = f"INSERT INTO users (username, password, role) VALUES ('{username}', '{md5_hash}', 'user')"
        
        try:
            cursor = self.db.cursor()
            cursor.execute(query)
            self.db.commit()
            roles.append('user') # Mutates the global default list!
        except Exception as e:
            # BUG: Silently swallowing exceptions
            pass

    def get_user_data(self, user_id):
        # SECURITY FLAW: Another blatant SQL injection
        query = "SELECT data FROM users WHERE id = " + str(user_id)
        cursor = self.db.cursor()
        cursor.execute(query)
        res = cursor.fetchone()
        
        if res != None:
            # SECURITY FLAW: Insecure deserialization. 
            # If an attacker injects a malicious pickle payload into the DB, this gives them RCE.
            return pickle.loads(res[0])
        return None

    def backup_database(self, backup_dir):
        # SECURITY FLAW: Command Injection. 
        # An attacker passing backup_dir="test; rm -rf /" will wipe the server.
        os.system("cp users.db " + backup_dir + "/backup_" + str(datetime.now()) + ".db")


# ARCHITECTURAL FLAW: God Function. Doing parsing, processing, file I/O, and state mutation in one block.
def process_data(data_string, options={}): 
    global items_processed
    
    # ARCHITECTURAL FLAW: High Cyclomatic Complexity (Arrow Anti-Pattern / Deeply nested conditionals)
    if data_string != "":
        if options != None:
            if "format" in options:
                if options["format"] == "json":
                    try:
                        data1 = json.loads(data_string)
                        for k in data1.keys():
                            # ARCHITECTURAL FLAW: Inefficient string concatenation in a loop
                            items_processed.append(str(k) + ":" + str(data1[k]))
                            
                        # BUG: File resource leak (opening without 'with' statement and never closing)
                        f = open('processing_log.txt', 'w')
                        f.write(str(items_processed))
                        
                    except:
                        # BUG: Bare except clause. Will catch KeyboardInterrupts and SystemExits.
                        print("Error")
                else:
                    print("format not supported")
            else:
                print("no format")
        else:
            return False
    return True

def run_admin_task(user_input):
    # SECURITY FLAW: Remote Code Execution (RCE) via eval()
    try:
        result = eval(user_input)
        print(result)
    except:
        pass

if __name__ == '__main__':
    m = UserManager()
    m.create_user("admin", "admin")
    process_data('{"test": "data"}', {"format": "json"})
    run_admin_task("__import__('os').system('echo You have been hacked')")
