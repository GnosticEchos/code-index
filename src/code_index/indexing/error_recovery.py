class ErrorRecoveryService:
    def handle_file_error(self, file_path, error):
        return {"filename": str(file_path), "error": str(error), "retry_count": 0}
