"""业务服务层，后续可在此接入相机、MES、数据库、统计等真实服务。"""

from .dashboard_service import DashboardService
from .config_service import ConfigService

__all__ = ["ConfigService", "DashboardService"]
