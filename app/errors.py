

class ApiServiceError(Exception):
    """Kelas dasar untuk semua error yang terjadi di layanan API."""
    def __init__(self, message="An internal service error occurred", status_code=500, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details

    def to_dict(self):
        """Mengubah error menjadi format dictionary untuk respons JSON."""
        error_payload = {'error': self.message}
        if self.details:
            error_payload['details'] = self.details
        return error_payload

class FirebaseError(ApiServiceError):
    """Error spesifik untuk masalah koneksi atau operasi Firebase."""
    def __init__(self, message="Database communication error", details=None):
        super().__init__(message, status_code=503, details=details) # 503 Service Unavailable

class MqttError(ApiServiceError):
    """Error spesifik untuk masalah koneksi atau operasi MQTT."""
    def __init__(self, message="MQTT communication error", details=None):
        super().__init__(message, status_code=503, details=details)

class DetectionError(ApiServiceError):
    """Error spesifik untuk masalah pada layanan deteksi objek."""
    def __init__(self, message="Object detection service error", details=None):
        super().__init__(message, status_code=500, details=details)

class NotFoundError(ApiServiceError):
    """Error untuk entitas yang tidak ditemukan (misal: sesi tidak ada)."""
    def __init__(self, message="Resource not found", details=None):
        super().__init__(message, status_code=404, details=details)

class InvalidUsageError(ApiServiceError):
    """Error untuk penggunaan API yang salah oleh klien."""
    def __init__(self, message="Invalid API usage", details=None):
        super().__init__(message, status_code=400, details=details)