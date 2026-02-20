"""
This file is intended to house widget definitions for a more modular dashboard approach in the future.
Currently, the dashboard services handle data gathering, but as the system grows,
we can extract "Widgets" into classes that are registered to specific roles.

Example concept:

class BaseWidget:
    template_name = ""
    def get_context(self, user):
        pass

class KpiWidget(BaseWidget):
    ...

class ChartWidget(BaseWidget):
    ...
    
"""

class DashboardWidgetRegistry:
    _registry = {}

    @classmethod
    def register(cls, widget_id, widget_class):
        cls._registry[widget_id] = widget_class

    @classmethod
    def get_widget(cls, widget_id):
        return cls._registry.get(widget_id)
