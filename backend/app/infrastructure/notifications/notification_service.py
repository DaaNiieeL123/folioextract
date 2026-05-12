try:
    from plyer import notification
except ImportError:
    notification = None

class NotificationService:
    @staticmethod
    def notify_done(count: int, error_count: int = 0) -> None:
        if not notification:
            return
            
        success_msg = f"✅ {count} archivos convertidos exitosamente."
        if error_count > 0:
            success_msg += f"\n❌ {error_count} archivos con errores."
            
        try:
            notification.notify(
                title="FolioExtract - Proceso Terminado",
                message=success_msg,
                app_name="FolioExtract",
                timeout=5
            )
        except Exception:
            pass # Fall back to skipping if OS doesn't support plyer or it crashes


