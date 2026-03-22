"""Application services."""

from importlib import import_module

__all__ = [
    "DashboardSection",
    "DashboardService",
    "DashboardSnapshot",
    "EventsOutlookService",
    "MacroMonitoringService",
    "MarketMonitoringService",
    "NewsPipelineService",
    "PushReportService",
]

_MODULE_BY_EXPORT = {
    "DashboardSection": ".dashboard_service",
    "DashboardService": ".dashboard_service",
    "DashboardSnapshot": ".dashboard_service",
    "EventsOutlookService": ".events_outlook_service",
    "MacroMonitoringService": ".macro_monitoring_service",
    "MarketMonitoringService": ".market_monitoring_service",
    "NewsPipelineService": ".news_pipeline_service",
    "PushReportService": ".push_report_service",
}


def __getattr__(name: str):
    module_name = _MODULE_BY_EXPORT.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
