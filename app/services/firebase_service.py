import firebase_admin
from firebase_admin import credentials, firestore
import traceback
from app.errors import FirebaseError

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
            raise FirebaseError("Failed to initialize Firebase Admin SDK", details=str(e))

    def get_session(self, session_id):
        try:
            doc_ref = self.db.collection('scan_sessions').document(session_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            raise FirebaseError("Failed to get session from database", details=str(e))

    def update_session(self, session_id, data):
        try:
            self.db.collection('scan_sessions').document(session_id).set(data, merge=True)
            return True
        except Exception as e:
            raise FirebaseError("Failed to update session", details=str(e))

    def set_session(self, session_id, data):
        try:
            self.db.collection('scan_sessions').document(session_id).set(data)
            return True
        except Exception as e:
            raise FirebaseError("Failed to set session", details=str(e))
    
    def get_qr_code_data(self, session_id):
        try:
            doc_ref = self.db.collection('qr_codes').document(session_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
           raise FirebaseError("Failed to get qr code", details=str(e))
        
    def save_qr_code_data(self, session_id, payload):
        try:
            self.db.collection('qr_codes').document(session_id).set(payload)
            return True
        except Exception as e:
            raise FirebaseError("Failed to save qr code", details=str(e))

firebase_service = FirebaseService()