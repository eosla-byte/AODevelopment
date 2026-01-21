
class PluginVersion(Base):
    __tablename__ = 'plugin_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_number = Column(String, nullable=False) # e.g. "1.0.1"
    changelog = Column(Text)
    download_url = Column(String)
    is_mandatory = Column(Boolean, default=False)
    release_date = Column(DateTime, default=func.now())
