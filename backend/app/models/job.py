"""
Job 数据库模型
"""
from sqlalchemy import Column, String, Integer, JSON, DateTime, Text
from datetime import datetime
from app.core.database import Base


class Job(Base):
    """治具生成任务模型"""
    
    __tablename__ = "jobs"
    
    # 基础信息
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="idle")  # idle, parsing, generating, completed, failed
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    
    # 文件路径
    file_path = Column(String, nullable=False)
    dxf_path = Column(String, nullable=True)
    svg_path = Column(String, nullable=True)
    
    # JSON 数据
    parameters = Column(JSON, nullable=True)  # 工程参数
    analysis_data = Column(JSON, nullable=True)  # PCB 分析结果
    result_data = Column(JSON, nullable=True)  # 治具生成结果
    confirmed_layers = Column(JSON, nullable=True)  # 用户确认的图层
    error_data = Column(JSON, nullable=True)  # 错误信息
    logs = Column(JSON, default=list)  # 诊断日志
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Job(id={self.id}, name={self.name}, status={self.status})>"
