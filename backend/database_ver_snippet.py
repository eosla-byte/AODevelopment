
def create_plugin_version(version: str, changelog: str, url: str, mandatory: bool):
    db = SessionLocal()
    try:
        new_v = models.PluginVersion(
            version_number=version,
            changelog=changelog,
            download_url=url,
            is_mandatory=mandatory
        )
        db.add(new_v)
        db.commit()
        return True
    except Exception as e:
        print(f"Error creating version: {e}")
        return False
    finally:
        db.close()

def get_plugin_versions():
    db = SessionLocal()
    try:
        # Sort by ID desc (newest first)
        versions = db.query(models.PluginVersion).order_by(models.PluginVersion.id.desc()).all()
        return versions
    finally:
        db.close()

def delete_plugin_version(version_id: int):
    db = SessionLocal()
    try:
        v = db.query(models.PluginVersion).filter(models.PluginVersion.id == version_id).first()
        if v:
            db.delete(v)
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_latest_plugin_version():
    db = SessionLocal()
    try:
        # Assumes ID desc is chronological.
        # Could also sort by version_number semver if needed, but ID is safer for insertion order
        v = db.query(models.PluginVersion).order_by(models.PluginVersion.id.desc()).first()
        if v:
            return {
                "version": v.version_number,
                "changelog": v.changelog,
                "url": v.download_url,
                "mandatory": v.is_mandatory
            }
        return None
    finally:
        db.close()
