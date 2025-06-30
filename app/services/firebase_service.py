
import firebase_admin
from firebase_admin import credentials, firestore

class FirebaseService:
    def __init__(self):
        self.db = None

    def init_app(self, cred_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        print("Firebase service initialized.")

    def get_session(self, session_id):
        doc_ref = self.db.collection('scan_sessions').document(session_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None

    def update_session(self, session_id, data):
        self.db.collection('scan_sessions').document(session_id).set(data, merge=True)

    def set_session(self, session_id, data):
        self.db.collection('scan_sessions').document(session_id).set(data)
    
    def get_qr_code_data(self, session_id):
        doc_ref = self.db.collection('qr_codes').document(session_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
        
    def save_qr_code_data(self, session_id, payload):
        self.db.collection('qr_codes').document(session_id).set(payload)

firebase_service = FirebaseService()