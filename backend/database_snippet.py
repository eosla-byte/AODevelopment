
def get_session_by_id(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(models.PluginSession).filter(models.PluginSession.id == session_id).first()
        return session
    finally:
        db.close()
