import firebase_admin
from firebase_admin import credentials, firestore
import traceback

class FirebaseService:
    def __init__(self):
        self.db = None

    def init_app(self, cred_path):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print("Firebase service initialized.")
        except Exception as e:
            print(f"ERROR: Gagal menginisialisasi Firebase Admin SDK: {e}")
            raise

    def get_session(self, session_id):
        try:
            doc_ref = self.db.collection('scan_sessions').document(session_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Firebase Error (get_session): {e}\n{traceback.format_exc()}")
            return None

    def update_session(self, session_id, data):
        try:
            self.db.collection('scan_sessions').document(session_id).set(data, merge=True)
            return True
        except Exception as e:
            print(f"Firebase Error (update_session): {e}\n{traceback.format_exc()}")
            return False

    def set_session(self, session_id, data):
        try:
            self.db.collection('scan_sessions').document(session_id).set(data)
            return True
        except Exception as e:
            print(f"Firebase Error (set_session): {e}\n{traceback.format_exc()}")
            return False
    
    def get_qr_code_data(self, session_id):
        try:
            doc_ref = self.db.collection('qr_codes').document(session_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Firebase Error (get_qr_code_data): {e}\n{traceback.format_exc()}")
            return None
        
    def save_qr_code_data(self, session_id, payload):
        try:
            self.db.collection('qr_codes').document(session_id).set(payload)
            return True
        except Exception as e:
            print(f"Firebase Error (save_qr_code_data): {e}\n{traceback.format_exc()}")
            return False

firebase_service = FirebaseService()